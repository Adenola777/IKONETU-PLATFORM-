"""The IkonetU Score: calculation, league placement and the next best actions.

Ported on 17 October 2026 from packages/score-engine/src/engine.ts. Both
engines give the same result on the same evidence, which
tests/test_score_engine_parity.py checks by running them side by side.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .rubric import (
    LANE_WEIGHT,
    LEAGUE_THRESHOLDS,
    REGISTRATION_SIGNAL,
    UNREGISTERED_CAP,
    Category,
    EvidenceStatus,
    Lane,
    League,
    ProductStage,
    Rubric,
    SignalDef,
)

EPSILON = 1e-9


def round2(n: float) -> float:
    """Rounds to cents the way JavaScript's Math.round does, half up, not to even."""
    return math.floor(n * 100 + 0.5) / 100


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    signal_code: str
    status: EvidenceStatus
    lane: Lane
    # An ISO date. Evidence past this date no longer counts.
    expires_at: str | None = None
    # per_item: the number of verified items in this submission.
    item_count: int | None = None
    # months: the number of verified months.
    months: int | None = None
    # revenue: verified revenue over the last 12 months, already in US dollars.
    revenue_usd: float | None = None
    # stage: the verified product stage.
    stage: ProductStage | None = None


@dataclass(frozen=True)
class SignalResult:
    code: str
    category: Category
    weighted: float
    capped: float
    max_points: int
    evidence_ids: list[str]


@dataclass(frozen=True)
class CategoryResult:
    category: Category
    earned: float
    cap: int
    uncapped: float

    def as_record(self) -> dict:
        """The shape record_score() stores in scores.categories."""
        return {"category": self.category, "uncapped": self.uncapped, "cap": self.cap, "earned": self.earned}


@dataclass(frozen=True)
class ScoreResult:
    rubric_version: str
    total: int
    league: League
    is_registered: bool
    unregistered_cap_applied: bool
    categories: list[CategoryResult] = field(default_factory=list)
    signals: list[SignalResult] = field(default_factory=list)


@dataclass(frozen=True)
class NextAction:
    code: str
    label: str
    category: Category
    estimated_gain: int


def league_for(total: float) -> League:
    """Maps a total to a league: Early 0 to 300, Rising 301 to 600, Investable 601 to 850, Elite 851 to 1000."""
    if total >= LEAGUE_THRESHOLDS["ELITE"]:
        return "ELITE"
    if total >= LEAGUE_THRESHOLDS["INVESTABLE"]:
        return "INVESTABLE"
    if total >= LEAGUE_THRESHOLDS["RISING"]:
        return "RISING"
    return "EARLY"


def parse_instant(value: str) -> datetime | None:
    """Reads an ISO date or timestamp as JavaScript's Date does for the forms this app stores."""
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        # A date alone is UTC midnight in JavaScript, and so is a timestamp without a zone here.
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def is_countable(item: EvidenceItem, now: datetime) -> bool:
    """True when the evidence counts towards the Score at `now`: approved, verified and unexpired."""
    if item.status != "approved":
        return False
    if LANE_WEIGHT.get(item.lane, 0) <= 0:
        return False
    if item.expires_at:
        expires = parse_instant(item.expires_at)
        if expires is None:
            return False
        if expires <= now:
            return False
    return True


def _weighted_points(definition: SignalDef, item: EvidenceItem) -> float:
    """The points one evidence item earns for its signal before the signal cap, already lane-weighted."""
    w = LANE_WEIGHT[item.lane]
    mode = definition.mode
    if mode == "fixed":
        return definition.points * w
    if mode == "per_item":
        count = 1 if item.item_count is None else item.item_count
        return max(0, math.floor(count)) * definition.points * w
    if mode == "months":
        return max(0, math.floor(item.months or 0)) * definition.points * w
    if mode == "revenue":
        per_point = definition.usd_per_point or 100
        usd = max(0, item.revenue_usd or 0)
        return math.floor(usd / per_point) * definition.points * w
    if mode == "stage":
        points = (definition.stage_points or {}).get(item.stage, 0) if item.stage else 0
        return points * w
    raise ValueError(f"unknown signal mode {mode}")


