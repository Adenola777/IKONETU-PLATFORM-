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
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from starlette.exceptions import HTTPException

from .. import admin_analytics as aa
from .. import admin_settings as aset
from .. import admin_schema as ad
from .. import admin_view as av
from .. import platform
from ..log import log_error, log_info
from ..session import require_staff
from ..staff import ROLE_NAME
from ..web import Meta, form_data, many, one, redirect, render
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
    from ..register import register_lines
    from ..staff import action_text, change_lines, entity_href, entry_reason

    text = action_text(e["action"])
    text = text[:1].upper() + text[1:]
    if e["action"] == "register.add":
        # An addition says how many entries it added and which numbers, as the register page counts them.
        details = [tuple(line.split(": ", 1)) for line in register_lines(e.get("after"))]
    else:
        details = [("Changed", line) for line in change_lines(e.get("before"), e.get("after"), e["entity"])]
    reason = entry_reason(e.get("after"))
    if reason:
        details.append(("Reason", reason))
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


# ---------------------------------------------------------------- investors
INVESTOR_PAGE = 15
ACCOUNT_FILTERS = ("any", "linked", "not")


def investor_filters(request: Request) -> dict:
    acct = _get(request, "account", "any")
    return {"q": _get(request, "q")[:120], "month": _get(request, "month", "all") or "all",
            "account": acct if acct in ACCOUNT_FILTERS else "any"}


def filter_register(rows: list[dict], f: dict) -> list[dict]:
    """The Investors board's filter, on the whole register in register number order."""
    q = f["q"].strip().lower()
    return [r for r in rows if
            (f["month"] == "all" or r["registered_on"][:7] == f["month"])
            and (f["account"] == "any" or (f["account"] == "linked") == bool(r.get("account_id")))
            and (not q or q in r["register_no"] or q in r["full_name"].lower())]


def register_months(rows: list[dict]) -> list[dict]:
    """Each month that holds entries, with the entries added in it and the running total, as the board counted them."""
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["registered_on"][:7]] = counts.get(r["registered_on"][:7], 0) + 1
    running, out = 0, []
    total = len(rows) or 1
    for k in sorted(counts):
        running += counts[k]
        out.append({"key": k, "label": av.month_name(k), "added": counts[k], "total": running,
                    "style": f"width:{round(running / total * 100)}%"})
    return out


async def _investor_page(request: Request, v, states: dict | None = None, status_code: int = 200):
    tab = _get(request, "tab", "register")
    tab = tab if tab in ("register", "accounts", "pending") else "register"
    register, accounts = await asyncio.gather(
        v.db.rpc("admin_register", {"p_limit": 1000, "p_offset": 0}),
        v.db.table("profiles").eq("role", "investor").order("created_at").limit(200).select(
            "user_id, full_name, status, created_at, investor_profiles(investor_type, firm, website, based_in, sectors, stages, "
            "countries, cheque_size, thesis)"),
    )
    rows = _rows(register, "admin.register_failed")
    people = _rows(accounts, "admin.investors_failed")
    f = investor_filters(request)
    shown = filter_register(rows, f)
    page = av.page_of(shown, av.page_number(_get(request, "page")), INVESTOR_PAGE)
    linked_to = {r["account_id"]: r["register_no"] for r in rows if r.get("account_id")}
    first = min((r["registered_on"][:7] for r in rows), default=None)
    month_keys = []
    if first:
        y, m = int(first[:4]), int(first[5:7])
        now = datetime.now(timezone.utc)
        while (y, m) <= (now.year, now.month):
            month_keys.append(f"{y:04d}-{m:02d}")
            y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    base = {"q": f["q"], "month": f["month"], "account": f["account"]}
    return await _page(request, v, "admin/investors.html", "investors", "Investors", {
        "tab": tab, "f": f, "rows": page["rows"], "page": page, "total": len(rows), "shown": len(shown),
        "failed": not register.ok or not accounts.ok, "months": register_months(rows), "month_keys": month_keys,
        "introduced": sum(1 for r in rows if r["introductions"]),
        "active": [p for p in people if p["status"] != "pending"], "pending": [p for p in people if p["status"] == "pending"],
        "linked_to": linked_to, "linking": _get(request, "link"), "adding": _get(request, "add") == "1",
        "link": lambda **changes: av.query("/admin/investors", {**base, **changes}),
        "csv": av.query("/admin/investors.csv", base), "states": states or {},
    }, status_code=status_code)


@router.get("/admin/investors")
async def investors(request: Request):
    v = await require_staff(request, admin=True)
    return await _investor_page(request, v)


