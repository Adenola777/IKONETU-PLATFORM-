"""The founder's pages: onboarding, the dashboard, the pitch, evidence, updates and the preview.

Ported from apps/web/app/onboarding and apps/web/app/dashboard. Every read and write is made as
the signed-in founder, so row level security applies. A form that is refused shows the page
again with the errors and what was typed; a form that saved sends the browser back to the page
with a short confirmation, so reloading the page does not send the form twice.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from starlette.datastructures import UploadFile

from ..config import settings
from ..forms import (
    parse_evidence,
    parse_onboarding,
    parse_pitch,
    parse_transcript,
    parse_update,
    parse_venture,
    signal_area,
    signal_label,
    signal_options,
)
from ..guards import is_repeat, request_key
from ..log import log_error, log_info
from ..product import country_name, stage_label, summarise_areas, why_it_matters
from ..score_engine import RUBRIC_V3
from ..score_view import area_shares, league_name, monthly_record, next_league_text, radar
from ..scoring import EVIDENCE_COLUMNS, next_steps, record_venture_score, venture_score
from ..session import RedirectTo, current_user, home_for, require_founder, require_viewer
from ..venture_profile import load_venture_profile
from ..web import Meta, failed, form_data, one, redirect, render, sent, set_flash

router = APIRouter()

SIGNAL_CODES = {s.code for s in RUBRIC_V3.signals if s.offered}
UPDATE_ID = re.compile(r"[0-9a-f-]{36}")


def _meta(title: str) -> Meta:
    return Meta(title=title, noindex=True)


def now_iso() -> str:
    """The time now as JavaScript's toISOString() writes it."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _typed(raw: dict) -> dict[str, str]:
    """What the person typed, one value per field, so a form can show it again."""
    return {k: one(raw, k) for k in raw}


# ---------------------------------------------------------------- onboarding
@router.get("/onboarding")
async def onboarding(request: Request):
    """The first step after sign-in: a person says whether they are a founder or an investor.

    The choice comes back here as ?role=, so the form works without script, and sends the person to
    that sign-up. Anything else shows the choice again.
    """
    v = await require_viewer(request)
    if v.profile:
        if v.profile.role == "founder":
            ventures = await v.db.table("ventures").eq("founder_id", v.id).limit(1).select("id")
            if not ventures.data:
                raise RedirectTo("/onboarding/founder")
        raise RedirectTo(home_for(v.profile))
    chosen = request.query_params.get("role")
    if chosen in ("founder", "investor"):
        raise RedirectTo(f"/onboarding/{chosen}")
    return render(request, "onboarding/choice.html", {}, _meta("Join IkonetU"))


def _onboarding_page(request: Request, ask_adult: bool, states: dict | None = None):
    context = {"ask_adult": ask_adult, **({"states": states} if states else {})}
    return render(request, "onboarding/founder.html", context, _meta("Create your founder profile"))


def _adult(user: dict) -> bool:
    return (user.get("user_metadata") or {}).get("confirmed_adult") is True


@router.get("/onboarding/founder")
async def founder_onboarding(request: Request):
    v = await require_viewer(request)
    if v.profile and v.profile.role != "founder":
        raise RedirectTo(home_for(v.profile))
    if v.profile:
        ventures = await v.db.table("ventures").eq("founder_id", v.id).limit(1).select("id")
        if ventures.data:
            raise RedirectTo("/dashboard")
    return _onboarding_page(request, ask_adult=not _adult(v.user))


ONBOARDING_FIELDS = (
    "fullName", "country", "city", "institution", "graduateStatus", "bio",
    "ventureName", "sector", "stage", "description", "ask", "website", "linkedin", "x", "instagram",
)
ONBOARDING_FAILED = "We could not save your details. Please try again."


