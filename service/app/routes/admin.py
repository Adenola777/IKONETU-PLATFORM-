"""The admin pages of the redesign the owner approved on 26 October 2026: the dashboard, founders,
investors, introductions, pitch videos, reports and evidence, analytics, the database, settings and
the audit log.

Each page reads what it shows through the admin functions of migration 20261027000002, which check
the caller's role again and write the audit log, so these routes only show and send. Filters are
sent in the page's address, so a filtered list can be bookmarked and exported as it stands.
"""

from __future__ import annotations

import asyncio
import re

from fastapi import APIRouter, Request
from starlette.exceptions import HTTPException

from .. import admin_view as av
from ..log import log_error, log_info
from ..session import require_staff
from ..web import Meta, form_data, one, redirect, render
from . import staff as legacy

router = APIRouter()

ID = re.compile(r"[0-9a-f-]{36}")
RECORD = re.compile(r"(p[0-9]{3,6}|s[0-9]{2,6})")
PAGE = 25


def _meta(title: str) -> Meta:
    return Meta(title=title, noindex=True)


def _get(request: Request, key: str, default: str = "") -> str:
    values = request.query_params.getlist(key)
    return values[0] if len(values) == 1 else default


def _notice(location: str, message: str):
    """Back to a page after a change, with the green notice the boards show once."""
    return redirect(location, {"form": "notice", "status": "sent", "message": message})


async def _page(request: Request, v, template: str, current: str, title: str, context: dict, **extra):
    shell = await av.shell(v)
    return render(request, template, {"shell": shell, "current": current, "av": av, **context}, _meta(title), **extra)


def _rows(result, event: str) -> list:
    if not result.ok:
        log_error(event, {"code": result.error.code})
    return result.data if result.ok and isinstance(result.data, list) else []


def _one(result, event: str):
    if not result.ok:
        log_error(event, {"code": result.error.code})
        return None
    data = result.data
    return (data[0] if data else None) if isinstance(data, list) else data


# ---------------------------------------------------------------- the dashboard
def bar_style(n: int, top: int, height: int) -> str:
    return f"height:{round(n / top * height)}px"


def width_style(n: int, top: int) -> str:
    return f"width:{round(n / top * 100) if top else 0}%"


def bars(rows: list, top_key=lambda r: r[1]) -> list[dict]:
    top = max([1, *(top_key(r) for r in rows)])
    return [{"label": label, "n": n, "style": width_style(n, top)} for label, n in rows]