@router.get("/admin/investors.csv")
async def investors_csv(request: Request):
    v = await require_staff(request, admin=True)
    rows = _rows(await v.db.rpc("admin_register", {"p_limit": 1000, "p_offset": 0}), "admin.register_failed")
    shown = filter_register(rows, investor_filters(request))
    return av.csv_response("ikonetu-investor-register.csv", ["Register number", "Name", "Registered", "Account"], [
        [r["register_no"], r["full_name"], r["registered_on"], (r["account_email"] or "Linked") if r.get("account_id") else "Not linked"]
        for r in shown])


@router.post("/admin/investors/register")
async def add_register_entries(request: Request):
    """Adds a pasted list to the register through admin_register_add(), with the rules of the register import of
    24 October: every entry or none, and an entry already there with the same name and date left as it was."""
    from ..register import added_text, parse_register
    from ..register import refusal_text as register_refusal

    values = await form_data(request)
    v = await require_staff(request, admin=True)
    text = one(values, "entries")
    parsed = parse_register(text)
    if not parsed.ok:
        return await _investor_page(request, v, {"add": {"message": "Nothing was added. Please correct the list.",
                                                        "problems": parsed.errors[:20], "more": max(0, len(parsed.errors) - 20),
                                                        "text": text}}, status_code=422)
    result = await v.db.rpc("admin_register_add", {"p_entries": parsed.entries})
    if not result.ok:
        (log_info if result.error.code in ("P0001", "22023") else log_error)("admin.register_add_failed", {"code": result.error.code})
        return await _investor_page(request, v, {"add": {"message": register_refusal(result.error.message), "problems": [],
                                                        "more": 0, "text": text}}, status_code=422)
    counts = _one(result, "admin.register_add_failed") or {}
    added, unchanged = counts.get("added", 0), counts.get("unchanged", 0)
    log_info("admin.register_added", {"added": added, "unchanged": unchanged})
    return _notice("/admin/investors", added_text(added, unchanged, parsed.skipped))


LINK_REFUSALS = (
    (r"no investor account", "No investor account uses {email}."),
    (r"already linked to register entry (\d+)", "That account is linked to register entry {0} already."),
    (r"already linked to an account", "This register entry is linked to an account already."),
    (r"not linked", "This register entry is not linked to an account."),
)


def link_refusal(message: str, email: str) -> str:
    for pattern, text in LINK_REFUSALS:
        m = re.search(pattern, message or "")
        if m:
            return text.format(*m.groups(), email=email)
    return "The link was not saved. Please try again."


@router.post("/admin/investors/link")
async def link_register(request: Request):
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    no, email = one(values, "no").strip(), one(values, "email").strip()
    if not re.fullmatch(r"[0-9]{3,6}", no):
        raise HTTPException(404)
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return await _investor_page(request, v, {"link": {"no": no, "email": email,
                                                         "message": "Enter the email address of the investor's account."}}, 422)
    result = await v.db.rpc("admin_register_link", {"p_no": no, "p_email": email})
    if not result.ok:
        (log_info if result.error.code in ("P0001", "P0002") else log_error)("admin.register_link_failed", {"code": result.error.code})
        return await _investor_page(request, v, {"link": {"no": no, "email": email,
                                                         "message": link_refusal(result.error.message, email)}}, 422)
    return _notice("/admin/investors", f"Linked register entry {no} to the account of {email}.")


@router.post("/admin/investors/unlink")
async def unlink_register(request: Request):
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    no = one(values, "no").strip()
    if not re.fullmatch(r"[0-9]{3,6}", no):
        raise HTTPException(404)
    result = await v.db.rpc("admin_register_unlink", {"p_no": no})
    if not result.ok:
        log_info("admin.register_unlink_failed", {"code": result.error.code})
        return _notice("/admin/investors", link_refusal(result.error.message, ""))
    return _notice("/admin/investors", f"Register entry {no} is no longer linked to an account.")


@router.get("/admin/register")
async def old_register(request: Request):
    """The register page from before the redesign now lives on Investors."""
    await require_staff(request, admin=True)
    return redirect("/admin/investors")


@router.get("/admin/register/add")
async def old_register_add(request: Request):
    await require_staff(request, admin=True)
    return redirect("/admin/investors?add=1")


# ---------------------------------------------------------------- introductions
INTRO_SORTS = {"number": "Register number", "new": "Newest first", "founder": "Founder, A to Z", "messages": "Most messages"}
INTRO_STATUSES = ("pending", "accepted", "declined", "withdrawn")
STATUS_DONE = {"accepted": ("Marked accepted", "Marked accepted."), "declined": ("Marked declined", "Marked declined."),
               "withdrawn": ("Withdrawn", "Introduction withdrawn."), "pending": ("Returned to pending", "Introduction pending again.")}