@router.post("/onboarding/founder")
async def complete_onboarding(request: Request):
    """Creates the founder's profile, records their consents and creates their first venture.

    Each step is skipped when it already exists, so a retry after a failure is safe.
    """
    raw = await form_data(request)
    values = {k: one(raw, k) for k in ONBOARDING_FIELDS}
    supabase = request.app.state.supabase
    if supabase is None:
        return _onboarding_page(request, True, failed("onboarding", ONBOARDING_FAILED, values=values))
    found = await current_user(request, supabase)
    if found is None:
        raise RedirectTo("/signin")
    user, access = found
    adult = _adult(user)

    parsed = parse_onboarding({k: one(raw, k) for k in raw}, adult)
    if not parsed.ok:
        return _onboarding_page(request, not adult, failed("onboarding", "Please check the form.", parsed.errors, values))
    rows = parsed.data
    db = supabase.as_user(access)

    def logged(step: str, error):
        log_error("onboarding.founder_failed", {"step": step, "code": error.code})
        return _onboarding_page(request, not adult, failed("onboarding", ONBOARDING_FAILED, values=values))

    existing = await db.table("profiles").eq("user_id", user["id"]).maybe_single("user_id")
    if not existing.ok:
        return logged("read profile", existing.error)
    if not existing.data:
        # The founder confirmed being a student founder on this form, so the profile records when.
        created = await db.table("profiles").insert({"user_id": user["id"], **rows["profile"], "student_declared_at": now_iso()})
        if not created.ok:
            return logged("insert profile", created.error)
        agreed = await db.table("consents").insert([{"user_id": user["id"], **c} for c in rows["consents"]])
        if not agreed.ok:
            return logged("insert consent", agreed.error)

    ventures = await db.table("ventures").eq("founder_id", user["id"]).limit(1).select("id")
    if not ventures.ok:
        return logged("read ventures", ventures.error)
    if not ventures.data:
        created = await db.table("ventures").insert({"founder_id": user["id"], **rows["venture"]})
        if not created.ok:
            return logged("insert venture", created.error)
    return redirect("/dashboard")


@router.get("/suspended")
async def suspended(request: Request):
    """Where a suspended founder or staff member lands."""
    v = await require_viewer(request)
    p = v.profile
    if p is None or p.role == "investor" or p.status == "active":
        raise RedirectTo(home_for(p))
    return render(request, "founder/suspended.html", {}, _meta("Your account is suspended"))


# ---------------------------------------------------------------- dashboard
async def _dashboard(request: Request, v, venture: dict, states: dict | None = None):
    db = v.db
    pitch, evidence, updates, requests, shown, snapshots = await asyncio.gather(
        db.table("pitches").eq("venture_id", venture["id"]).maybe_single("duration_seconds, updated_at"),
        db.table("evidence").eq("venture_id", venture["id"]).select(EVIDENCE_COLUMNS),
        db.table("venture_updates").eq("venture_id", venture["id"]).order("created_at", ascending=False).limit(1)
        .select("created_at"),
        db.table("introductions").eq("founder_id", v.id).eq("status", "pending").select("id"),
        # The readiness check reads the evidence the way investors see it, so the two always agree.
        db.rpc("venture_evidence", {"p_venture": venture["id"]}),
        db.table("score_snapshots").eq("venture_id", venture["id"]).order("month", ascending=False).limit(12)
        .select("month, total, league"),
    )
    own = evidence.data or []
    # The score is worked out here from the founder's evidence, with the same engine and rules
    # record_venture_score uses, so the dashboard is current even when a recording is late.
    score = venture_score(own)
    shares = area_shares(score)
    steps = [
        {"code": a.code, "label": a.label, "category": a.category, "gain": max(1, int(a.estimated_gain + 0.5)),
         "hint": RUBRIC_V3.signal(a.code).hint, "why": why_it_matters(a.category)}
        for a in next_steps(own)
    ]
    context = {
        "profile": v.profile,
        "venture": venture,
        "waiting": len(requests.data or []),
        "held": bool(venture.get("hidden_at")),
        "published": bool(venture.get("published_at")),
        "has_pitch": bool(pitch.data),
        "areas": summarise_areas(shown.data or []),
        "score": score,
        "league": league_name(score.league),
        "next_league": next_league_text(score.total),
        "shares": shares,
        "chart": radar(shares),
        "record": monthly_record(snapshots.data or []),
        "steps": steps,
        "evidence_count": len(own),
        "reviewed": sum(1 for e in own if e["status"] == "approved"),
        "last_update": (updates.data or [{}])[0].get("created_at") if updates.data else None,
        "country": country_name(venture.get("country")),
        "stage": stage_label(venture["stage"]),
        "now": datetime.now(timezone.utc),
    }
    if states:
        context["states"] = states
    return render(request, "founder/dashboard.html", context, _meta("Your dashboard"))