def dashboard_context(d: dict, recent: list[dict]) -> dict:
    staff = d["admins"] + d["reviewers"]
    staff_sub = " · ".join(x for x in (av.plural(d["admins"], "admin") if d["admins"] else "",
                                       av.plural(d["reviewers"], "reviewer") if d["reviewers"] else "") if x) or "None"
    kpis = [
        ("Waitlist", d["waitlist"], "form responses received", "/admin/audit", "f"),
        ("Founders", d["founders"], "on the register", "/admin/founders", "f"),
        ("Investors", d["investors"], "on the register", "/admin/investors", "i"),
        ("Pitch videos", d["videos"], f"{d['videos_pending']} pending review", "/admin/videos", "f"),
        ("Introductions", d["intros"], f"{d['intros_pending']} pending · {d['intros_accepted']} accepted", "/admin/introductions", "i"),
        ("Messages", d["messages"], f"{d['messages']} sent in {av.plural(d['conversations'], 'conversation')}", "/admin/introductions", "n"),
        ("Staff", staff, staff_sub, "/admin/settings", "n"),
    ]
    months = d.get("months") or []
    top = max([1, *(max(m["founders"], m["investors"]) for m in months)])
    chart = [{"label": av.SHORT[int(m["month"][5:7]) - 1], "f": m["founders"], "i": m["investors"],
              "f_style": bar_style(m["founders"], top, 180), "i_style": bar_style(m["investors"], top, 180)} for m in months]
    chart_label = "Founders and investors by month: " + "; ".join(
        f"{av.month_name(m['month'])}, {m['founders']} founders, {m['investors']} investors" for m in months)
    queues = [
        ("Pitch videos to review", d["videos_pending"], "/admin/videos"),
        ("Evidence to review", d["evidence_waiting"], "/admin/content?tab=evidence"),
        ("Open reports", d["reports_open"], "/admin/content"),
        ("Investors awaiting approval", d["investors_awaiting"], "/admin/investors?tab=pending"),
        ("Sign-ups not finished", d["unfinished"], "/admin/founders?tab=unfinished"),
    ]
    latest = []
    lf = d.get("latest_founder")
    if lf:
        latest.append(("Latest founder", " · ".join(x for x in (lf["full_name"] or "(no name given)", lf["startup"]) if x),
                       "Joined the register " + av.long_text(lf["joined_at"]), f"/admin/founders/{lf['record_id']}"))
    li = d.get("latest_investor")
    if li:
        latest.append(("Latest investor", f"{li['full_name']} · {li['register_no']}",
                       "Added to the register " + av.full_date(li["registered_on"]), "/admin/investors"))
    held = f"{d['intros_register']} from the registers"
    if d["intros_accepted"]:
        held += f", and {d['intros_accepted']} accepted holding {av.plural(d['messages'], 'message')}"
    latest.append(("Introductions", f"{d['intros']} made · {d['intros_pending']} pending · {d['intros_accepted']} accepted",
                   held, "/admin/introductions"))
    countries = [tuple(c) for c in d.get("countries") or []]
    support = [tuple(s) for s in d.get("support") or []]
    gave_none = d["founders"] - d["founders_with_support"]
    return {
        "today": av.today_text(), "kpis": kpis, "chart": chart, "chart_label": chart_label, "queues": queues, "latest": latest,
        "countries": bars(countries), "support": bars(support),
        "country_note": f"{av.plural(d['founders'], 'founder')} in {av.plural(len(countries), 'country', 'countries')}.",
        "support_note": (f"{d['founders_with_support']} of {d['founders']} founders asked for at least one kind of support; "
                         f"{gave_none} gave none."),
        "recent": [{"when": av.when_text(e["at"], e["date_only"]), "who": e["who"], "text": e["text"]} for e in recent],
    }


async def staff_log(v, limit: int) -> tuple[list[dict], dict[str, str]]:
    """The newest audit_log entries and the names of the people who made them."""
    result = await v.db.table("audit_log").order("id", ascending=False).limit(limit).select(
        "id, actor_id, action, entity, entity_id, before, after, created_at")
    rows = _rows(result, "admin.audit_failed")
    return rows, await legacy._actor_names(v, rows)


@router.get("/admin")
async def dashboard(request: Request):
    v = await require_staff(request)
    if v.profile.role != "admin":
        return redirect("/admin/content")
    d, history, (log, names) = await asyncio.gather(
        v.db.rpc("admin_dashboard"), v.db.rpc("admin_register_history", {"p_limit": 6}), staff_log(v, 6))
    data = _one(d, "admin.dashboard_failed")
    hist = _one(history, "admin.history_failed") or {}
    recent = av.newest_first(av.register_entries(hist) + av.staff_entries(log, names, describe_staff))[:6]
    context = {"d": dashboard_context(data, recent)} if data else {"failed": True}
    return await _page(request, v, "admin/dashboard.html", "dashboard", "Dashboard", context)