def intro_row(n: dict) -> dict:
    inv_sample, f_sample = n["sample"], n["founder_sample"]
    f_no = "FND-" + n["record_id"][1:]
    return {
        **n, "inv_no_text": "Not on the register" if inv_sample else f"Register number {n['investor_no']}",
        "inv_no_shown": "None" if inv_sample else n["investor_no"], "inv_tag": "Not on the register" if inv_sample else "On the register",
        "f_tag": "Not on the register" if f_sample else "On the register", "f_name": n["founder_name"] or "(no name given)",
        "f_no": "None" if f_sample else f_no, "f_no_text": "Not on the register" if f_sample else f_no,
        "startup_text": n["startup"] or "Not given", "sector_text": n["sector"] or "Not given", "made": av.day_text(n["made_on"]),
        "chip": av.INTRO_CHIPS[n["status"]], "inv_on": av.day_text(n["investor_registered_on"]),
        "search": " ".join([n["investor_no"] or "", n["investor_name"], n["founder_name"], "" if f_sample else f_no.lower(),
                            n["founder_email"], n["startup"]]).lower(),
    }


def filter_intros(rows: list[dict], q: str, status: str, sort: str) -> list[dict]:
    q = q.strip().lower()
    shown = [r for r in rows if (status == "any" or r["status"] == status) and (not q or q in r["search"])]
    if sort == "messages":
        return sorted(shown, key=lambda r: (-r["messages"], r["intro_id"]))
    if sort == "founder":
        return sorted(shown, key=lambda r: (av.name_key(r["f_name"]), r["intro_id"]))
    if sort == "new":
        return sorted(shown, key=lambda r: r["intro_id"], reverse=True)
    return sorted(shown, key=lambda r: (r["investor_no"] or "~", r["intro_id"]))


def intro_query(request: Request) -> tuple[str, str, str]:
    status, sort = _get(request, "status", "any"), _get(request, "sort", "number")
    return _get(request, "q")[:120], status if status in INTRO_STATUSES else "any", sort if sort in INTRO_SORTS else "number"


@router.get("/admin/introductions")
async def introductions(request: Request):
    v = await require_staff(request, admin=True)
    result = await v.db.rpc("admin_register_introductions")
    rows = [intro_row(n) for n in _rows(result, "admin.introductions_failed")]
    q, status, sort = intro_query(request)
    shown = filter_intros(rows, q, status, sort)
    page = av.page_of(shown, av.page_number(_get(request, "page")), PAGE)
    counts = {k: sum(1 for r in rows if r["status"] == k) for k in INTRO_STATUSES}
    base = {"q": q, "status": status, "sort": None if sort == "number" else sort}
    return await _page(request, v, "admin/introductions.html", "introductions", "Introductions", {
        "rows": page["rows"], "page": page, "total": len(rows), "shown": len(shown), "counts": counts, "failed": not result.ok,
        "q": q, "status": status, "sort": sort, "INTRO_SORTS": INTRO_SORTS,
        "link": lambda **changes: av.query("/admin/introductions", {**base, **changes}), "csv": av.query("/admin/introductions.csv", base),
        "subtitle": (f"{av.plural(len(rows), 'introduction')} · {counts['pending']} pending · {counts['accepted']} accepted"),
    })


@router.get("/admin/introductions.csv")
async def introductions_csv(request: Request):
    v = await require_staff(request, admin=True)
    rows = [intro_row(n) for n in _rows(await v.db.rpc("admin_register_introductions"), "admin.introductions_failed")]
    shown = filter_intros(rows, *intro_query(request))
    head = ["Made", "Register number", "Investor", "Founder", "Founder register number", "Founder email", "Founder phone", "Startup",
            "Sector", "Status", "Messages", "Note"]
    return av.csv_response("ikonetu-introductions.csv", head, [
        [r["made"], r["investor_no"] or "S01", r["investor_name"], r["f_name"], r["f_no"], r["founder_email"], r["founder_phone"],
         r["startup_text"], r["sector_text"], r["chip"], r["messages"], r["note"] or "None"] for r in shown])