@router.get("/dashboard")
async def dashboard(request: Request):
    v, venture = await require_founder(request)
    return await _dashboard(request, v, venture)


@router.post("/dashboard/publish")
async def set_published(request: Request):
    """Publishes the profile to approved investors, or hides it.

    The database refuses to publish a venture without a pitch, or one that IkonetU has hidden
    until an admin lifts the hold.
    """
    v, venture = await require_founder(request)
    publish = one(await form_data(request), "publish") == "yes"
    result = await v.db.table("ventures").eq("id", venture["id"]).update({"published_at": now_iso() if publish else None})
    if not result.ok:
        expected = re.search(r"add a pitch|lifts the hold", result.error.message or "")
        (log_info if expected else log_error)("venture.publish_failed", {"venture": venture["id"], "code": result.error.code})
    return redirect("/dashboard")


@router.post("/dashboard/venture")
async def update_venture(request: Request):
    """Changes the venture's details."""
    values = _typed(await form_data(request))
    v, venture = await require_founder(request)
    parsed = parse_venture(values.get("name", ""), values.get("sector", ""), values.get("stage", ""),
                           values.get("description", ""), values.get("website", ""), values.get("ask", ""))
    if not parsed.ok:
        return await _dashboard(request, v, venture, failed("venture", "Please check the form.", parsed.errors, values))
    result = await v.db.table("ventures").eq("id", venture["id"]).update(parsed.data)
    if not result.ok:
        log_error("venture.update_failed", {"venture": venture["id"], "code": result.error.code})
        return await _dashboard(request, v, venture,
                                failed("venture", "We could not save the changes. Please try again.", values=values))
    return sent("/dashboard", "venture", "Your venture's details are saved.")


# ---------------------------------------------------------------- pitch
async def _pitch_page(request: Request, v, venture: dict, states: dict | None = None):
    pitch = await v.db.table("pitches").eq("venture_id", venture["id"]).maybe_single(
        "storage_path, duration_seconds, transcript, updated_at"
    )
    signed = await v.storage.signed_url("pitches", pitch.data["storage_path"], 3600) if pitch.data else None
    context = {
        "venture": venture, "pitch": pitch.data, "signed": signed, "user_id": v.id,
        "storage_url": settings.supabase_url or "", "storage_key": settings.supabase_key or "",
    }
    if states:
        context["states"] = states
    return render(request, "founder/pitch.html", context, _meta("Your pitch"))


@router.get("/dashboard/pitch")
async def pitch_page(request: Request):
    v, venture = await require_founder(request)
    return await _pitch_page(request, v, venture)


@router.post("/dashboard/pitch/token")
async def pitch_token(request: Request):
    """The founder's own access token, for the browser to upload the video to their folder.

    The session cookies are HTTP-only, so the page cannot read the token itself. supabase-js
    in the Next.js app read the same token from its cookie to upload the video. The answer is
    only readable by this site's own pages.
    """
    v, _ = await require_founder(request)
    return JSONResponse({"token": v.access_token}, headers={"Cache-Control": "no-store"})


