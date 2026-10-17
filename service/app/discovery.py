"""The discovery filters. Ported from apps/web/lib/discovery.ts.

Choices inside one group widen the list and choices across groups narrow it, as the For
investors page says. The database does the filtering (discover_ventures); this module reads
and writes the query string, so a filtered list has its own address and works without script.
"""

from __future__ import annotations

import math
from urllib.parse import quote_plus

from .forms import js_number
from .product import COUNTRIES, SECTORS, STAGES
from .validate import js_trim

FILTER_GROUPS = (
    {"key": "sector", "label": "Sector", "options": tuple({"value": s, "label": s} for s in SECTORS)},
    {"key": "stage", "label": "Stage", "options": tuple({"value": s["code"], "label": s["label"]} for s in STAGES)},
    {"key": "country", "label": "Geography", "options": tuple({"value": c["code"], "label": c["name"]} for c in COUNTRIES)},
    {"key": "evidence", "label": "Evidence", "options": (
        {"value": "revenue_reviewed", "label": "Revenue reviewed"},
        {"value": "registry_record", "label": "Registry record"},
        {"value": "any_reviewed", "label": "Any reviewed evidence"},
    )},
)

ACTIVITY_OPTIONS = (
    {"value": "", "label": "Any time"},
    {"value": "30", "label": "In the last 30 days"},
    {"value": "90", "label": "In the last 90 days"},
)

PAGE_SIZE = 24


def _list(values: list[str]) -> list[str]:
    """Every value given, split at commas and trimmed, with the empty ones dropped."""
    return [x for x in (js_trim(part) for v in values for part in v.split(",")) if x]


def parse_filters(params) -> dict:
    """Reads the filters from the query string. Unknown values are dropped. `params` is a multi-dict."""
    out: dict = {}
    for g in FILTER_GROUPS:
        allowed = {o["value"] for o in g["options"]}
        chosen: list[str] = []
        for v in _list(params.getlist(g["key"])):
            if v in allowed and v not in chosen:
                chosen.append(v)
        out[g["key"]] = chosen
    activity = next(iter(_list(params.getlist("activity"))), "")
    out["activity"] = activity if activity in ("30", "90") else ""
    first = next(iter(_list(params.getlist("page"))), None)
    page = js_number(first) if first is not None else math.nan
    out["page"] = int(page) if math.isfinite(page) and page.is_integer() and 1 < page < 1000 else 1
    return out


def rpc_args(f: dict) -> dict:
    """The arguments discover_ventures takes. An empty group means no filter."""
    return {
        "p_sectors": f["sector"] or None,
        "p_stages": f["stage"] or None,
        "p_countries": f["country"] or None,
        "p_evidence": f["evidence"] or None,
        "p_active_days": int(f["activity"]) if f["activity"] else None,
        "p_limit": PAGE_SIZE,
        "p_offset": (f["page"] - 1) * PAGE_SIZE,
    }


def query_string(f: dict, page: int = 1) -> str:
    """The query string for a set of filters, as URLSearchParams writes it, without the page unless asked."""
    pairs = [(g["key"], v) for g in FILTER_GROUPS for v in f[g["key"]]]
    if f["activity"]:
        pairs.append(("activity", f["activity"]))
    if page > 1:
        pairs.append(("page", str(page)))
    s = "&".join(f"{quote_plus(k, safe='*')}={quote_plus(v, safe='*')}" for k, v in pairs)
    return f"?{s}" if s else ""


def filter_count(f: dict) -> int:
    return sum(len(f[g["key"]]) for g in FILTER_GROUPS) + (1 if f["activity"] else 0)


def match_text(total: int, filtered: bool) -> str:
    noun = "founder" if total == 1 else "founders"
    if filtered:
        verb = "matches" if total == 1 else "match"
        return f"{total} {noun} {verb} these filters. Sorted by company name."
    verb = "is" if total == 1 else "are"
    return f"{total} {noun} {verb} on IkonetU. Sorted by company name."