@router.get("/admin/introductions/{intro_id}")
async def introduction(request: Request, intro_id: str):
    v = await require_staff(request, admin=True)
    if not re.fullmatch(r"[ns][0-9]{3,6}", intro_id):
        raise HTTPException(404)
    found, log = await asyncio.gather(
        v.db.rpc("admin_register_introductions", {"p_id": intro_id}),
        v.db.table("audit_log").eq("entity", "register_introductions").eq("entity_id", intro_id).order("id", ascending=False)
        .limit(50).select("id, actor_id, after, created_at"))
    rows = _rows(found, "admin.introduction_failed")
    if not rows:
        raise HTTPException(404)
    n = intro_row(rows[0])
    history = [{"text": STATUS_DONE.get((e.get("after") or {}).get("status"), ("Changed",))[0], "at": av.long_text(e["created_at"])}
               for e in _rows(log, "admin.introduction_log_failed")]
    if n.get("accepted_on"):
        history.append({"text": f"Accepted by {n['f_name']}, which opened their conversation", "at": av.day_text(n["accepted_on"])})
    history.append({"text": "Introduction made", "at": n["made"]})
    return await _page(request, v, "admin/introduction.html", "introductions", "Introduction", {
        "n": n, "history": history, "tel": av.tel(n["founder_phone"]) if n["founder_phone"] else None,
        "joined": av.long_text(n["founder_joined_at"])})


@router.post("/admin/introductions/{intro_id}/status")
async def introduction_status(request: Request, intro_id: str):
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    status = one(values, "status")
    if not re.fullmatch(r"[ns][0-9]{3,6}", intro_id) or status not in INTRO_STATUSES:
        raise HTTPException(404)
    result = await v.db.rpc("admin_register_introduction_status", {"p_id": intro_id, "p_status": status})
    if not result.ok:
        (log_info if result.error.code in ("P0001", "P0002") else log_error)("admin.introduction_status_failed", {"code": result.error.code})
        return _notice(f"/admin/introductions/{intro_id}", "The status did not change, because the introduction changed meanwhile.")
    return _notice(f"/admin/introductions/{intro_id}", STATUS_DONE[status][1])


# ---------------------------------------------------------------- pitch videos in Google Drive
VIDEO_TABS = (("pending", "Pending review"), ("approved", "Approved"), ("rejected", "Rejected"), ("all", "All"))


def video_row(r: dict) -> dict:
    added = av.day_text(r["added_on"])
    decided = None
    if r["status"] != "pending":
        who = r.get("decided_by_name") or "an admin"
        verb = "Approved" if r["status"] == "approved" else "Rejected"
        decided = f"{verb} by {who}, {av.long_text(r['decided_at'])}." + (f" Reason: {r['reason']}" if r.get("reason") else "")
    kind = f"{r['file_type']} · {r['size_text']}"
    meta = f"{kind} · {r['folder']} · added to Google Drive {added}"
    linked = bool(r.get("record_id"))
    # A video linked to a founder record is titled with its startup, as the Videos board titled each card.
    return {**r, "kind": kind, "uploaded": f"to Google Drive {added}", "chip": av.VIDEO_CHIPS[r["status"]], "decided": decided,
            "title": (r.get("startup") or r.get("founder_name") or r["file_name"]) if linked else r["file_name"],
            "line": " · ".join(x for x in (r.get("founder_name"), r.get("sector")) if x) if linked
            else f"{r['folder'].split(' / ')[0]} folder · {kind}",
            "meta": f"{r['file_name']} · {meta}" if linked else meta,
            "record_href": f"/admin/founders/{r['record_id']}" if linked else None,
            "transcript_text": r.get("transcript") or "No transcript came with this file."}


def in_tab(r: dict, tab: str) -> bool:
    return tab == "all" or r["status"] == tab


async def _videos(v) -> list[dict]:
    return [video_row(r) for r in _rows(await v.db.rpc("admin_pitch_videos"), "admin.videos_failed")]


@router.get("/admin/videos")
async def videos(request: Request):
    v = await require_staff(request, admin=True)
    result = await v.db.rpc("admin_pitch_videos")
    rows = [video_row(r) for r in _rows(result, "admin.videos_failed")]
    tab = _get(request, "tab", "pending")
    tab = tab if tab in dict(VIDEO_TABS) else "pending"
    shown = [r for r in rows if in_tab(r, tab)]
    chosen = _get(request, "video")
    sel = next((r for r in shown if r["video_id"] == chosen), shown[0] if shown else None)
    pending = sum(1 for r in rows if r["status"] == "pending")
    return await _page(request, v, "admin/videos.html", "videos", "Pitch videos", {
        "tab": tab, "tabs": [(k, label, sum(1 for r in rows if in_tab(r, k))) for k, label in VIDEO_TABS],
        "items": shown, "sel": sel, "failed": not result.ok, "reason_missing": _get(request, "reason") == "missing",
        "subtitle": f"{pending} {'video waits' if pending == 1 else 'videos wait'} for review · {av.plural(len(rows), 'video')} in all",
    })


