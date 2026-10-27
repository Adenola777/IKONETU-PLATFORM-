"""The investor's pages: sign-up, the waiting page, discovery, a founder profile, the profile form and
the list of requests. Ported from apps/web/app/onboarding/investor and apps/web/app/investor.

Every read and write is made as the signed-in investor, so row level security decides what they
may see. A founder profile they may not see answers 404, as one that does not exist.
"""

from __future__ import annotations

import asyncio
import math
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from starlette.exceptions import HTTPException

from .. import platform
from ..discovery import PAGE_SIZE, filter_count, match_text, parse_filters, query_string, rpc_args
from ..forms import parse_introduction_note
from ..investor import parse_investor_edit, parse_investor_signup
from ..log import log_error, log_info
from ..product import is_shown_status, weeks_text
from ..session import RedirectTo, home_for, require_investor, require_viewer
from ..venture_profile import load_venture_profile
from ..web import Meta, failed, form_data, lower_first, one, redirect, render, sent

router = APIRouter()

ID = re.compile(r"[0-9a-f-]{36}")


def _meta(title: str) -> Meta:
    return Meta(title=title, noindex=True)


def _adult(user: dict) -> bool:
    return (user.get("user_metadata") or {}).get("confirmed_adult") is True


# ---------------------------------------------------------------- sign-up and waiting
def _signup_page(request: Request, v, states: dict | None = None):
    context = {"ask_adult": not _adult(v.user), "name": v.profile.full_name if v.profile else ""}
    if states:
        context["states"] = states
    return render(request, "investor/signup.html", context, _meta("Create your investor profile"))


@router.get("/onboarding/investor")
async def investor_onboarding(request: Request):
    v = await require_viewer(request)
    if v.profile and v.profile.role != "investor":
        raise RedirectTo(home_for(v.profile))
    if v.profile:
        details = await v.db.table("investor_profiles").eq("user_id", v.id).maybe_single("user_id")
        if details.data:
            raise RedirectTo(home_for(v.profile))
    return _signup_page(request, v)


SIGNUP_FAILED = "We could not save your details. Please try again."


@router.post("/onboarding/investor")
async def create_investor(request: Request):
    """Creates the investor's profile as pending, records their consents and saves their details.

    Each step is skipped when it already exists, so a retry is safe.
    """
    values = await form_data(request)
    v = await require_viewer(request)
    if v.profile and v.profile.role != "investor":
        raise RedirectTo("/dashboard")
    parsed = parse_investor_signup(values, _adult(v.user))
    if not parsed.ok:
        return _signup_page(request, v, failed("investor", "Please check the form.", parsed.errors, values))
    rows = parsed.data

    def logged(step: str, error):
        log_error("onboarding.investor_failed", {"step": step, "code": error.code})
        return _signup_page(request, v, failed("investor", SIGNUP_FAILED, values=values))

    if not v.profile:
        made = await v.db.table("profiles").insert({"user_id": v.id, **rows["profile"]})
        if not made.ok:
            return logged("insert profile", made.error)
        agreed = await v.db.table("consents").insert([{"user_id": v.id, **c} for c in rows["consents"]])
        if not agreed.ok:
            return logged("insert consents", agreed.error)
    existing = await v.db.table("investor_profiles").eq("user_id", v.id).maybe_single("user_id")
    if not existing.ok:
        return logged("read investor profile", existing.error)
    if not existing.data:
        saved = await v.db.table("investor_profiles").insert({"user_id": v.id, **rows["investor"]})
        if not saved.ok:
            return logged("insert investor profile", saved.error)
    return redirect("/investor/pending")


@router.get("/investor/pending")
async def investor_pending(request: Request):
    """Where an investor waits for an admin's decision, or learns it was declined."""
    v = await require_viewer(request)
    if v.profile is None or v.profile.role != "investor":
        raise RedirectTo(home_for(v.profile))
    if v.profile.status == "active":
        raise RedirectTo("/investor")
    details = await v.db.table("investor_profiles").eq("user_id", v.id).maybe_single("created_at")
    if not details.data:
        raise RedirectTo("/onboarding/investor")
    return render(request, "investor/pending.html", {
        "declined": v.profile.status == "suspended", "sent_at": details.data["created_at"],
    }, _meta("Your investor account"))