@router.post("/dashboard/pitch/record")
async def record_pitch(request: Request):
    """Records a pitch the browser has just uploaded to the founder's own folder.

    A new pitch replaces the old one, and the old file is removed. Row level security checks
    that the path is in the founder's folder.
    """
    v, venture = await require_founder(request)
    try:
        body = await request.json()
    except ValueError:
        body = None
    parsed = parse_pitch(body)
    if not parsed.ok:
        message = next(iter(parsed.errors.values()), "Please check the pitch.")
        return JSONResponse({"status": "error", "message": message, "errors": parsed.errors})
    p = parsed.data
    if not p["path"].startswith(f"{v.id}/"):
        return JSONResponse({"status": "error", "message": "The upload did not finish. Please try again.", "errors": {}})

    old = await v.db.table("pitches").eq("venture_id", venture["id"]).maybe_single("storage_path")
    row = {
        "storage_path": p["path"], "mime_type": p["mimeType"], "size_bytes": p["size"],
        "duration_seconds": math.floor(p["duration"] * 10 + 0.5) / 10, "transcript": p["transcript"],
    }
    if old.data:
        saved = await v.db.table("pitches").eq("venture_id", venture["id"]).update(row)
    else:
        saved = await v.db.table("pitches").insert({"venture_id": venture["id"], **row})
    if not saved.ok:
        log_error("pitch.save_failed", {"venture": venture["id"], "code": saved.error.code})
        await v.storage.remove("pitches", [p["path"]])
        return JSONResponse({"status": "error", "message": "We could not save your pitch. Please try again.", "errors": {}})
    if old.data and old.data["storage_path"] != p["path"]:
        await v.storage.remove("pitches", [old.data["storage_path"]])
    response = JSONResponse({"status": "sent", "message": "Your pitch is saved."})
    # The browser loads the page again after the save, and the page shows the confirmation once.
    set_flash(response, {"form": "upload", "status": "sent", "message": "Your pitch is saved."})
    return response


@router.post("/dashboard/pitch/transcript")
async def save_transcript(request: Request):
    """Changes the transcript of the current pitch, and with it the captions."""
    values = _typed(await form_data(request))
    v, venture = await require_founder(request)
    parsed = parse_transcript(values.get("transcript", ""))
    if not parsed.ok:
        return await _pitch_page(request, v, venture, failed("transcript", "Please check the transcript.", parsed.errors, values))
    result = await v.db.table("pitches").eq("venture_id", venture["id"]).update(parsed.data, count=True)
    if not result.ok or not result.count:
        return await _pitch_page(request, v, venture,
                                 failed("transcript", "We could not save the transcript. Please try again.", values=values))
    return sent("/dashboard/pitch", "transcript", "The transcript and captions are saved.")


@router.post("/dashboard/pitch/remove")
async def remove_pitch(request: Request):
    """Removes the pitch. A published profile is hidden first, because a profile needs a pitch."""
    v, venture = await require_founder(request)
    old = await v.db.table("pitches").eq("venture_id", venture["id"]).maybe_single("storage_path")
    if not old.data:
        return redirect("/dashboard/pitch")
    if venture.get("published_at"):
        await v.db.table("ventures").eq("id", venture["id"]).update({"published_at": None})
    gone = await v.db.table("pitches").eq("venture_id", venture["id"]).delete()
    if not gone.ok:
        log_error("pitch.remove_failed", {"venture": venture["id"], "code": gone.error.code})
        return redirect("/dashboard/pitch")
    await v.storage.remove("pitches", [old.data["storage_path"]])
    return redirect("/dashboard/pitch")


# ---------------------------------------------------------------- evidence
def founder_status(r: dict) -> dict:
    """What the founder sees about each item. Investors see less: venture_evidence decides that."""
    status = r["status"]
    if status == "approved" and r.get("lane") == "self":
        return {"text": "Your own statement. It counts at 60% of its points without a review, and investors do not see it.",
                "investors": None}
    if status == "approved":
        if r.get("lane") in ("government", "source"):
            return {"text": "Approved from an outside source.", "investors": "third_party"}
        return {"text": "Approved by an IkonetU reviewer.", "investors": "reviewed"}
    if status == "needs_more":
        return {"text": "A reviewer asked for more. Investors do not see this item. Add the evidence again with what was asked for.",
                "investors": None}
    if status == "rejected":
        return {"text": "Not accepted. Investors do not see this item.", "investors": None}
    if status == "expired":
        return {"text": "Expired. Investors no longer see this item.", "investors": None}
    return {"text": "Waiting for a reviewer.", "investors": "submitted"}


def _asked_signal(request: Request) -> str:
    asked = request.query_params.get("signal", "")
    return asked if asked in SIGNAL_CODES else ""