def _next_video(rows: list[dict], tab: str, done_id: str) -> str | None:
    """After a decision the board kept the video if it stays in the list, and otherwise moved to the next one waiting."""
    shown = [r for r in rows if in_tab(r, tab)]
    if any(r["video_id"] == done_id for r in shown):
        return done_id
    nxt = next((r for r in shown if r["status"] == "pending"), shown[0] if shown else None)
    return nxt["video_id"] if nxt else None


async def _after_video(v, tab: str, video_id: str, message: str):
    rows = await _videos(v)
    nxt = _next_video(rows, tab if tab in dict(VIDEO_TABS) else "pending", video_id)
    return _notice(av.query("/admin/videos", {"tab": None if tab == "pending" else tab, "video": nxt}), message)


@router.post("/admin/videos/{video_id}/approve")
async def approve_video(request: Request, video_id: str):
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    if not re.fullmatch(r"t[0-9]{2,6}", video_id):
        raise HTTPException(404)
    tab = one(values, "tab")
    checks = {k: one(values, k) == "on" for k, _ in av.VIDEO_CHECKS}
    result = await v.db.rpc("admin_pitch_video_decide", {"p_id": video_id, "p_decision": "approved", "p_checks": checks})
    name = next((r["title"] for r in await _videos(v) if r["video_id"] == video_id), video_id)
    if not result.ok:
        log_info("admin.video_decide_refused", {"video": video_id, "code": result.error.code})
        text = "Tick all four to approve." if result.error.code == "22023" else "This video has been reviewed already."
        return _notice(av.query("/admin/videos", {"tab": tab or None, "video": video_id}), text)
    return await _after_video(v, tab, video_id, f"Approved the {name} pitch video.")


@router.post("/admin/videos/{video_id}/reject")
async def reject_video(request: Request, video_id: str):
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    if not re.fullmatch(r"t[0-9]{2,6}", video_id):
        raise HTTPException(404)
    tab, reason = one(values, "tab"), one(values, "reason")
    if reason not in av.REJECT_REASONS:
        return _notice(av.query("/admin/videos", {"tab": tab or None, "video": video_id, "reason": "missing"}), "Choose a reason first.")
    result = await v.db.rpc("admin_pitch_video_decide", {"p_id": video_id, "p_decision": "rejected", "p_reason": reason})
    name = next((r["title"] for r in await _videos(v) if r["video_id"] == video_id), video_id)
    if not result.ok:
        log_info("admin.video_decide_refused", {"video": video_id, "code": result.error.code})
        return _notice(av.query("/admin/videos", {"tab": tab or None, "video": video_id}), "This video has been reviewed already.")
    return await _after_video(v, tab, video_id,
                              f"Rejected the {name} pitch video. The reason is kept with the file, because no founder account is linked to it.")


@router.post("/admin/videos/{video_id}/reopen")
async def reopen_video(request: Request, video_id: str):
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    if not re.fullmatch(r"t[0-9]{2,6}", video_id):
        raise HTTPException(404)
    tab = one(values, "tab")
    result = await v.db.rpc("admin_pitch_video_reopen", {"p_id": video_id})
    name = next((r["title"] for r in await _videos(v) if r["video_id"] == video_id), video_id)
    if not result.ok:
        log_info("admin.video_reopen_refused", {"video": video_id, "code": result.error.code})
        return _notice(av.query("/admin/videos", {"tab": tab or None, "video": video_id}), "This video is waiting for review already.")
    return await _after_video(v, tab, video_id, f"The {name} pitch video is pending review again.")


# ---------------------------------------------------------------- reports and evidence
@router.get("/admin/content")
async def content(request: Request):
    """Open reports and the evidence waiting for a decision. Reviewers and admins both work here."""
    from ..forms import signal_label

    v = await require_staff(request)
    tab = "evidence" if _get(request, "tab") == "evidence" else "reports"
    reports, evidence, stale = await asyncio.gather(
        v.db.rpc("admin_reports"),
        v.db.table("evidence").in_("status", list(legacy.WAITING)).order("created_at").limit(200)
        .select("id, signal_code, summary, created_at, ventures(name), evidence_files(id)"),
        v.db.rpc("ventures_with_stale_scores"))
    now = datetime.now(timezone.utc)
    open_reports = [{**r, "when": av.day_text(r["created_at"])} for r in _rows(reports, "admin.reports_failed")]
    waiting = [{**e, "sent": av.day_text(e["created_at"]), "signal": signal_label(e["signal_code"]),
                "files": len(e.get("evidence_files") or []), "waiting": (now - av.moment(e["created_at"])).days}
               for e in _rows(evidence, "admin.evidence_failed")]
    return await _page(request, v, "admin/content.html", "moderation", "Reports and Evidence", {
        "tab": tab, "reports": open_reports, "evidence": waiting, "stale": _rows(stale, "admin.stale_failed"),
        "resolving": _get(request, "resolve"), "score_failed": _get(request, "score") == "failed",
        "failed": not reports.ok or not evidence.ok,
    })