def _combine(definition: SignalDef, values: list[float]) -> float:
    """per_item evidence adds up. Every other mode counts the single best item."""
    if not values:
        return 0
    if definition.mode == "per_item":
        total = 0.0
        for v in values:
            total += v
        return total
    return max(values)


def calculate_score(evidence: list[EvidenceItem], rubric: Rubric, now: datetime | None = None) -> ScoreResult:
    """Calculates the IkonetU Score from approved evidence only (PRD S-1).

    The rules follow the TRD: lane weight, then the signal cap, then the
    category cap, then the unregistered cap of 600, and then the total is
    rounded down.
    """
    moment = now or datetime.now(timezone.utc)
    countable = [e for e in evidence if is_countable(e, moment)]
    codes = {s.code for s in rubric.signals}

    signals: list[SignalResult] = []
    for definition in rubric.signals:
        items = [e for e in countable if e.signal_code == definition.code]
        weighted = _combine(definition, [_weighted_points(definition, i) for i in items])
        signals.append(SignalResult(
            code=definition.code,
            category=definition.category,
            weighted=round2(weighted),
            capped=round2(min(weighted, definition.max_points)),
            max_points=definition.max_points,
            evidence_ids=[i.id for i in items],
        ))

    categories: list[CategoryResult] = []
    for category, cap in rubric.category_caps.items():
        uncapped = 0.0
        for s in signals:
            if s.category == category:
                uncapped += s.capped
        categories.append(CategoryResult(category=category, uncapped=round2(uncapped), cap=cap, earned=round2(min(uncapped, cap))))

    is_registered = REGISTRATION_SIGNAL in codes and any(e.signal_code == REGISTRATION_SIGNAL for e in countable)

    earned = 0.0
    for c in categories:
        earned += c.earned
    total = math.floor(earned + EPSILON)
    unregistered_cap_applied = False
    if not is_registered and total > UNREGISTERED_CAP:
        total = UNREGISTERED_CAP
        unregistered_cap_applied = True

    return ScoreResult(
        rubric_version=rubric.version,
        total=total,
        league=league_for(total),
        is_registered=is_registered,
        unregistered_cap_applied=unregistered_cap_applied,
        categories=categories,
        signals=signals,
    )


def convert_to_usd(amount: float, usd_per_unit: float) -> float:
    """Converts revenue in a local currency to US dollars with one stated rate (TRD rule 4).

    `usd_per_unit` is the value of one unit of the local currency in US dollars
    on the evidence date. The caller stores the rate with the result.
    """
    if not math.isfinite(amount) or not math.isfinite(usd_per_unit) or usd_per_unit <= 0:
        raise ValueError("convert_to_usd needs a finite amount and a positive rate")
    return round2(amount * usd_per_unit)


def next_best_actions(result: ScoreResult, rubric: Rubric, limit: int = 5) -> list[NextAction]:
    """Suggests the evidence that would add the most points next (PRD P-3, O-4).

    It uses each signal's expected lane and the room left under the signal and
    category caps.
    """
    room_by_category = {c.category: c.cap - c.earned for c in result.categories}
    by_signal = {s.code: s for s in result.signals}

    actions: list[NextAction] = []
    for definition in rubric.signals:
        current = by_signal[definition.code].capped if definition.code in by_signal else 0
        w = LANE_WEIGHT[definition.expected_lane]
        mode = definition.mode
        if mode == "fixed":
            step = definition.points * w - current
        elif mode == "per_item":
            step = definition.points * w
        elif mode == "months":
            step = definition.points * 3 * w
        elif mode == "revenue":
            step = 10 * definition.points * w
        else:
            values = sorted((definition.stage_points or {}).values())
            following = next((v for v in values if v * w > current + EPSILON), None)
            step = 0 if following is None else following * w - current
        room = min(definition.max_points - current, room_by_category.get(definition.category, 0))
        gain = math.floor(min(step, room) + EPSILON)
        if gain > 0:
            actions.append(NextAction(definition.code, definition.label, definition.category, gain))

    actions.sort(key=lambda a: (-a.estimated_gain, a.code))
    return actions[:limit]