async def _evidence_page(request: Request, v, venture: dict, states: dict | None = None):
    signal = _asked_signal(request)
    result = await v.db.table("evidence").eq("venture_id", venture["id"]).order("created_at", ascending=False).select(
        "id, signal_code, status, lane, summary, source_ref, public_note, reason, decided_at, created_at, evidence_files(id)"
    )
    rows = [
        {**r, "shown": founder_status(r), "area": signal_area(r["signal_code"]), "label": signal_label(r["signal_code"])}
        for r in (result.data or [])
    ]
    context = {"rows": rows, "signal": signal, "signal_options": signal_options(), "new_key": str(uuid.uuid4()),
               "categories": RUBRIC_V3.categories}
    if states:
        context["states"] = states
    return render(request, "founder/evidence.html", context, _meta("Your evidence"))


@router.get("/dashboard/evidence")
async def evidence_page(request: Request):
    v, venture = await require_founder(request)
    return await _evidence_page(request, v, venture)


EVIDENCE_ADDED = "Your evidence is added. A reviewer will look at it, and its status shows below."
STATEMENT_ADDED = "Your statement is added, and your score includes it."


@router.post("/dashboard/evidence")
async def submit_evidence(request: Request):
    """Adds one piece of evidence.

    Its files go to the founder's own folder in the private evidence bucket, each with a SHA-256
    taken here on the server, so a reviewer can spot the same file used twice. Investors never
    see the files. The evidence and its file records are saved together by submit_evidence(),
    in one transaction. If that fails, the files just uploaded are removed, so nothing is left
    half saved. The form's request key makes a second copy of the same submission a no-op, and
    it is checked before any file is uploaded.
    """
    form = await request.form()
    values = {k: str(form.get(k)) for k in form.keys() if k not in ("files", "requestKey") and isinstance(form.get(k), str)}
    v, venture = await require_founder(request)
    here = request.url.path + (f"?{request.url.query}" if request.url.query else "")
    key = request_key(form.get("requestKey") if isinstance(form.get("requestKey"), str) else None)
    files = [f for f in form.getlist("files") if isinstance(f, UploadFile) and (f.size or 0) > 0]
    parsed = parse_evidence(values.get("signal", ""), values.get("summary", ""), values.get("link", ""),
                            [{"name": f.filename, "type": f.content_type or "", "size": f.size or 0} for f in files])
    if not parsed.ok:
        return await _evidence_page(request, v, venture, failed("evidence", "Please check the form.", parsed.errors, values))
    if parsed.data["statement"]:
        return await _declare(request, v, venture, parsed.data, key, here, values)

    if key:
        seen = await v.db.table("evidence").eq("venture_id", venture["id"]).eq("request_key", key).maybe_single("id")
        if seen.data:
            return sent(here, "evidence", EVIDENCE_ADDED)

    stored: list[dict] = []

    async def remove_stored():
        if not stored:
            return
        gone = await v.storage.remove("evidence", [s["storage_path"] for s in stored])
        if not gone.ok:
            log_error("evidence.cleanup_failed", {"venture": venture["id"], "files": len(stored), "code": gone.error.message})

    for f in files:
        content = await f.read()
        path = f"{v.id}/{uuid.uuid4()}"
        up = await v.storage.upload("evidence", path, content, f.content_type or "")
        if not up.ok:
            log_error("evidence.upload_failed", {"venture": venture["id"], "code": up.error.message})
            await remove_stored()
            return await _evidence_page(request, v, venture,
                                        failed("evidence", "A file did not upload. Please try again.", values=values))
        stored.append({"storage_path": path, "sha256": hashlib.sha256(content).hexdigest(),
                       "mime_type": f.content_type or "", "size_bytes": len(content)})

    made = await v.db.rpc("submit_evidence", {
        "p_venture": venture["id"], "p_signal": parsed.data["signal"], "p_summary": parsed.data["summary"],
        "p_link": parsed.data["link"], "p_request_key": key, "p_files": stored,
    })
    if not made.ok:
        await remove_stored()
        if is_repeat(made.error):
            return sent(here, "evidence", EVIDENCE_ADDED)
        log_error("evidence.save_failed", {"venture": venture["id"], "code": made.error.code})
        return await _evidence_page(request, v, venture,
                                    failed("evidence", "We could not save the evidence. Please try again.", values=values))
    return sent(here, "evidence", EVIDENCE_ADDED)