@router.get("/admin/evidence")
async def old_queue(request: Request):
    """The evidence queue from before the redesign now lives on Reports and Evidence."""
    await require_staff(request)
    return redirect("/admin/content?tab=evidence")


@router.post("/admin/content/reports/{report_id}/resolve")
async def resolve_report(request: Request, report_id: str):
    values = await form_data(request)
    v = await require_staff(request)
    if not ID.fullmatch(report_id):
        raise HTTPException(404)
    note = one(values, "note").strip()
    if not 5 <= len(note) <= 280:
        return _notice(f"/admin/content?resolve={report_id}", "Say what was done in 5 to 280 characters.")
    result = await v.db.rpc("admin_report_resolve", {"p_id": report_id, "p_note": note})
    if not result.ok:
        log_info("admin.report_resolve_refused", {"code": result.error.code})
        return _notice("/admin/content", "The report was not resolved, because it changed meanwhile.")
    return _notice("/admin/content", "The report is resolved.")


# ---------------------------------------------------------------- analytics
def _range(request: Request) -> str:
    key = _get(request, "range", "year")
    return key if key in aa.RANGES else "year"


async def _analytics(v, key: str) -> tuple[dict | None, bool]:
    source, intros = await asyncio.gather(v.db.rpc("admin_analytics_source"), v.db.rpc("admin_register_introductions"))
    data = _one(source, "admin.analytics_failed")
    rows = _rows(intros, "admin.introductions_failed")
    if data is None:
        return None, True
    return aa.build(data, rows, key, datetime.now(timezone.utc).date()), not intros.ok


@router.get("/admin/analytics")
async def analytics(request: Request):
    v = await require_staff(request, admin=True)
    key = _range(request)
    a, failed = await _analytics(v, key)
    return await _page(request, v, "admin/analytics.html", "analytics", "Analytics", {
        "a": a, "failed": a is None, "table_failed": failed and a is not None,
        "link": lambda k: av.query("/admin/analytics", {"range": None if k == "year" else k}),
        "csv": av.query("/admin/analytics.csv", {"range": None if key == "year" else key}),
    })


@router.get("/admin/analytics.csv")
async def analytics_csv(request: Request):
    v = await require_staff(request, admin=True)
    a, _ = await _analytics(v, _range(request))
    if a is None:
        raise HTTPException(503)
    return av.csv_response(a["csv_name"], aa.CSV_HEAD, a["csv_rows"])


# ---------------------------------------------------------------- the database
@router.get("/admin/database")
async def database(request: Request):
    v = await require_staff(request, admin=True)
    q, with_rows = _get(request, "q")[:80], _get(request, "rows") == "1"
    data = _one(await v.db.rpc("admin_database"), "admin.database_failed")
    db = ad.build(data, q, with_rows, datetime.now(timezone.utc).date()) if data else None
    return await _page(request, v, "admin/database.html", "database", "Database", {
        "db": db, "failed": db is None, "q": q, "with_rows": with_rows})


# ---------------------------------------------------------------- settings
def _refusal(result, fallback: str) -> str:
    """A setting the database refused, in its own words when it explains them."""
    text = result.error.message or ""
    return text[:1].upper() + text[1:] + "." if result.error.code == "22023" and text else fallback


async def _settings(request: Request, v, states: dict | None = None, status_code: int = 200):
    s, people = await asyncio.gather(v.db.rpc("admin_settings"), v.db.rpc("admin_staff"))
    row = _one(s, "admin.settings_failed")
    last = v.user.get("last_sign_in_at")
    staff_rows = [{**m, "role_name": ROLE_NAME.get(m["role"], m["role"]), "since": av.day_text(m["since"]),
                   "you": m["user_id"] == v.id} for m in _rows(people, "admin.staff_failed")]
    context = {
        "s": row, "failed": row is None, "staff": staff_rows, "staff_failed": not people.ok, "TYPES": aset.TYPES,
        "STAFF_ROLES": aset.STAFF_ROLES,
        "me": {"name": v.profile.full_name, "email": v.email, "role": ROLE_NAME.get(v.profile.role, v.profile.role),
               "last": av.long_text(last) if last else "Not recorded"},
    }
    if states:
        context["states"] = states
    return await _page(request, v, "admin/settings.html", "settings", "Settings", context, status_code=status_code)


