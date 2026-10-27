"""The activity feed: what the system recorded as each venture made progress, in words.

The database writes every entry itself (migration 20261027000001) and activity_feed() decides who
reads which. An entry names the venture and says what happened. It never holds the founder's own
text, the IkonetU Score, or an investor's name or firm: an introduction names the investor's type only.
"""

from __future__ import annotations

from .forms import signal_area
from .product import area_label, country_name, date_text, days_between

PAGE_SIZE = 30

# The investor in an accepted introduction, by type.
INVESTOR_TYPE_PHRASE = {"individual": "an individual investor", "angel": "an angel investor", "fund": "a fund"}

# The icon beside each kind of entry. Evidence takes the icon of its status, as on a profile.
KIND_ICON = {
    "published": "rocket",
    "pitch_added": "video",
    "pitch_replaced": "video",
    "ask_set": "flag",
    "introduction_accepted": "handshake",
}


def entry_icon(row: dict) -> str:
    if row.get("kind") == "evidence_approved":
        return "link" if (row.get("detail") or {}).get("outside") else "shield-check"
    return KIND_ICON.get(row.get("kind"), "activity")


def entry_text(row: dict) -> str:
    """What happened, as one sentence that starts with the venture's name."""
    name = row.get("venture_name") or "A venture"
    kind = row.get("kind")
    detail = row.get("detail") or {}
    if kind == "published":
        return f"{name} published its profile."
    if kind == "pitch_added":
        return f"{name} added a pitch."
    if kind == "pitch_replaced":
        return f"{name} recorded a new pitch."
    if kind == "ask_set":
        return f"{name} set out what it is raising."
    if kind == "evidence_approved":
        area = area_label(signal_area(str(detail.get("signal_code") or ""))) or "an area"
        if detail.get("outside"):
            return f"{name} has third-party evidence in {area}."
        return f"{name} has platform-reviewed evidence in {area}."
    if kind == "introduction_accepted":
        who = INVESTOR_TYPE_PHRASE.get(str(detail.get("investor_type") or ""), "an investor")
        return f"{name} accepted an introduction from {who}."
    return f"{name} made progress."


def ago_text(at, now) -> str:
    """When an entry happened: Today, Yesterday, 3 days ago, and its date once it is older than 30 days."""
    d = days_between(at, now)
    if d == 0:
        return "Today"
    if d == 1:
        return "Yesterday"
    if d <= 30:
        return f"{d} days ago"
    return date_text(at)


def feed_entry(row: dict, can_open: bool) -> dict:
    """One row of activity_feed() as the page shows it. Only investors and staff may open a profile."""
    place = " · ".join(x for x in (row.get("sector"), country_name(row.get("country"))) if x)
    return {
        "id": row["id"],
        "kind": row.get("kind"),
        "text": entry_text(row),
        "place": place,
        "icon": entry_icon(row),
        "at": row["created_at"],
        "href": f"/investor/ventures/{row['venture_id']}" if can_open else None,
    }


async def load_feed(db, *, before: str | None = None, after: str | None = None, venture: str | None = None,
                    limit: int = PAGE_SIZE):
    """Rows of activity_feed(), newest first, read as the person looking. None when the read failed."""
    args: dict = {"p_limit": limit}
    if before:
        args["p_before"] = before
    if after:
        args["p_after"] = after
    if venture:
        args["p_venture"] = venture
    result = await db.rpc("activity_feed", args)
    if not result.ok:
        return None
    return result.data or []
