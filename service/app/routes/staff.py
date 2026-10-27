"""The staff pages: the overview, the evidence queue and decisions, investor approvals, founders, people
and roles, and the audit log. Ported from apps/web/app/admin.

Reviewers see the overview, founders and the evidence queue. The rest is for admins. The database
functions check the role again and write the audit log, so these pages only show and send.
"""

from __future__ import annotations

import asyncio
import re

from fastapi import APIRouter, Request
from starlette.exceptions import HTTPException

from .. import admin_view
from ..activity import feed_entry, load_feed
from ..forms import REVIEW_LANES, parse_decision
from ..jsfmt import parse_int, search_params, to_fixed
from ..log import log_error, log_info
from ..score_engine import RUBRIC_V3
from ..scoring import record_venture_score
from ..session import require_staff
from ..staff import (
    change_lines,
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


async def _frame(v) -> dict:
    """The admin frame for a page from before the redesign: the sidebar, and app.css for the page's own styles."""
    return {"shell": await admin_view.shell(v), "legacy": True}


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


# ---------------------------------------------------------------- investors
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
        else:
            done = "approved" if one(values, "approve") == "yes" else "declined or suspended"
            return redirect("/admin/investors?tab=pending", {"form": "notice", "status": "sent", "message": f"The investor is {done}."})
    return redirect("/admin/investors?tab=pending")


# ---------------------------------------------------------------- evidence
@router.post("/admin/evidence/recompute")
async def recompute(request: Request):
    """Recomputes the score of a venture whose score missed an update after a decision."""
    v = await require_staff(request)
    venture = one(await form_data(request), "venture")
    if not ID.fullmatch(venture):
        return redirect("/admin/content?tab=evidence")
    scored = await record_venture_score(v.db, venture, None)
    return redirect("/admin/content?tab=evidence" if scored else "/admin/content?tab=evidence&score=failed")


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
    return render(request, "staff/review.html", {**context, **await _frame(v)}, _meta("Review evidence"))


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
    return redirect("/admin/content?tab=evidence" if scored else "/admin/content?tab=evidence&score=failed")


# ---------------------------------------------------------------- ventures
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

    founder, held_by, pitch, evidence, activity, intros, score = await asyncio.gather(
        v.db.table("profiles").eq("user_id", venture["founder_id"]).maybe_single("full_name, role, status, city, created_at"),
        holder(),
        v.db.table("pitches").eq("venture_id", venture_id).maybe_single("duration_seconds, updated_at"),
        v.db.table("evidence").eq("venture_id", venture_id).order("created_at", ascending=False)
        .select("id, signal_code, summary, status, lane, created_at, decided_at"),
        load_feed(v.db, venture=venture_id, limit=5),
        v.db.table("introductions").eq("venture_id", venture_id).select("status"),
        v.db.table("scores").eq("venture_id", venture_id).maybe_single("total, league, computed_at"),
    )
    statuses = [i["status"] for i in (intros.data or [])]
    context = {
        "role": _role(v), "admin": v.profile.role == "admin", "venture": venture, "done": done, "holder": held_by,
        "founder": founder.data, "pitch": pitch.data, "score": score.data,
        "activity": [feed_entry(r, False) for r in (activity or [])],
        "evidence": [{**e, "waiting": e["status"] in WAITING, "state": evidence_state(e)} for e in (evidence.data or [])],
        "intro_count": statuses.count,
    }
    if states:
        context["states"] = states
    return render(request, "staff/venture.html", {**context, **await _frame(v)}, _meta("Venture"))


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
        **await _frame(v),
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
    return render(request, "staff/person.html", {**context, **await _frame(v)}, _meta("Person"))


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