def _saved(form: str, anchor: str, message: str = aset.SAVED):
    return redirect(f"/admin/settings#{anchor}", {"form": form, "status": "sent", "message": message})


def _not_saved(form: str, message: str, values: dict | None = None) -> dict:
    return {form: {"status": "error", "message": message, "values": values or {}}}


@router.get("/admin/settings")
async def settings_page(request: Request):
    v = await require_staff(request, admin=True)
    return await _settings(request, v)


@router.post("/admin/settings/pitch")
async def save_pitch_rules(request: Request):
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    typed = {"types": many(values, "types"), "max_mb": one(values, "max_mb"), "max_seconds": one(values, "max_seconds")}
    f = aset.parse_pitch_rules(typed["types"], typed["max_mb"], typed["max_seconds"])
    if f.error:
        return await _settings(request, v, _not_saved("pitch", f.error, typed), 400)
    result = await v.db.rpc("admin_set_pitch_rules", f.data)
    if not result.ok:
        log_info("admin.settings_refused", {"form": "pitch", "code": result.error.code})
        return await _settings(request, v, _not_saved("pitch", _refusal(result, "The pitch rules were not saved. Please try again."), typed), 400)
    platform.forget()
    return _saved("pitch", "pitch")


@router.post("/admin/settings/introductions")
async def save_introduction_rules(request: Request):
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    typed = {"on": one(values, "on") == "1", "per_day": one(values, "per_day")}
    f = aset.parse_introduction_rules(typed["on"], typed["per_day"])
    if f.error:
        return await _settings(request, v, _not_saved("introductions", f.error, typed), 400)
    result = await v.db.rpc("admin_set_introduction_rules", f.data)
    if not result.ok:
        log_info("admin.settings_refused", {"form": "introductions", "code": result.error.code})
        return await _settings(request, v, _not_saved(
            "introductions", _refusal(result, "The introduction rules were not saved. Please try again."), typed), 400)
    platform.forget()
    return _saved("introductions", "introductions")


@router.post("/admin/settings/mode")
async def save_mode(request: Request):
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    typed = {"mode": one(values, "mode"), "message": one(values, "message")}
    f = aset.parse_mode(typed["mode"], typed["message"])
    if f.error:
        return await _settings(request, v, _not_saved("mode", f.error, typed), 400)
    result = await v.db.rpc("admin_set_platform_mode", f.data)
    if not result.ok:
        log_info("admin.settings_refused", {"form": "mode", "code": result.error.code})
        return await _settings(request, v, _not_saved("mode", _refusal(result, "The status was not saved. Please try again."), typed), 400)
    platform.forget()
    return _saved("mode", "status")


@router.post("/admin/settings/password")
async def change_password(request: Request):
    """Changes the signed-in admin's own password through Supabase Auth. The password is never logged or shown again."""
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    f = aset.parse_password(one(values, "password"), one(values, "again"))
    if f.error:
        return await _settings(request, v, _not_saved("password", f.error), 400)
    result = await request.app.state.supabase.update_password(v.access_token, f.data["password"])
    if not result.ok:
        log_info("admin.password_refused", {"status": result.error.status, "code": result.error.code})
        return await _settings(request, v, _not_saved("password", aset.password_refusal(result.error.code, result.error.status)), 400)
    log_info("admin.password_changed", {})
    return _saved("password", "account", "Password changed.")


@router.post("/admin/settings/staff")
async def add_staff(request: Request):
    values = await form_data(request)
    v = await require_staff(request, admin=True)
    typed = {"email": one(values, "email"), "role": one(values, "role")}
    f = aset.parse_staff_add(typed["email"], typed["role"])
    if f.error:
        return await _settings(request, v, _not_saved("staff", f.error, typed), 400)
    result = await v.db.rpc("admin_staff_add", f.data)
    if not result.ok:
        log_info("admin.staff_add_refused", {"code": result.error.code})
        return await _settings(request, v, _not_saved("staff", aset.staff_refusal(result.error.message or "", f.data["p_email"]), typed), 400)
    return _saved("staff", "staff", f"Added {f.data['p_email']} as {f.data['p_role']}.")


