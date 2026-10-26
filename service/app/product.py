"""Names, statuses and wording shared by the signed-in pages. Ported from apps/web/lib/product.ts."""

from __future__ import annotations

from datetime import datetime, timezone

# Founders and investors can be in any country since 21 October 2026.
from .countries import COUNTRIES
from .score_engine.engine import parse_instant

# The sectors a venture and an investor choose from. Discovery filters on them.
SECTORS = ("Fintech", "Agritech", "Edtech", "Health", "Other")
CHEQUE_SIZES = ("Under $25,000", "$25,000 to $100,000", "$100,000 to $500,000", "Over $500,000", "Prefer not to say")
INVESTOR_TYPES = ("individual", "angel", "fund")

STAGES = (
    {"code": "idea", "label": "Idea"},
    {"code": "mvp", "label": "First version"},
    {"code": "revenue", "label": "Earning revenue"},
    {"code": "scaling", "label": "Scaling"},
)

# The eleven areas of evidence, in the order of the score engine's rubric v3. The product area
# holds both pathways, Technical Output and Business Operations, because the score counts
# whichever of the two is higher.
AREAS = (
    {"code": "identity", "label": "Identity", "categories": ("identity",)},
    {"code": "business", "label": "Registration", "categories": ("business",)},
    {"code": "infrastructure", "label": "Business tools", "categories": ("infrastructure",)},
    {"code": "team", "label": "Team", "categories": ("team",)},
    {"code": "financial", "label": "Financial", "categories": ("financial",)},
    {"code": "academic", "label": "Academic", "categories": ("academic",)},
    {"code": "output", "label": "Product or operations", "categories": ("technical", "operations")},
    {"code": "traction", "label": "Traction", "categories": ("traction",)},
    {"code": "awards", "label": "Recognition", "categories": ("awards",)},
    {"code": "governance", "label": "Governance", "categories": ("governance",)},
    {"code": "media", "label": "Pitch and media", "categories": ("media",)},
)
AREA_COUNT = len(AREAS)


def country_name(code: str | None) -> str:
    return next((c["name"] for c in COUNTRIES if c["code"] == code), code or "")


def stage_label(code: str) -> str:
    return next((s["label"] for s in STAGES if s["code"] == code), code)


def area_of(category: str) -> str:
    """The area a rubric category belongs to."""
    return next((a["code"] for a in AREAS if category in a["categories"]), category)


def area_label(code: str) -> str:
    """The area's name, for an area or a rubric category."""
    area = area_of(code)
    return next((a["label"] for a in AREAS if a["code"] == area), code)


# The three statuses an investor sees. The database decides which one applies
# (venture_evidence and discover_ventures): third_party for evidence approved from a
# registry or other outside source, reviewed for evidence an IkonetU reviewer approved,
# and submitted for evidence nobody has decided yet.
STATUS = {
    "third_party": {
        "name": "Third-party evidence available", "chip": "chip-3p", "icon": "link",
        "means": "An outside source backs it. The outside source has not assessed the company.",
    },
    "reviewed": {
        "name": "Platform reviewed", "chip": "chip-ok", "icon": "shield-check",
        "means": "An IkonetU reviewer compared it with its source. A review is not an audit, a valuation or an endorsement.",
    },
    "submitted": {
        "name": "Founder submitted", "chip": "chip-n", "icon": "upload",
        "means": "IkonetU has not checked it. Treat it as the founder's own statement.",
    },
}
RANK = {"third_party": 3, "reviewed": 2, "submitted": 1}


def is_shown_status(v: object) -> bool:
    return v in STATUS


# The readiness check, the same on the website and in the app. An area is strong when it
# holds platform-reviewed or third-party evidence, building when it holds founder-submitted
# evidence only, and a gap when it holds none. The owner set this on 15 October 2026.
LEVEL = {
    "strong": {"name": "Strong", "chip": "chip-ok", "means": "Platform-reviewed or third-party evidence"},
    "building": {"name": "Building", "chip": "chip-n", "means": "Founder-submitted evidence only"},
    "gap": {"name": "Gap", "chip": "chip-none", "means": "No evidence yet"},
}


def level_of(status: str | None) -> str:
    if status in ("third_party", "reviewed"):
        return "strong"
    if status == "submitted":
        return "building"
    return "gap"


def area_cells(areas: list[dict]) -> list[dict]:
    """One entry per area, in rubric order, with its level and how many pieces of evidence it holds.

    `areas` holds one entry per rubric category or per area. An area with two categories takes
    the best status of the two and adds their counts.
    """
    cells = []
    for a in AREAS:
        found = [x for x in areas if x["category"] in a["categories"] or x["category"] == a["code"]]
        best = max((x["status"] for x in found), key=lambda st: RANK.get(st, 0), default=None)
        cells.append({
            "code": a["code"], "label": a["label"], "level": level_of(best), "count": sum(x["count"] for x in found),
        })
    return cells


