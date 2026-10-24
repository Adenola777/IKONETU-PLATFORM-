"""The staff pages: the overview, the evidence queue and decisions, investor approvals, founders, people
and roles, and the audit log. Ported from apps/web/app/admin.

Reviewers see the overview, founders and the evidence queue. The rest is for admins. The database
functions check the role again and write the audit log, so these pages only show and send.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from starlette.exceptions import HTTPException

from ..forms import REVIEW_LANES, parse_decision
from ..jsfmt import month_long, month_short, number_text, parse_int, search_params, to_fixed
from ..log import log_error, log_info
from ..product import days_between
from ..register import added_text, parse_register, register_lines
from ..register import refusal_text as register_refusal
from ..score_engine import RUBRIC_V3
from ..scoring import record_venture_score
from ..session import require_staff
from ..staff import (
    ACTION_GROUPS,
    change_lines,
    entity_href,
    entry_reason,
    parse_hold,
    parse_lift,
    parse_role_change,
    parse_status_change,
    refusal_text,
    roles_for,
)
from ..web import Meta, failed, form_data, one, redirect, render

router = APIRouter()

ID = re.compile(r"[0-9a-f-]{36}")
WAITING = ("submitted", "checking", "needs_review")
PAGE = 50


def _meta(title: str) -> Meta:
    return Meta(title=title, noindex=True)


def _role(v) -> str:
    return "admin" if v.profile.role == "admin" else "reviewer"


def _single(request: Request, key: str) -> str | None:
    """A query value given once, as a page read `typeof value === "string"`. Given twice, it is an array, and counts as none."""
    values = request.query_params.getlist(key)
    return values[0] if len(values) == 1 else None


def _page(request: Request) -> int:
    """Math.max(1, Number.parseInt(page, 10) || 1)."""
    n = parse_int(_single(request, "page") or "1")
    return max(1, n or 1)


def _search(request: Request) -> str:
    """The search box's text, cut to 80 UTF-16 units as String.prototype.slice cut it."""
    q = _single(request, "q") or ""
    units = q.encode("utf-16-le")[:160]
    return units.decode("utf-16-le", errors="ignore")


async def _actor_names(v, entries: list[dict]) -> dict[str, str]:
    ids = list(dict.fromkeys(e["actor_id"] for e in entries if e.get("actor_id")))
    if not ids:
        return {}
    actors = await v.db.table("profiles").in_("user_id", ids).select("user_id, full_name")
    return {p["user_id"]: p["full_name"] for p in (actors.data or [])}


def _actor(names: dict[str, str], actor_id: str | None) -> str:
    name = names.get(actor_id) if actor_id else None
    return "The system" if name is None else name


# ---------------------------------------------------------------- overview
def age_text(iso: str) -> str:
    d = days_between(iso, datetime.now(timezone.utc))
    return "today" if d == 0 else "yesterday" if d == 1 else f"{d} days ago"


def month_bars(months: list[dict]) -> dict:
    """The last six months as bars drawn to scale from zero, with the geometry the Next.js page drew."""
    width, height, top, base, bw = 360, 160, 22, 132, 36
    peak = max([1, *(m["count"] for m in months)])
    gap = (width - bw * len(months)) / len(months) if months else 0
    bars = []
    for i, m in enumerate(months):
        h = ((base - top) * m["count"]) / peak
        x = gap / 2 + i * (bw + gap)
        date = f"{m['month']}-01T00:00:00Z"
        bars.append({
            "count": m["count"], "month": month_short(date), "month_long": month_long(date),
            "title": f"{month_long(date)}: {m['count']}",
            "path": _bar(x, base, bw, h) if m["count"] > 0 else None,
            "x": number_text(x + bw / 2), "value_y": number_text(base - h - 6), "month_y": number_text(base + 18),
        })
    return {"width": width, "height": height, "base": base, "bars": bars}