@router.post("/admin/settings/staff/{user_id}/remove")
async def remove_staff(request: Request, user_id: str):
    await form_data(request)
    v = await require_staff(request, admin=True)
    if not ID.fullmatch(user_id):
        raise HTTPException(404)
    people = {m["user_id"]: m for m in _rows(await v.db.rpc("admin_staff"), "admin.staff_failed")}
    if user_id not in people or user_id == v.id:
        return _saved("staff", "staff", "This person is not on the staff list, or is you.")
    result = await v.db.rpc("admin_staff_remove", {"p_user": user_id})
    if not result.ok:
        log_info("admin.staff_remove_refused", {"code": result.error.code})
        return await _settings(request, v, _not_saved("staff", "The staff list was not changed. Please try again."), 400)
    return _saved("staff", "staff", aset.removed_text(people[user_id]["email"], result.data))


# ---------------------------------------------------------------- the audit log
AUDIT_ORDERS = ("new", "old")
DAY = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
AUDIT_STAFF_ROWS = 1000


def audit_filters(request: Request) -> dict:
    kind, order = _get(request, "kind", "all"), _get(request, "order", "new")
    start, end = _get(request, "from"), _get(request, "to")
    return {"q": _get(request, "q")[:120], "kind": kind if kind in av.KINDS else "all",
            "from": start if DAY.fullmatch(start) else "", "to": end if DAY.fullmatch(end) else "",
            "order": order if order in AUDIT_ORDERS else "new"}


def filter_audit(entries: list[dict], f: dict) -> list[dict]:
    """The audit board's filter, on entries that are newest first."""
    q = f["q"].strip().lower()
    shown = [e for e in entries if (f["kind"] == "all" or e["kind"] == f["kind"])
             and (not f["from"] or e["at"][:10] >= f["from"]) and (not f["to"] or e["at"][:10] <= f["to"])
             and (not q or q in e["search"])]
    return shown[::-1] if f["order"] == "old" else shown


async def _audit_entries(v) -> tuple[list[dict], bool]:
    history, (log, names) = await asyncio.gather(v.db.rpc("admin_register_history"), staff_log(v, AUDIT_STAFF_ROWS))
    hist = _one(history, "admin.history_failed") or {}
    return av.newest_first(av.register_entries(hist) + av.staff_entries(log, names, describe_staff)), not history.ok


@router.get("/admin/audit")
async def audit(request: Request):
    v = await require_staff(request, admin=True)
    entries, failed = await _audit_entries(v)
    f = audit_filters(request)
    shown = filter_audit(entries, f)
    page = av.page_of(shown, av.page_number(_get(request, "page")), PAGE)
    base = {"q": f["q"], "kind": f["kind"], "from": f["from"], "to": f["to"], "order": None if f["order"] == "new" else f["order"]}
    cards = []
    for kind, (label, _) in av.KINDS.items():
        ats = sorted(e["at"] for e in entries if e["kind"] == kind)
        cards.append({"kind": kind, "label": label, "count": len(ats), "on": f["kind"] == kind,
                      "range": f"{av.when_text(ats[0], True)} to {av.when_text(ats[-1], True)}" if ats else "None",
                      "href": av.query("/admin/audit", {**base, "kind": None if f["kind"] == kind else kind, "page": None})})
    subtitle = (f"{av.plural(len(entries), 'entry', 'entries')} from {av.when_text(entries[-1]['at'], True)} to "
                f"{av.when_text(entries[0]['at'], True)}") if entries else "No entries yet"
    return await _page(request, v, "admin/audit.html", "audit", "Audit log", {
        "rows": [{**e, "when": av.when_text(e["at"], e["date_only"]), "kind_text": av.KINDS[e["kind"]][0],
                  "chip": av.KINDS[e["kind"]][1]} for e in page["rows"]],
        "page": page, "cards": cards, "f": f, "failed": failed, "subtitle": subtitle, "KINDS": av.KINDS,
        "count_text": av.shown_text(len(shown), len(entries), "entries"),
        "link": lambda **changes: av.query("/admin/audit", {**base, **changes}), "csv": av.query("/admin/audit.csv", base),
    })


@router.get("/admin/audit.csv")
async def audit_csv(request: Request):
    v = await require_staff(request, admin=True)
    entries, _ = await _audit_entries(v)
    shown = filter_audit(entries, audit_filters(request))
    return av.csv_response("ikonetu-audit-log.csv", ["When", "Who", "Action", "What"],
                           [[e["at"].replace("T", " "), e["who"], av.KINDS[e["kind"]][0], e["text"]] for e in shown])