async def _declare(request: Request, v, venture: dict, data: dict, key: str | None, here: str, values: dict):
    """Adds the founder's own statement for a self-declared signal through declare_evidence(), which
    approves it at once in the self lane. The score is then recorded by the server's own service
    role, because a founder may not record a score. If that fails, the venture stays on the staff
    list of scores to update, and the founder's dashboard already counts the statement."""
    made = await v.db.rpc("declare_evidence", {
        "p_venture": venture["id"], "p_signal": data["signal"], "p_summary": data["summary"], "p_request_key": key,
    })
    if not made.ok:
        if is_repeat(made.error):
            return sent(here, "evidence", STATEMENT_ADDED)
        log_error("evidence.declare_failed", {"venture": venture["id"], "code": made.error.code})
        return await _evidence_page(request, v, venture,
                                    failed("evidence", "We could not save the statement. Please try again.", values=values))
    supabase = request.app.state.supabase
    server = supabase.as_service() if supabase else None
    if server is None:
        log_error("score.record_failed", {"venture": venture["id"], "attempts": 0, "code": "no_service_role"})
    else:
        await record_venture_score(server, venture["id"], made.data if isinstance(made.data, str) else None)
    return sent(here, "evidence", STATEMENT_ADDED)


# ---------------------------------------------------------------- updates
async def _updates_page(request: Request, v, venture: dict, states: dict | None = None):
    result = await v.db.table("venture_updates").eq("venture_id", venture["id"]).order("created_at", ascending=False) \
        .limit(100).select("id, body, created_at")
    context = {"rows": result.data or [], "new_key": str(uuid.uuid4()), "now": datetime.now(timezone.utc)}
    if states:
        context["states"] = states
    return render(request, "founder/updates.html", context, _meta("Progress updates"))


@router.get("/dashboard/updates")
async def updates_page(request: Request):
    v, venture = await require_founder(request)
    return await _updates_page(request, v, venture)


@router.post("/dashboard/updates")
async def post_update(request: Request):
    raw = await form_data(request)
    values = {k: one(raw, k) for k in raw if k != "requestKey"}
    v, venture = await require_founder(request)
    parsed = parse_update(values.get("body", ""))
    if not parsed.ok:
        return await _updates_page(request, v, venture, failed("update", "Please check the update.", parsed.errors, values))
    result = await v.db.table("venture_updates").insert({
        "venture_id": venture["id"], "body": parsed.data["body"], "request_key": request_key(one(raw, "requestKey")),
    })
    if is_repeat(result.error):
        return sent("/dashboard/updates", "update", "Your update is posted.")
    if not result.ok:
        log_error("update.post_failed", {"venture": venture["id"], "code": result.error.code})
        return await _updates_page(request, v, venture,
                                   failed("update", "We could not post the update. Please try again.", values=values))
    return sent("/dashboard/updates", "update", "Your update is posted.")


@router.post("/dashboard/updates/remove")
async def remove_update(request: Request):
    v, venture = await require_founder(request)
    update_id = one(await form_data(request), "id")
    if UPDATE_ID.fullmatch(update_id):
        result = await v.db.table("venture_updates").eq("id", update_id).eq("venture_id", venture["id"]).delete()
        if not result.ok:
            log_error("update.remove_failed", {"venture": venture["id"], "code": result.error.code})
    return redirect("/dashboard/updates")


# ---------------------------------------------------------------- preview
@router.get("/dashboard/preview")
async def preview(request: Request):
    """The founder's own profile, laid out exactly as approved investors see it."""
    v, venture = await require_founder(request)
    p = await load_venture_profile(v.db, v.storage, venture["id"])
    return render(request, "founder/preview.html", {"venture": venture, "p": p, "now": datetime.now(timezone.utc)},
                  _meta("What investors see"))