def _bar(x: float, base: float, w: float, h: float) -> str:
    """A bar anchored to the baseline, with its top corners rounded by four pixels."""
    r = min(4, h, w / 2)
    t = base - h
    n = number_text
    return f"M{n(x)} {n(base)}V{n(t + r)}Q{n(x)} {n(t)} {n(x + r)} {n(t)}H{n(x + w - r)}Q{n(x + w)} {n(t)} {n(x + w)} {n(t + r)}V{n(base)}Z"


@router.get("/admin")
async def overview(request: Request):
    v = await require_staff(request)
    result = await v.db.rpc("admin_overview")
    if not result.ok:
        log_error("admin.overview_failed", {"code": result.error.code})
    data = result.data
    o = (data[0] if data else None) if isinstance(data, list) else data
    return render(request, "staff/overview.html", {
        "role": _role(v), "admin": v.profile.role == "admin", "o": o, "age_text": age_text,
        "chart": month_bars((o or {}).get("north_star_months") or []),
    }, _meta("Overview"))


# ---------------------------------------------------------------- investors
@router.get("/admin/investors")
async def investors(request: Request):
    """Admins approve or decline investor accounts. Pending accounts come first, oldest first."""
    v = await require_staff(request, admin=True)
    result = await v.db.table("profiles").eq("role", "investor").order("created_at").limit(200).select(
        "user_id, full_name, status, created_at, investor_profiles(investor_type, firm, website, based_in, sectors, stages, "
        "countries, cheque_size, thesis)"
    )
    rows = result.data or []
    return render(request, "staff/investors.html", {
        "role": _role(v), "failed": not result.ok,
        "pending": [r for r in rows if r["status"] == "pending"],
        "decided": [r for r in rows if r["status"] != "pending"][::-1],
    }, _meta("Investors"))


@router.post("/admin/investors/decide")
async def decide_investor(request: Request):
    """An admin approves or declines an investor. The database checks the role again and writes the audit log."""
    v = await require_staff(request, admin=True)
    values = await form_data(request)
    user = one(values, "user")
    if ID.fullmatch(user):
        result = await v.db.rpc("decide_investor", {"p_user": user, "p_approve": one(values, "approve") == "yes"})
        if not result.ok:
            log_error("investor.decide_failed", {"code": result.error.code})
    return redirect("/admin/investors")


# ---------------------------------------------------------------- evidence
@router.get("/admin/evidence")
async def queue(request: Request):
    """Evidence waiting for a decision, oldest first, and any venture whose score missed an update."""
    v = await require_staff(request)
    stale, result = await asyncio.gather(
        v.db.rpc("ventures_with_stale_scores"),
        v.db.table("evidence").in_("status", list(WAITING)).order("created_at").limit(200)
        .select("id, signal_code, summary, created_at, ventures(name)"),
    )
    return render(request, "staff/queue.html", {
        "role": _role(v), "score_failed": _single(request, "score") == "failed", "stale": stale.data or [],
        "rows": result.data or [], "failed": not result.ok,
    }, _meta("Evidence to review"))


@router.post("/admin/evidence/recompute")
async def recompute(request: Request):
    """Recomputes the score of a venture whose score missed an update after a decision."""
    v = await require_staff(request)
    venture = one(await form_data(request), "venture")
    if not ID.fullmatch(venture):
        return redirect("/admin/evidence")
    scored = await record_venture_score(v.db, venture, None)
    return redirect("/admin/evidence" if scored else "/admin/evidence?score=failed")


