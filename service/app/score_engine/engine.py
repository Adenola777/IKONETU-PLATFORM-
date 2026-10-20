"""The IkonetU Score: calculation, league placement and the next best actions.

Rubric v3 uses the specification's weighted normalisation (page 16):

    IkonetU Score = ( sum of (category effective / category maximum) x category weight ) x 1,000

where a category's effective points are the sum of each signal's points times the weight of the
lane it was verified in. A category counts at most its maximum, so no category can give more than
its weight. Technical Output and Business Operations fill the same slot, and the higher of the two
counts (page 36).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .rubric import (
    LANE_TIER,
    LANE_WEIGHT,
    LEAGUE_THRESHOLDS,
    REGISTRATION_SIGNAL,
    UNREGISTERED_CAP,
    Category,
    CategoryDef,
    EvidenceStatus,
    Lane,
    League,
    Rubric,
)

EPSILON = 1e-9


def round2(n: float) -> float:
    """Rounds to two places, half up, not to even."""
    return math.floor(n * 100 + 0.5) / 100


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    signal_code: str
    status: EvidenceStatus
    lane: Lane
    # An ISO date. Evidence past this date no longer counts.
    expires_at: str | None = None


@dataclass(frozen=True)
class SignalResult:
    code: str
    category: Category
    points: int
    # The points times the weight of the best lane among the signal's countable evidence.
    effective: float
    lane: Lane | None
    evidence_ids: list[str]


@dataclass(frozen=True)
class CategoryResult:
    category: Category
    label: str
    max_points: int
    weight: int
    # The signals' effective points added up, before the maximum.
    uncapped: float
    earned: float
    # earned as a share of the maximum, from 0 to 1.
    share: float
    # What the category adds to the 1,000.
    contribution: float
    # False for the pathway that lost to its alternative, which adds nothing.
    counted: bool

    def as_record(self) -> dict:
        """The shape record_score() stores in scores.categories and score_snapshots.categories."""
        return {
            "category": self.category, "max": self.max_points, "weight": self.weight, "uncapped": self.uncapped,
            "earned": self.earned, "share": round2(self.share * 100), "contribution": self.contribution,
            "counted": self.counted,
        }


@dataclass(frozen=True)
class ScoreResult:
    rubric_version: str
    total: int
    league: League
    is_registered: bool
    unregistered_cap_applied: bool
    # The pathway that counted for the shared slot: "technical" or "operations".
    pathway: Category
    categories: list[CategoryResult] = field(default_factory=list)
    signals: list[SignalResult] = field(default_factory=list)

    def category(self, code: str) -> CategoryResult | None:
        return next((c for c in self.categories if c.category == code), None)

    def tier_mix(self) -> dict[str, float]:
        """The share of the counted effective points from each tier, in per cent (page 29)."""
        counted = {c.category for c in self.categories if c.counted}
        by_tier = {"T1": 0.0, "T2": 0.0, "T3": 0.0, "T4": 0.0}
        for s in self.signals:
            if s.lane and s.category in counted:
                by_tier[LANE_TIER[s.lane]] += s.effective
        total = sum(by_tier.values())
        return {t: round2(v / total * 100) if total else 0.0 for t, v in by_tier.items()}


@dataclass(frozen=True)
class NextAction:
    code: str
    label: str
    category: Category
    # The points the signal would add to the 1,000 at the lane a founder can get today.
    estimated_gain: float


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
    """Reads an ISO date or timestamp, as the database and the forms write them."""
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
        # A date alone is read as UTC midnight, and so is a timestamp without a zone.
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


def _contribution(definition: CategoryDef, earned: float) -> float:
    return round2(earned / definition.max_points * definition.weight * 10)


def calculate_score(evidence: list[EvidenceItem], rubric: Rubric, now: datetime | None = None) -> ScoreResult:
    """Calculates the IkonetU Score from approved evidence only (PRD S-1).

    Each signal earns its points once, at the weight of the best lane among its countable
    evidence. Then each category is capped at its maximum and weighted, the higher pathway
    fills the shared slot, the total is rounded down, and the cap of 600 applies to a venture
    without approved company registration (PRD S-6).
    """
    moment = now or datetime.now(timezone.utc)
    countable = [e for e in evidence if is_countable(e, moment)]

    signals: list[SignalResult] = []
    for definition in rubric.signals:
        items = [e for e in countable if e.signal_code == definition.code]
        best = max(items, key=lambda i: LANE_WEIGHT[i.lane], default=None)
        signals.append(SignalResult(
            code=definition.code, category=definition.category, points=definition.points,
            effective=round2(definition.points * LANE_WEIGHT[best.lane]) if best else 0.0,
            lane=best.lane if best else None, evidence_ids=[i.id for i in items],
        ))

    raw: dict[str, tuple[float, float]] = {}
    for c in rubric.categories:
        uncapped = round2(sum(s.effective for s in signals if s.category == c.code))
        raw[c.code] = (uncapped, round2(min(uncapped, c.max_points)))

    def slot(c: CategoryDef) -> str:
        return c.alternative_to or c.code

    # In each slot the category that adds most counts. On a tie the first in rubric order counts.
    winners: dict[str, str] = {}
    for c in rubric.categories:
        held = winners.get(slot(c))
        if held is None or _contribution(c, raw[c.code][1]) > _contribution(rubric.category(held), raw[held][1]) + EPSILON:
            winners[slot(c)] = c.code

    categories: list[CategoryResult] = []
    for c in rubric.categories:
        uncapped, earned = raw[c.code]
        counted = winners[slot(c)] == c.code
        categories.append(CategoryResult(
            category=c.code, label=c.label, max_points=c.max_points, weight=c.weight, uncapped=uncapped, earned=earned,
            share=earned / c.max_points, contribution=_contribution(c, earned) if counted else 0.0, counted=counted,
        ))

    is_registered = any(e.signal_code == REGISTRATION_SIGNAL for e in countable) and rubric.signal(REGISTRATION_SIGNAL) is not None
    total = math.floor(sum(c.contribution for c in categories) + EPSILON)
    unregistered_cap_applied = False
    if not is_registered and total > UNREGISTERED_CAP:
        total = UNREGISTERED_CAP
        unregistered_cap_applied = True

    technical = next((c for c in rubric.categories if c.alternative_to), None)
    pathway = winners[technical.alternative_to] if technical else "technical"
    return ScoreResult(
        rubric_version=rubric.version, total=total, league=league_for(total), is_registered=is_registered,
        unregistered_cap_applied=unregistered_cap_applied, pathway=pathway, categories=categories, signals=signals,
    )


def next_best_actions(result: ScoreResult, rubric: Rubric, limit: int = 5, leave_out: set[str] | None = None) -> list[NextAction]:
    """Suggests the evidence that would add the most to the Score next (PRD P-3, O-4).

    Each signal a founder can add today is valued at the lane they can get for it, within the
    room its category has left. A signal in the pathway that does not count is valued by how far
    it would lift that pathway above the one that does. The cap of 600 is not considered.
    """
    leave_out = leave_out or set()
    by_signal = {s.code: s for s in result.signals}
    by_category = {c.category: c for c in result.categories}

    def slot_of(code: str) -> str:
        definition = rubric.category(code)
        return definition.alternative_to or definition.code

    def slot_value(slot: str, changed: str | None = None, earned: float = 0.0) -> float:
        best = 0.0
        for c in rubric.categories:
            if (c.alternative_to or c.code) != slot:
                continue
            e = earned if c.code == changed else by_category[c.code].earned
            best = max(best, _contribution(c, min(e, c.max_points)))
        return best

    actions: list[NextAction] = []
    for definition in rubric.signals:
        if not definition.offered or definition.code in leave_out:
            continue
        current = by_signal[definition.code].effective
        step = definition.points * LANE_WEIGHT[definition.expected_lane] - current
        if step <= EPSILON:
            continue
        category = by_category[definition.category]
        slot = slot_of(definition.category)
        gain = slot_value(slot, definition.category, category.uncapped + step) - slot_value(slot)
        if gain > EPSILON:
            actions.append(NextAction(definition.code, definition.label, definition.category, round2(gain)))

    actions.sort(key=lambda a: (-a.estimated_gain, a.code))
    return actions[:limit]