# ---------------------------------------------------------------- discovery
def consistency(active_weeks: int | None) -> str:
    """A card's line on momentum, for example "active in 4 of the last 13 weeks"."""
    return lower_first(weeks_text(active_weeks or 0))


@router.get("/investor")
async def discover(request: Request):
    """Published founder profiles, filtered and sorted by company name. Nothing here is ranked."""
    v = await require_investor(request)
    filters = parse_filters(request.query_params)
    result = await v.db.rpc("discover_ventures", rpc_args(filters))
    rows = [{**r, "areas": [a for a in (r.get("areas") or []) if is_shown_status(a.get("status"))]} for r in (result.data or [])]
    # Each card's muted preview plays from a signed link, made only for the pitches on this page.
    previews: dict[str, dict] = {}
    if rows:
        pitches = await v.db.table("pitches").in_("venture_id", [r["venture_id"] for r in rows]).select(
            "venture_id, storage_path, transcript, duration_seconds"
        )
        found = pitches.data or []
        links = await asyncio.gather(*(v.storage.signed_url("pitches", p["storage_path"], 3600) for p in found))
        for p, link in zip(found, links, strict=True):
            previews[p["venture_id"]] = {"src": link, "transcript": p["transcript"], "duration": float(p["duration_seconds"])}
    total = rows[0]["total_count"] if rows else 0
    filtered = filter_count(filters) > 0
    return render(request, "investor/discover.html", {
        "filters": filters, "chosen": filter_count(filters), "rows": rows, "previews": previews, "total": total,
        "filtered": filtered, "failed": not result.ok, "pages": max(1, math.ceil(total / PAGE_SIZE)),
        "now": datetime.now(timezone.utc), "match_text": match_text, "query_string": query_string, "consistency": consistency,
    }, _meta("Discover founders"))


# ---------------------------------------------------------------- a founder profile
PAUSED = "IkonetU has paused introduction requests for now. Please try again later."


def limit_text(n: int) -> str:
    """Ten requests, or one request, as the investor pages write the daily limit."""
    return f"{platform.number_text(n)} {'request' if n == 1 else 'requests'}"


async def _venture_page(request: Request, v, venture_id: str, states: dict | None = None):
    if not ID.fullmatch(venture_id):
        raise HTTPException(404)
    p = await load_venture_profile(v.db, v.storage, venture_id)
    if not p:
        raise HTTPException(404)
    mine = await v.db.table("introductions").eq("venture_id", venture_id).eq("investor_id", v.id) \
        .order("created_at", ascending=False).limit(1).maybe_single("id, status, created_at, decided_at")
    rules = await platform.rules(request.app.state.supabase)
    context = {"p": p, "venture_id": venture_id, "intro": mine.data, "now": datetime.now(timezone.utc),
               "intros_on": rules.introductions_on}
    if states:
        context["states"] = states
    return render(request, "investor/venture.html", context, _meta("Founder profile"))


@router.get("/investor/ventures/{venture_id}")
async def venture_page(request: Request, venture_id: str):
    v = await require_investor(request)
    return await _venture_page(request, v, venture_id)


@router.post("/investor/ventures/{venture_id}/introduction")
async def request_introduction(request: Request, venture_id: str):
    """An approved investor asks a founder for an introduction. The database fills in who is asking."""
    values = await form_data(request)
    v = await require_investor(request)
    venture = one(values, "venture")
    if not ID.fullmatch(venture):
        return await _venture_page(request, v, venture_id, failed("request", "This founder profile could not be found."))
    parsed = parse_introduction_note(one(values, "note"))
    if not parsed.ok:
        return await _venture_page(request, v, venture_id, failed("request", "Please check your note.", parsed.errors, values))
    result = await v.db.table("introductions").insert({"venture_id": venture, "note": parsed.data["note"]})
    if not result.ok:
        error = result.error
        text = error.message or ""
        limit = re.search(r"limit of (\d+) requests a day", text)
        expected = error.code == "23505" or limit or re.search(r"switched off|not published", text)
        (log_info if expected else log_error)(
            "introduction.request_refused" if expected else "introduction.request_failed", {"venture": venture, "code": error.code}
        )
        if error.code == "23505":
            message = "You have already asked this founder for an introduction."
        elif limit:
            message = f"You have reached the limit of {limit_text(int(limit.group(1)))} a day. Please try again tomorrow."
        elif "switched off" in text:
            message = PAUSED
        elif "not published" in text:
            message = "This founder has hidden their profile."
        else:
            message = "We could not send your request. Please try again."
        return await _venture_page(request, v, venture_id, failed("request", message, values=values))
    # The page then shows the request waiting for the founder.
    return redirect(f"/investor/ventures/{venture_id}")