async def _review_page(request: Request, v, evidence_id: str, states: dict | None = None):
    if not ID.fullmatch(evidence_id):
        raise HTTPException(404)
    res = await v.db.table("evidence").eq("id", evidence_id).maybe_single(
        "id, venture_id, signal_code, status, summary, source_ref, created_at, ventures(name, founder_id), "
        "evidence_files(id, storage_path, mime_type, size_bytes, sha256)"
    )
    e = res.data
    if not e:
        raise HTTPException(404)
    signal = RUBRIC_V3.signal(e["signal_code"])
    stored = e.get("evidence_files") or []
    # Files open through links that last five minutes (SRD SEC-E2).
    links = await asyncio.gather(*(v.storage.signed_url("evidence", f["storage_path"], 300) for f in stored))
    files = [{**f, "url": link, "size_text": to_fixed(f["size_bytes"] / 1024 / 1024, 1)} for f, link in zip(stored, links, strict=True)]
    # The same file used elsewhere, found by its SHA-256.
    twins = 0
    if stored:
        found = await v.db.table("evidence_files").in_("sha256", [f["sha256"] for f in stored]).neq("evidence_id", e["id"]) \
            .limit(20).select("evidence_id, sha256")
        twins = len(found.data or [])
    context = {
        "role": _role(v), "e": e, "category": signal.category if signal else "", "mode": "fixed",
        "how": signal.how if signal else "reviewer", "hint": signal.hint if signal else "",
        "files": files, "twins": twins, "own": (e.get("ventures") or {}).get("founder_id") == v.id,
        "open": e["status"] in WAITING,
    }
    if states:
        context["states"] = states
    return render(request, "staff/review.html", context, _meta("Review evidence"))


@router.get("/admin/evidence/{evidence_id}")
async def review(request: Request, evidence_id: str):
    v = await require_staff(request)
    return await _review_page(request, v, evidence_id)


@router.post("/admin/evidence/{evidence_id}")
async def decide(request: Request, evidence_id: str):
    """Records a reviewer's decision through decide_evidence, then recomputes the venture's score.

    decide_evidence checks the reviewer's role, refuses their own evidence and writes the audit log.
    The score is recorded with up to three attempts (scoring.record_venture_score).
    """
    values = await form_data(request)
    v = await require_staff(request)
    ident = one(values, "id")
    if not ID.fullmatch(ident):
        return await _review_page(request, v, evidence_id, failed("decision", "This evidence could not be found."))
    parsed = parse_decision({k: one(values, k) for k in values})
    if not parsed.ok:
        return await _review_page(request, v, evidence_id, failed("decision", "Please check the decision.", parsed.errors, values))
    d = parsed.data
    if d["decision"] == "approve":
        args = {"p_evidence": ident, "p_decision": "approve", "p_lane": d["lane"], "p_public_note": d["publicNote"],
                "p_item_count": d["itemCount"], "p_months": d["months"], "p_revenue_usd": d["revenueUsd"], "p_stage": d["stage"]}
    else:
        args = {"p_evidence": ident, "p_decision": d["decision"], "p_reason": d["reason"]}
    result = await v.db.rpc("decide_evidence", args)
    if not result.ok:
        text = result.error.message or ""
        own, taken = "own evidence" in text, "already been decided" in text
        if own or taken:
            log_info("evidence.decide_refused", {"evidence": ident, "reason": "own_evidence" if own else "already_decided"})
        else:
            log_error("evidence.decide_failed", {"evidence": ident, "code": result.error.code})
        message = ("You cannot decide evidence on your own venture." if own
                   else "Someone has already decided this evidence." if taken
                   else "The decision was not saved. Please try again.")
        return await _review_page(request, v, evidence_id, failed("decision", message, values=values))
    ev = await v.db.table("evidence").eq("id", ident).maybe_single("venture_id")
    scored = await record_venture_score(v.db, ev.data["venture_id"], ident) if ev.data else False
    return redirect("/admin/evidence" if scored else "/admin/evidence?score=failed")


# ---------------------------------------------------------------- founders
STATES = (
    {"code": "all", "label": "Every venture"},
    {"code": "published", "label": "Published to investors"},
    {"code": "unpublished", "label": "Not published"},
    {"code": "hidden", "label": "Hidden by IkonetU"},
)