def readiness_text(areas: list[dict]) -> str:
    """The readiness check in words, so the meter's colours are never the only signal."""
    cells = area_cells(areas)

    def n(level: str) -> int:
        return sum(1 for c in cells if c["level"] == level)
    if n("gap") == AREA_COUNT:
        return "No evidence yet, so all eleven areas are gaps."
    return f"Strong in {n('strong')} of {AREA_COUNT} areas, building in {n('building')}, with a gap in {n('gap')}."


def summarise_areas(rows: list[dict]) -> list[dict]:
    """The best status and the count of each area, from venture_evidence rows (category, shown_status)."""
    best: dict[str, dict] = {}
    for e in rows:
        status = e.get("shown_status")
        if not is_shown_status(status):
            continue
        had = best.get(e["category"])
        best[e["category"]] = {
            "category": e["category"],
            "status": had["status"] if had and RANK[had["status"]] >= RANK[status] else status,
            "count": (had["count"] if had else 0) + 1,
        }
    return list(best.values())


def _when(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    return parse_instant(value) if value else None


def days_between(then, now: datetime) -> int:
    """Whole days between two moments, counted in UTC calendar days."""
    a = _when(then).astimezone(timezone.utc).date()
    b = now.astimezone(timezone.utc).date()
    return max(0, (b - a).days)


def activity_text(last, now: datetime) -> str:
    """ "Updated today", "Updated yesterday" or "Updated 9 days ago"."""
    if not last:
        return "No activity yet"
    d = days_between(last, now)
    if d == 0:
        return "Updated today"
    if d == 1:
        return "Updated yesterday"
    return f"Updated {d} days ago"


def is_recent(last, now: datetime, days: int = 30) -> bool:
    return bool(last) and days_between(last, now) <= days


def clock_text(seconds) -> str:
    """A pitch length as m:ss, for example 0:58."""
    try:
        n = float(seconds or 0)
    except (TypeError, ValueError):
        n = 0.0
    s = max(0, int(n + 0.5) if n >= 0 else 0)
    return f"{s // 60}:{s % 60:02d}"


MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")


def date_text(iso) -> str:
    """A date as 15 October 2026, in UK English, read in UTC."""
    if not iso:
        return ""
    d = _when(iso)
    if d is None:
        return ""
    d = d.astimezone(timezone.utc)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def day_month(iso) -> str:
    """A date as 15 Oct, for the narrow places a card has room for, read in UTC."""
    d = _when(iso) if iso else None
    if d is None:
        return ""
    d = d.astimezone(timezone.utc)
    return f"{d.day} {MONTHS[d.month - 1][:3]}"


def initials(name: str | None) -> str:
    """The first letters of the first two words of a name, for an avatar. A missing name gives a question mark."""
    words = [w for w in (name or "").split() if w[:1].isalpha()]
    return "".join(w[0] for w in words[:2]).upper() or "?"


INVESTOR_TYPE_NAME = {"individual": "Individual investor", "angel": "Angel investor", "fund": "Fund investor"}

# Why each area matters to an investor. The founder's next steps use the same sentences.
AREA_WHY = {
    "identity": "Investors want to know who stands behind the company.",
    "business": "A registered company with a tax number can sign contracts and take investment.",
    "infrastructure": "Working business tools show that the company runs day to day.",
    "team": "Investors back people, so they want to see who is building the company.",
    "financial": "Investors can check numbers that are written down.",
    "academic": "Study and training show the skills the founder brings.",
    "output": "A product or a working operation is easier to believe than a description.",
    "traction": "Customers and partners show that the market wants what the company sells.",
    "awards": "Outside recognition shows that others have judged the work.",
    "governance": "Good governance lowers the risk of backing the company.",
    "media": "A clear pitch and visible progress let investors check what the founder says.",
}


def why_it_matters(category: str) -> str:
    return AREA_WHY[area_of(category)]


def evidence_added_text(items: list[dict], now: datetime) -> str:
    """The evidence added in the last 90 days, for example "7 pieces in 90 days, in 7 of 11 areas"."""
    recent = [e for e in items if days_between(e["createdAt"], now) <= 90]
    if not recent:
        return "None in 90 days"
    areas = len({area_of(e["category"]) for e in recent})
    return f"{len(recent)} {'piece' if len(recent) == 1 else 'pieces'} in 90 days, in {areas} of {AREA_COUNT} areas"


def momentum(update_dates: list[str], now: datetime) -> dict:
    """Momentum, as the website describes it: recency, consistency and evidence added.

    Consistency counts progress updates in the last 90 days, and the strip marks each of
    the last 13 weeks that had an update. Momentum has no streaks or points of its own.
    """
    days = [days_between(d, now) for d in update_dates]
    in90 = sum(1 for d in days if d <= 90)
    weeks = [{"ago": 12 - i, "active": any(d // 7 == 12 - i for d in days)} for i in range(13)]
    return {
        "in90": in90,
        "consistencyText": "No updates in 90 days" if in90 == 0 else f"{in90} {'update' if in90 == 1 else 'updates'} in 90 days",
        "weeks": weeks,
        "activeWeeks": sum(1 for w in weeks if w["active"]),
    }
