"""The activity feed, for founders and approved investors.

The page lists the newest entries and links to older ones, so it works without script. feed-live.js
asks /activity/new every 30 seconds while the page is open and adds what is new at the top. Every
read is made as the person looking, and activity_feed() decides what they may see.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from fastapi import APIRouter, Request
from fastapi.responses import Response

from ..activity import PAGE_SIZE, feed_entry, load_feed
from ..log import log_error
from ..session import RedirectTo, require_founder, require_investor, require_viewer
from ..web import Meta, redirect, render, templates

router = APIRouter()

# A moment as the database writes it, for the page links and the live check.
MOMENT = re.compile(r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}(:?\d{2})?)?")


def _moment(value: str | None) -> str | None:
    value = (value or "").strip()
    return value if MOMENT.fullmatch(value) else None


async def _member(request: Request):
    """An active founder with a venture, or an approved investor. Anyone else goes to their own home."""
    v = await require_viewer(request)
    if v.profile is not None and v.profile.role == "founder":
        await require_founder(request)
        return v, "founder"
    await require_investor(request)
    return v, "investor"


@router.get("/activity")
async def activity_page(request: Request):
    v, role = await _member(request)
    before = _moment(request.query_params.get("before"))
    rows = await load_feed(v.db, before=before)
    if rows is None:
        log_error("activity.read_failed", {"role": role})
    entries = [feed_entry(r, role == "investor") for r in (rows or [])]
    return render(request, "activity/feed.html", {
        "role": role,
        "current": "activity",
        "entries": entries,
        "failed": rows is None,
        "older": entries[-1]["at"] if len(entries) == PAGE_SIZE else None,
        "newest": entries[0]["at"] if entries and not before else None,
        "paged": bool(before),
        "now": datetime.now(timezone.utc),
    }, Meta(title="Activity", noindex=True))


@router.get("/activity/new")
async def activity_new(request: Request):
    """What is new since an entry, as list items for feed-live.js. 204 when there is nothing new.

    A person whose session has ended is sent to sign in, and the script stops when the answer
    does not carry X-Activity-Feed.
    """
    v, role = await _member(request)
    after = _moment(request.query_params.get("after"))
    if after is None:
        return Response(status_code=204, headers={"X-Activity-Feed": "1"})
    rows = await load_feed(v.db, after=after)
    if not rows:
        return Response(status_code=204, headers={"X-Activity-Feed": "1"})
    entries = [feed_entry(r, role == "investor") for r in rows]
    response = templates.TemplateResponse(request, "activity/entries.html", {
        "entries": entries, "now": datetime.now(timezone.utc),
    })
    response.headers["Cache-Control"] = "private, no-cache, no-store, max-age=0, must-revalidate"
    response.headers["X-Activity-Feed"] = "1"
    response.headers["X-Activity-Newest"] = str(entries[0]["at"])
    return response


@router.get("/dashboard/updates")
async def old_updates_page(request: Request):
    """Founders no longer post updates. The old address leads to the feed."""
    raise RedirectTo("/activity")


@router.post("/dashboard/updates")
async def old_post_update(request: Request):
    return redirect("/activity")