@router.get("/admin/founders")
async def founders(request: Request):
    """Every venture and its founder, sorted by name, for reviewers and admins."""
    v = await require_staff(request)
    q = _search(request)
    asked = _single(request, "state")
    state = asked if asked in {s["code"] for s in STATES} else "all"
    page = _page(request)
    result = await v.db.rpc("admin_ventures", {"p_search": q or None, "p_state": state, "p_limit": PAGE, "p_offset": (page - 1) * PAGE})
    if not result.ok:
        log_error("admin.ventures_failed", {"code": result.error.code})
    rows = result.data or []

    def link(p: int) -> str:
        return "/admin/founders?" + search_params([*((("q", q),) if q else ()), ("state", state), ("page", str(p))])

    return render(request, "staff/founders.html", {
        "role": _role(v), "admin": v.profile.role == "admin", "q": q, "state": state, "page": page, "rows": rows,
        "total": rows[0]["total_count"] if rows else 0, "failed": not result.ok, "STATES": STATES, "PAGE": PAGE, "link": link,
        "now": datetime.now(timezone.utc),
    }, _meta("Founders"))


VENTURE_DONE = {
    "hidden": "The profile is hidden from investors. The founder sees your reason on their dashboard.",
    "lifted": "The hold is lifted. The founder can publish the profile again when they choose.",
}


def evidence_state(e: dict) -> str:
    if e["status"] in WAITING:
        return "Waiting for review"
    if e["status"] == "approved" and e.get("lane") == "self":
        return "The founder's own statement"
    if e["status"] == "approved":
        return next((lane["name"] for lane in REVIEW_LANES if lane["code"] == e.get("lane")), "Approved")
    return {"needs_more": "More asked for", "rejected": "Rejected", "expired": "Expired"}.get(e["status"], e["status"])


async def _venture_page(request: Request, v, venture_id: str, states: dict | None = None):
    done = VENTURE_DONE.get(",".join(request.query_params.getlist("done")))
    if not ID.fullmatch(venture_id):
        raise HTTPException(404)
    found = await v.db.table("ventures").eq("id", venture_id).maybe_single(
        "id, founder_id, name, sector, stage, country, description, website, ask, created_at, published_at, hidden_at, "
        "hidden_reason, hidden_by"
    )
    venture = found.data
    if not venture:
        raise HTTPException(404)

    async def holder():
        if not venture.get("hidden_by"):
            return None
        r = await v.db.table("profiles").eq("user_id", venture["hidden_by"]).maybe_single("full_name")
        return (r.data or {}).get("full_name")

    founder, held_by, pitch, evidence, updates, intros, score = await asyncio.gather(
        v.db.table("profiles").eq("user_id", venture["founder_id"]).maybe_single("full_name, role, status, city, created_at"),
        holder(),
        v.db.table("pitches").eq("venture_id", venture_id).maybe_single("duration_seconds, updated_at"),
        v.db.table("evidence").eq("venture_id", venture_id).order("created_at", ascending=False)
        .select("id, signal_code, summary, status, lane, created_at, decided_at"),
        v.db.table("venture_updates").eq("venture_id", venture_id).order("created_at", ascending=False).limit(3)
        .select("body, created_at"),
        v.db.table("introductions").eq("venture_id", venture_id).select("status"),
        v.db.table("scores").eq("venture_id", venture_id).maybe_single("total, league, computed_at"),
    )
    statuses = [i["status"] for i in (intros.data or [])]
    context = {
        "role": _role(v), "admin": v.profile.role == "admin", "venture": venture, "done": done, "holder": held_by,
        "founder": founder.data, "pitch": pitch.data, "score": score.data, "updates": updates.data or [],
        "evidence": [{**e, "waiting": e["status"] in WAITING, "state": evidence_state(e)} for e in (evidence.data or [])],
        "intro_count": statuses.count,
    }
    if states:
        context["states"] = states
    return render(request, "staff/venture.html", context, _meta("Venture"))


@router.get("/admin/founders/{venture_id}")
async def venture(request: Request, venture_id: str):
    v = await require_staff(request)
    return await _venture_page(request, v, venture_id)