async def _withdraw(request: Request) -> None:
    """An investor withdraws a request the founder has not answered."""
    v = await require_investor(request)
    intro = one(await form_data(request), "id")
    if not ID.fullmatch(intro):
        return
    result = await v.db.table("introductions").eq("id", intro).update({"status": "withdrawn"})
    if not result.ok:
        log_error("introduction.withdraw_failed", {"introduction": intro, "code": result.error.code})


@router.post("/investor/ventures/{venture_id}/withdraw")
async def withdraw_from_profile(request: Request, venture_id: str):
    await _withdraw(request)
    return redirect(f"/investor/ventures/{venture_id}" if ID.fullmatch(venture_id) else "/investor/introductions")


@router.post("/investor/introductions/withdraw")
async def withdraw_from_list(request: Request):
    await _withdraw(request)
    return redirect("/investor/introductions")


@router.get("/investor/introductions")
async def investor_introductions(request: Request):
    v = await require_investor(request)
    result = await v.db.table("introductions").eq("investor_id", v.id).order("created_at", ascending=False).limit(200) \
        .select("id, venture_id, status, venture_name, founder_name, created_at, decided_at")
    rows = result.data or []
    tab = request.query_params.get("tab", "")
    if tab not in ("all", "waiting", "accepted"):
        tab = "all"
    shown = {"all": rows, "waiting": [r for r in rows if r["status"] == "pending"],
             "accepted": [r for r in rows if r["status"] == "accepted"]}
    rules = await platform.rules(request.app.state.supabase)
    return render(request, "investor/introductions.html", {
        "rows": rows, "shown": shown[tab], "tab": tab, "counts": {k: len(x) for k, x in shown.items()},
        "per_day": limit_text(rules.introductions_per_day), "intros_on": rules.introductions_on,
    }, _meta("Your introductions"))


# ---------------------------------------------------------------- the investor's own profile
async def _profile_page(request: Request, v, states: dict | None = None):
    d = await v.db.table("investor_profiles").eq("user_id", v.id).maybe_single(
        "investor_type, firm, website, based_in, sectors, stages, countries, cheque_size, thesis"
    )
    x = d.data
    initial = {
        "fullName": v.profile.full_name, "investorType": x["investor_type"], "firm": x.get("firm") or "",
        "website": x.get("website") or "", "basedIn": x["based_in"], "sectors": x["sectors"], "stages": x["stages"],
        "countries": x["countries"], "chequeSize": x["cheque_size"], "thesis": x.get("thesis") or "",
    } if x else {"fullName": v.profile.full_name}
    context = {"initial": initial}
    if states:
        context["states"] = states
    return render(request, "investor/profile.html", context, _meta("Your investor profile"))


@router.get("/investor/profile")
async def investor_profile(request: Request):
    v = await require_investor(request)
    return await _profile_page(request, v)


@router.post("/investor/profile")
async def update_investor(request: Request):
    """An approved investor changes their details. A request already sent keeps the name it was sent with."""
    values = await form_data(request)
    v = await require_investor(request)
    parsed = parse_investor_edit(values)
    if not parsed.ok:
        return await _profile_page(request, v, failed("investor", "Please check the form.", parsed.errors, values))
    a = await v.db.table("profiles").eq("user_id", v.id).update(parsed.data["profile"])
    b = await v.db.table("investor_profiles").eq("user_id", v.id).update(parsed.data["investor"])
    if not a.ok or not b.ok:
        log_error("investor.update_failed", {"profile": a.error.code if a.error else None, "investor": b.error.code if b.error else None})
        return await _profile_page(request, v, failed("investor", "We could not save your changes. Please try again.", values=values))
    return sent("/investor/profile", "investor", "Your details are saved.")
