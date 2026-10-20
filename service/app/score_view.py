"""How the founder's dashboard shows the IkonetU Score: the league, the radar chart and the monthly record."""

from __future__ import annotations

import math

from .product import AREAS, MONTHS
from .score_engine import LEAGUE_THRESHOLDS, RUBRIC_V3, ScoreResult
from .score_engine.engine import parse_instant

LEAGUES = (
    {"code": "EARLY", "name": "Early", "low": 0, "high": LEAGUE_THRESHOLDS["RISING"] - 1},
    {"code": "RISING", "name": "Rising", "low": LEAGUE_THRESHOLDS["RISING"], "high": LEAGUE_THRESHOLDS["INVESTABLE"] - 1},
    {"code": "INVESTABLE", "name": "Investable", "low": LEAGUE_THRESHOLDS["INVESTABLE"], "high": LEAGUE_THRESHOLDS["ELITE"] - 1},
    {"code": "ELITE", "name": "Elite", "low": LEAGUE_THRESHOLDS["ELITE"], "high": 1000},
)


def league_name(code: str) -> str:
    return next((lg["name"] for lg in LEAGUES if lg["code"] == code), code.title())


def next_league_text(total: int) -> str:
    """How far the score is from the next league, for example "189 points to Investable"."""
    for lg in LEAGUES[1:]:
        if total < lg["low"]:
            gap = lg["low"] - total
            return f"{gap} {'point' if gap == 1 else 'points'} to {lg['name']}"
    return "The top league"


def area_shares(score: ScoreResult) -> list[dict]:
    """One entry per area, in rubric order: the share of its maximum the area has earned.

    The product area shows whichever pathway the score counts.
    """
    out = []
    for a in AREAS:
        counted = [c for c in score.categories if c.category in a["categories"] and c.counted]
        c = counted[0] if counted else score.category(a["categories"][0])
        definition = RUBRIC_V3.category(c.category)
        out.append({
            "code": a["code"], "label": a["label"], "category": c.category, "full_label": definition.label,
            "share": c.share, "percent": int(c.share * 100 + 0.5), "weight": c.weight,
            "contribution": c.contribution,
        })
    return out


def radar(shares: list[dict], size: int = 320, radius: int = 110, pad: int = 64) -> dict:
    """The points of an eleven-axis radar chart, as SVG coordinates. The first axis points up.

    The view box is `pad` wider on each side than the chart, so the labels beside it fit.
    """
    centre = size / 2
    n = len(shares)

    def at(i: int, r: float) -> tuple[float, float]:
        angle = -math.pi / 2 + 2 * math.pi * i / n
        return round(centre + r * math.cos(angle), 1), round(centre + r * math.sin(angle), 1)

    def ring(fraction: float) -> str:
        return " ".join(f"{x},{y}" for x, y in (at(i, radius * fraction) for i in range(n)))

    axes, labels = [], []
    for i, s in enumerate(shares):
        x, y = at(i, radius)
        axes.append({"x": x, "y": y})
        lx, ly = at(i, radius + 18)
        anchor = "middle" if abs(lx - centre) < 6 else ("start" if lx > centre else "end")
        labels.append({"x": lx, "y": round(ly + 4, 1), "anchor": anchor, "text": s["label"]})
    shape = " ".join(f"{x},{y}" for x, y in (at(i, radius * max(s["share"], 0.0)) for i, s in enumerate(shares)))
    return {
        "size": size, "centre": centre, "rings": [ring(f) for f in (0.25, 0.5, 0.75, 1.0)], "axes": axes,
        "labels": labels, "shape": shape, "view": f"{-pad} 0 {size + 2 * pad} {size}",
    }


def month_text(iso) -> str:
    """A month as October 2026."""
    d = parse_instant(str(iso)) if iso else None
    return f"{MONTHS[d.month - 1]} {d.year}" if d else ""


def monthly_record(rows: list[dict]) -> list[dict]:
    """The monthly record, newest first, with each month's change from the month before it on record."""
    ordered = sorted(rows, key=lambda r: r["month"])
    out = []
    previous = None
    for r in ordered:
        change = None if previous is None else r["total"] - previous
        out.append({"month": month_text(r["month"]), "total": r["total"], "league": league_name(r["league"]), "change": change})
        previous = r["total"]
    return list(reversed(out))