@router.post("/admin/founders/{venture_id}/hide")
async def hide_venture(request: Request, venture_id: str):
    """An admin hides a founder's profile from investors with a reason the founder reads.

    admin_hide_venture() checks the role again, unpublishes the profile, keeps the founder from
    publishing it, and writes the audit log.
    """
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    parsed = parse_hold(values)
    if not parsed.ok:
        return await _venture_page(request, v, venture_id, failed("hide", "Please check the reason.", parsed.errors, values))
    result = await v.db.rpc("admin_hide_venture", {"p_venture": parsed.data["id"], "p_reason": parsed.data["reason"]})
    if not result.ok:
        (log_info if result.error.code == "P0001" else log_error)("admin.hide_failed", {"venture": parsed.data["id"], "code": result.error.code})
        return await _venture_page(request, v, venture_id, failed("hide", refusal_text(result.error.message), values=values))
    return redirect(f"/admin/founders/{parsed.data['id']}?done=hidden")


@router.post("/admin/founders/{venture_id}/lift")
async def lift_hold(request: Request, venture_id: str):
    """An admin lifts the hold. The founder can then publish the profile again; it is not published for them."""
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    parsed = parse_lift(values)
    if not parsed.ok:
        return await _venture_page(request, v, venture_id, failed("lift", "Please check the note.", parsed.errors, values))
    result = await v.db.rpc("admin_lift_hold", {"p_venture": parsed.data["id"], "p_note": parsed.data["note"]})
    if not result.ok:
        (log_info if result.error.code == "P0001" else log_error)("admin.lift_failed", {"venture": parsed.data["id"], "code": result.error.code})
        return await _venture_page(request, v, venture_id, failed("lift", refusal_text(result.error.message), values=values))
    return redirect(f"/admin/founders/{parsed.data['id']}?done=lifted")


# ---------------------------------------------------------------- people
ROLES = ("founder", "investor", "reviewer", "admin")
STATUSES = ("active", "pending", "suspended")


@router.get("/admin/people")
async def people(request: Request):
    """Every account, newest first, with its email address. Admins only."""
    v = await require_staff(request, admin=True)
    q = _search(request)
    role = _single(request, "role") if _single(request, "role") in ROLES else None
    status = _single(request, "status") if _single(request, "status") in STATUSES else None
    page = _page(request)
    result = await v.db.rpc("admin_accounts", {
        "p_search": q or None, "p_role": role, "p_status": status, "p_limit": PAGE, "p_offset": (page - 1) * PAGE,
    })
    if not result.ok:
        log_error("admin.accounts_failed", {"code": result.error.code})
    rows = result.data or []

    def link(p: int) -> str:
        pairs = [*((("q", q),) if q else ()), *((("role", role),) if role else ()), *((("status", status),) if status else ()),
                 ("page", str(p))]
        return "/admin/people?" + search_params(pairs)

    return render(request, "staff/people.html", {
        "q": q, "role_filter": role, "status": status, "page": page, "rows": rows,
        "total": rows[0]["total_count"] if rows else 0, "failed": not result.ok, "ROLES": ROLES, "STATUSES": STATUSES,
        "PAGE": PAGE, "link": link,
    }, _meta("People and roles"))


PERSON_DONE = {
    "role": "The role is changed, and the change is in the audit log.",
    "suspended": "The account is suspended, and the change is in the audit log.",
    "active": "The account is active again. A founder's profile stays unpublished until the founder publishes it.",
}