# ---------------------------------------------------------------- staff actions, in words
def describe_staff(e: dict) -> tuple[str, list[tuple[str, str]], str | None]:
    """What a staff action did, for the audit log and the dashboard: a sentence, its details and the record's page."""
    from ..staff import action_text, change_lines, entity_href, entry_reason

    text = action_text(e["action"])
    text = text[:1].upper() + text[1:]
    details = [("Changed", line) for line in change_lines(e.get("before"), e.get("after"))]
    reason = entry_reason(e.get("after"))
    if reason:
        details.append(("Reason", reason))
    after = e.get("after") or {}
    if e["action"] == "register.add" and isinstance(after.get("added"), int):
        details.append(("Entries added", str(after["added"])))
    if e.get("entity_id"):
        details.append(("Record", f"{e['entity']} {e['entity_id']}"))
    href = entity_href(e["entity"], e.get("entity_id"))
    if not href and e["entity"] in ("founder_register",) and e.get("entity_id") and e["action"] != "register.founder_delete":
        href = f"/admin/founders/{e['entity_id']}"
    if not href and e["entity"] == "register_introductions" and e.get("entity_id"):
        href = f"/admin/introductions/{e['entity_id']}"
    return text, details, href


# ---------------------------------------------------------------- founders
FOUNDER_SORTS = {"new": "Newest first", "old": "Oldest first", "name": "Name, A to Z"}
VIDEO_FILTERS = ("pending", "approved", "rejected", "none")


def founder_filters(request: Request) -> dict:
    sort = _get(request, "sort", "new")
    video = _get(request, "video", "any")
    return {
        "q": _get(request, "q")[:120], "country": _get(request, "country", "any") or "any",
        "month": _get(request, "month", "any") or "any", "support": _get(request, "support", "any") or "any",
        "video": video if video in VIDEO_FILTERS else "any", "sort": sort if sort in FOUNDER_SORTS else "new",
    }


def filter_founders(rows: list[dict], f: dict) -> list[dict]:
    """The Founders board's filter and sort, on the records admin_founder_records gives."""
    q = f["q"].strip().lower()
    shown = [r for r in rows if
             (f["country"] == "any" or r["country_key"] == f["country"])
             and (f["month"] == "any" or av.moment(r["joined_at"]).strftime("%Y-%m") == f["month"])
             and (f["support"] == "any" or f["support"] in (r.get("support") or []))
             and (f["video"] == "any" or r["video_status"] == f["video"])
             and (not q or q in " ".join([r["full_name"], r["startup"], r["email"], r["phone"]]).lower())]
    if f["sort"] == "name":
        return sorted(shown, key=lambda r: (av.name_key(r["full_name"]), r["record_id"]))
    newest = f["sort"] != "old"
    return sorted(shown, key=lambda r: (av.moment(r["joined_at"]), r["record_id"]), reverse=newest)


def founder_options(rows: list[dict]) -> dict:
    countries: dict[str, int] = {}
    for r in rows:
        countries[r["country_key"]] = countries.get(r["country_key"], 0) + 1
    support: dict[str, int] = {}
    for r in rows:
        for s in r.get("support") or []:
            support[s] = support.get(s, 0) + 1
    return {
        "countries": sorted(countries.items(), key=lambda c: (-c[1], c[0])),
        "months": sorted({av.moment(r["joined_at"]).strftime("%Y-%m") for r in rows}),
        "support": [k for k, n in sorted(support.items(), key=lambda s: (-s[1], s[0])) if n > 1],
    }


def founder_row(r: dict) -> dict:
    return {
        **r, "name_text": r["full_name"] or "(no name given)", "reg_no": "FND-" + r["record_id"][1:],
        "startup_text": r["startup"] or "(no startup name)", "joined": av.day_text(r["joined_at"]),
        "chip": av.VIDEO_CHIPS[r["video_status"]], "repeat": r["responses"] > 1,
    }


@router.get("/admin/founders")
async def founders(request: Request):
    v = await require_staff(request)
    admin = v.profile.role == "admin"
    tab = _get(request, "tab", "founders" if admin else "accounts")
    if not admin or tab == "accounts":
        return await _accounts_tab(request, v, admin)
    records, unfinished = await asyncio.gather(v.db.rpc("admin_founder_records"), v.db.rpc("admin_unfinished_signups"))
    rows = _rows(records, "admin.founders_failed")
    signups = _rows(unfinished, "admin.signups_failed")
    f = founder_filters(request)
    counts = {k: sum(1 for r in rows if r["video_status"] == k) for k in VIDEO_FILTERS}
    shown = filter_founders(rows, f)
    page = av.page_of(shown, av.page_number(_get(request, "page")), PAGE)
    base = {k: f[k] for k in ("q", "country", "month", "support", "video")} | {"sort": None if f["sort"] == "new" else f["sort"]}
    asking = _get(request, "remove")
    shell = await av.shell(v)
    waitlist = (shell.get("counts") or {}).get("waitlist") or 0
    context = {
        "tab": "unfinished" if tab == "unfinished" else "founders", "f": f, "options": founder_options(rows), "counts": counts,
        "rows": [founder_row(r) for r in page["rows"]], "page": page, "total": len(rows), "shown": len(shown),
        "failed": not records.ok,
        "subtitle": (f"{av.plural(len(rows), 'founder')} on the register, from {waitlist} waitlist responses · "
                     f"{counts['pending']} pitch {'video' if counts['pending'] == 1 else 'videos'} waiting for review"),
        "signups": [{**s, "started": av.day_text(s["started_at"]), "asking": s["user_id"] == asking} for s in signups],
        "csv": av.query("/admin/founders.csv", base),
        "link": lambda **changes: av.query("/admin/founders", {**base, **changes}),
        "FOUNDER_SORTS": FOUNDER_SORTS,
    }
    return render(request, "admin/founders.html", {"shell": shell, "current": "founders", "av": av, **context}, _meta("Founders"))


async def _accounts_tab(request: Request, v, admin: bool):
    """The founders who have an IkonetU account, with their ventures: the founders list from before the redesign."""
    q = _get(request, "q")[:80]
    result = await v.db.rpc("admin_ventures", {"p_search": q or None, "p_state": "all", "p_limit": 100, "p_offset": 0})
    rows = _rows(result, "admin.ventures_failed")
    return await _page(request, v, "admin/founder_accounts.html", "founders", "Founders", {
        "rows": rows, "q": q, "admin": admin, "failed": not result.ok})


@router.get("/admin/founders.csv")
async def founders_csv(request: Request):
    v = await require_staff(request, admin=True)
    rows = _rows(await v.db.rpc("admin_founder_records", {"p_full": True}), "admin.founders_failed")
    shown = filter_founders(rows, founder_filters(request))
    head = ["Joined", "Register responses", "Name", "Email", "Phone", "Country", "University", "Startup", "Sector", "Stage",
            "Investment sought", "Year of study", "Degree programme", "Support asked for", "Problem", "Target market",
            "What makes it unique", "Pitch video"]
    return av.csv_response("ikonetu-founders.csv", head, [
        [av.moment(r["joined_at"]).strftime("%Y-%m-%d %H:%M:%S"), r["responses"], r["full_name"], r["email"], r["phone"], r["country"],
         r["university"], r["startup"], r["sector"], r["stage"], r["amount"], r["study_year"], r["degree"],
         "; ".join(r.get("support") or []), r["problem"], r["target_market"], r["unique_answer"], av.VIDEO_CHIPS[r["video_status"]]]
        for r in shown])