async def _person_page(request: Request, v, user_id: str, states: dict | None = None):
    done = PERSON_DONE.get(",".join(request.query_params.getlist("done")))
    if not ID.fullmatch(user_id):
        raise HTTPException(404)
    result = await v.db.rpc("admin_accounts", {"p_user": user_id, "p_limit": 1})
    if not result.ok:
        log_error("admin.account_failed", {"code": result.error.code})
    a = (result.data or [None])[0]
    if not a:
        raise HTTPException(404)
    investor, log = await asyncio.gather(
        v.db.table("investor_profiles").eq("user_id", user_id).maybe_single("user_id"),
        v.db.table("audit_log").eq("entity", "profiles").eq("entity_id", user_id).order("id", ascending=False).limit(20)
        .select("id, actor_id, action, created_at, before, after"),
    )
    raw = log.data or []
    names = await _actor_names(v, raw)
    entries = [{**e, "actor": _actor(names, e.get("actor_id")), "lines": change_lines(e.get("before"), e.get("after")),
                "reason": entry_reason(e.get("after"))} for e in raw]
    context = {
        "a": a, "done": done, "own_account": a["user_id"] == v.id, "entries": entries, "has_investor": bool(investor.data),
        "roles": roles_for(a["role"], bool(a.get("venture_id")), bool(investor.data)),
    }
    if states:
        context["states"] = states
    return render(request, "staff/person.html", context, _meta("Person"))


@router.get("/admin/people/{user_id}")
async def person(request: Request, user_id: str):
    v = await require_staff(request, admin=True)
    return await _person_page(request, v, user_id)


@router.post("/admin/people/{user_id}/role")
async def set_role(request: Request, user_id: str):
    """An admin changes a person's role through admin_set_role(), which refuses a change to the admin's own account."""
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    parsed = parse_role_change(values)
    if not parsed.ok:
        return await _person_page(request, v, user_id, failed("role", "Please check the form.", parsed.errors, values))
    result = await v.db.rpc("admin_set_role", {"p_user": parsed.data["id"], "p_role": parsed.data["role"], "p_reason": parsed.data["reason"]})
    if not result.ok:
        (log_info if result.error.code in ("P0001", "42501") else log_error)("admin.role_failed", {"user": parsed.data["id"], "code": result.error.code})
        return await _person_page(request, v, user_id, failed("role", refusal_text(result.error.message), values=values))
    return redirect(f"/admin/people/{parsed.data['id']}?done=role")


@router.post("/admin/people/{user_id}/status")
async def set_status(request: Request, user_id: str):
    """An admin suspends an account with a reason, or makes it active again, through admin_set_status()."""
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    parsed = parse_status_change(values)
    if not parsed.ok:
        return await _person_page(request, v, user_id, failed("status", "Please check the form.", parsed.errors, values))
    result = await v.db.rpc("admin_set_status", {
        "p_user": parsed.data["id"], "p_status": parsed.data["status"], "p_reason": parsed.data["reason"],
    })
    if not result.ok:
        (log_info if result.error.code in ("P0001", "42501") else log_error)("admin.status_failed", {"user": parsed.data["id"], "code": result.error.code})
        return await _person_page(request, v, user_id, failed("status", refusal_text(result.error.message), values=values))
    return redirect(f"/admin/people/{parsed.data['id']}?done={parsed.data['status']}")


# ---------------------------------------------------------------- investor register
MONTH = re.compile(r"([0-9]{4})-(0[1-9]|1[0-2])")


@router.get("/admin/register")
async def register(request: Request):
    """The investor register, in register number order, with the entries of each month and the running total."""
    v = await require_staff(request, admin=True)
    q = _search(request)
    asked = _single(request, "month") or ""
    month = asked if MONTH.fullmatch(asked) else None
    page = _page(request)
    result, months = await asyncio.gather(
        v.db.rpc("admin_register", {"p_search": q or None, "p_month": f"{month}-01" if month else None,
                                    "p_limit": PAGE, "p_offset": (page - 1) * PAGE}),
        v.db.rpc("admin_register_months"),
    )
    if not result.ok:
        log_error("admin.register_failed", {"code": result.error.code})
    if not months.ok:
        log_error("admin.register_months_failed", {"code": months.error.code})
    rows = result.data or []
    month_rows = months.data or []

    def link(p: int) -> str:
        pairs = [*((("q", q),) if q else ()), *((("month", month),) if month else ()), ("page", str(p))]
        return "/admin/register?" + search_params(pairs)

    return render(request, "staff/register.html", {
        "q": q, "month": month, "page": page, "rows": rows, "total": rows[0]["total_count"] if rows else 0,
        "failed": not result.ok, "months": month_rows, "months_failed": not months.ok,
        "in_register": month_rows[-1]["running_total"] if month_rows else 0, "PAGE": PAGE, "link": link,
    }, _meta("Investor register"))


def _register_add_page(request: Request, states: dict | None = None):
    return render(request, "staff/register_add.html", {"states": states or {}}, _meta("Add to the investor register"))


@router.get("/admin/register/add")
async def register_add_form(request: Request):
    await require_staff(request, admin=True)
    return _register_add_page(request)


@router.post("/admin/register/add")
async def register_add(request: Request):
    """Adds a pasted list to the register through admin_register_add(), which adds every entry or none and writes the
    audit log. An entry already there with the same name and date stays as it was."""
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    text = one(values, "entries")
    parsed = parse_register(text)
    if not parsed.ok:
        return _register_add_page(request, {"add": {"status": "error", "message": "Nothing was added. Please correct the list.",
                                                    "problems": parsed.errors[:20], "more": max(0, len(parsed.errors) - 20),
                                                    "values": values}})
    result = await v.db.rpc("admin_register_add", {"p_entries": parsed.entries})
    if not result.ok:
        (log_info if result.error.code in ("P0001", "22023") else log_error)("admin.register_add_failed", {"code": result.error.code})
        return _register_add_page(request, {"add": {"status": "error", "message": register_refusal(result.error.message),
                                                    "values": values}})
    data = result.data
    counts = (data[0] if data else None) if isinstance(data, list) else data
    added, unchanged = (counts or {}).get("added", 0), (counts or {}).get("unchanged", 0)
    log_info("admin.register_added", {"added": added, "unchanged": unchanged})
    return redirect("/admin/register", {"form": "added", "status": "sent", "message": added_text(added, unchanged, parsed.skipped)})


# ---------------------------------------------------------------- audit log
@router.get("/admin/audit")
async def audit(request: Request):
    """Every staff decision, newest first. Older entries are reached page by page."""
    v = await require_staff(request, admin=True)
    asked = _single(request, "group")
    group = asked if asked in {g["code"] for g in ACTION_GROUPS} else None
    before_text = _single(request, "before")
    before = int(before_text) if before_text and re.fullmatch(r"[0-9]+", before_text) else None
    query = v.db.table("audit_log").order("id", ascending=False).limit(PAGE + 1)
    if group:
        query = query.like("action", f"{group}.%")
    if before:
        query = query.lt("id", before)
    result = await query.select("id, actor_id, action, entity, entity_id, before, after, created_at")
    if not result.ok:
        log_error("admin.audit_failed", {"code": result.error.code})
    everything = result.data or []
    raw = everything[:PAGE]
    names = await _actor_names(v, raw)
    entries = []
    for e in raw:
        hidden = (e.get("after") or {}).get("profiles_hidden")
        counted = isinstance(hidden, (int, float)) and not isinstance(hidden, bool) and hidden > 0
        lines = register_lines(e.get("after")) if e["action"] == "register.add" else change_lines(e.get("before"), e.get("after"))
        entries.append({
            **e, "actor": _actor(names, e.get("actor_id")), "href": entity_href(e["entity"], e.get("entity_id")),
            "lines": lines, "reason": entry_reason(e.get("after")),
            "hidden": number_text(hidden) if counted else None,
        })
    older = None
    if len(everything) > PAGE and raw:
        older = "/admin/audit?" + search_params([*((("group", group),) if group else ()), ("before", str(raw[-1]["id"]))])
    return render(request, "staff/audit.html", {
        "group": group, "before": before, "entries": entries, "older": older, "failed": not result.ok,
    }, _meta("Audit log"))