def record_context(r: dict) -> dict:
    """The founder detail board's values for one record."""
    name = r["full_name"] or "(no name given)"
    intros = r.get("introductions") or []
    responses = r.get("responses") or []
    video = r.get("video")
    facts = [("Startup", r["startup"]), ("Sector", r["sector"]), ("Stage", r["stage"]), ("Investment sought", r["amount"]),
             ("Country", r["country"]), ("University", r["university"]), ("Degree programme", r["degree"]),
             ("Year of study", r["study_year"])]
    answers = [("What problem are you solving?", r["problem"]), ("Your target market", r["target_market"]),
               ("How is your solution unique?", r["unique_answer"])]
    history = [{"text": f"Introduced to {x['investor_name']}" + (f", register number {x['investor_no']}" if x.get("investor_no") else ""),
                "at": av.day_text(x["made_on"])} for x in intros]
    history += [{"text": "Sent the register form again", "at": av.long_text(w["responded_at"])} for w in responses[1:][::-1]]
    history.append({"text": "Joined the register", "at": av.long_text(r["joined_at"])})
    messages = sum(x.get("messages") or 0 for x in intros)
    return {
        "r": r, "name": name, "avatar": av.initials(r["full_name"]), "reg_no": "FND-" + r["record_id"][1:],
        "joined": av.long_text(r["joined_at"]), "facts": [(k, v or "Not given") for k, v in facts],
        "answers": [(k, v or "Not given") for k, v in answers],
        "responses": [{"startup": w["startup"] or "No startup name", "sector": w["sector"] or "No sector",
                       "at": av.long_text(w["responded_at"])} for w in responses[::-1]],
        "intros": [{**x, "made": av.day_text(x["made_on"]), "chip": av.INTRO_CHIPS[x["status"]],
                    "messages_text": av.plural(x.get("messages") or 0, "message")} for x in intros],
        "message_total": messages, "video": video, "video_status": (video or {}).get("status") or "none",
        "history": history, "mailto": "mailto:" + r["email"] if r["email"] else None, "tel": av.tel(r["phone"]) if r["phone"] else None,
    }


@router.get("/admin/founders/{key}")
async def founder(request: Request, key: str):
    """A register record, such as p001, or a venture in the app, by its id."""
    v = await require_staff(request)
    if ID.fullmatch(key):
        return await legacy._venture_page(request, v, key)
    if v.profile.role != "admin":
        return redirect("/admin/founders")
    if not RECORD.fullmatch(key):
        raise HTTPException(404)
    r = _one(await v.db.rpc("admin_founder_record", {"p_id": key}), "admin.founder_failed")
    if not r:
        raise HTTPException(404)
    return await _page(request, v, "admin/founder.html", "founders", r["full_name"] or "Founder",
                       {**record_context(r), "delete_error": None})


@router.post("/admin/founders/{key}/delete")
async def delete_founder(request: Request, key: str):
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    if not RECORD.fullmatch(key):
        raise HTTPException(404)
    r = _one(await v.db.rpc("admin_founder_record", {"p_id": key}), "admin.founder_failed")
    if not r:
        raise HTTPException(404)
    if one(values, "confirm").strip() != "DELETE":
        return await _page(request, v, "admin/founder.html", "founders", r["full_name"] or "Founder",
                           {**record_context(r), "delete_error": "Type DELETE to confirm."}, status_code=422)
    result = await v.db.rpc("admin_founder_record_delete", {"p_id": key})
    if not result.ok:
        log_error("admin.founder_delete_failed", {"record": key, "code": result.error.code})
        return await _page(request, v, "admin/founder.html", "founders", r["full_name"] or "Founder",
                           {**record_context(r), "delete_error": "The record was not deleted. Please try again."})
    log_info("admin.founder_deleted", {"record": key})
    return _notice("/admin/founders", f"Deleted the record for {r['full_name'] or '(no name given)'}.")


@router.post("/admin/founders/signups/{user_id}/remove")
async def remove_signup(request: Request, user_id: str):
    await form_data(request)
    v = await require_staff(request, admin=True)
    if not ID.fullmatch(user_id):
        raise HTTPException(404)
    signups = _rows(await v.db.rpc("admin_unfinished_signups"), "admin.signups_failed")
    found = next((s for s in signups if s["user_id"] == user_id), None)
    if not found:
        return _notice("/admin/founders?tab=unfinished", "That sign-up is no longer waiting, so nothing was removed.")
    result = await v.db.rpc("admin_remove_signup", {"p_user": user_id})
    if not result.ok:
        (log_info if result.error.code in ("P0001", "42501") else log_error)("admin.signup_remove_failed", {"code": result.error.code})
        return _notice("/admin/founders?tab=unfinished", "The sign-up was not removed. Please try again.")
    return _notice("/admin/founders?tab=unfinished", f"Removed the sign-up for {found['email']}.")
