"""Rubric v2, the lane weights, the league thresholds and the caps.

Ported on 17 October 2026 from packages/score-engine/src/rubric.ts, whose
values it repeats exactly. The rubric is mirrored into the rubric_signals
table by migration 20261005000002, which rubric_sql.py generates, so a change
here needs that migration regenerated and the tests updated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Category = Literal["identity", "legal", "financial", "product", "market", "team", "media", "operations"]
League = Literal["EARLY", "RISING", "INVESTABLE", "ELITE"]
# How a piece of evidence was verified (TRD, Score engine rule 2).
# self is a claim with no approved evidence, and it earns nothing (PRD E-6).
Lane = Literal["government", "source", "ai", "human", "human_confirmed", "self"]
EvidenceStatus = Literal["submitted", "checking", "needs_review", "needs_more", "approved", "rejected", "expired"]
ProductStage = Literal["idea", "mvp", "revenue", "scaling"]
# fixed: one item earns `points`, and the best item counts.
# per_item: each verified item earns `points`, summed up to `max_points`.
# months: `points` per verified month, the best item counts, up to `max_points`.
# revenue: 1 point per `usd_per_point` US dollars, the best item counts, up to `max_points`.
# stage: points looked up from `stage_points`, and the best item counts.
SignalMode = Literal["fixed", "per_item", "months", "revenue", "stage"]

CATEGORIES: tuple[Category, ...] = ("identity", "legal", "financial", "product", "market", "team", "media", "operations")
LANES: tuple[Lane, ...] = ("government", "source", "ai", "human", "human_confirmed", "self")
EVIDENCE_STATUSES: tuple[EvidenceStatus, ...] = (
    "submitted", "checking", "needs_review", "needs_more", "approved", "rejected", "expired",
)
PRODUCT_STAGES: tuple[ProductStage, ...] = ("idea", "mvp", "revenue", "scaling")


@dataclass(frozen=True)
class SignalDef:
    code: str
    category: Category
    label: str
    mode: SignalMode
    points: int
    max_points: int
    # The lane a founder is most likely to get, used to estimate the next best actions.
    expected_lane: Lane
    usd_per_point: int | None = None
    stage_points: dict[str, int] | None = None


@dataclass(frozen=True)
class Rubric:
    version: str
    category_caps: dict[Category, int]
    signals: tuple[SignalDef, ...] = field(default_factory=tuple)

    def signal(self, code: str) -> SignalDef | None:
        return next((s for s in self.signals if s.code == code), None)


# Lane weights from the TRD. Self-declared claims earn nothing.
LANE_WEIGHT: dict[Lane, float] = {
    "government": 1.0,
    "source": 0.95,
    "ai": 0.85,
    "human": 0.85,
    "human_confirmed": 0.95,
    "self": 0,
}

LEAGUE_THRESHOLDS = {"RISING": 301, "INVESTABLE": 601, "ELITE": 851}

# A venture without approved company registration cannot score above this (PRD S-6).
UNREGISTERED_CAP = 600

# The signal whose approval marks a venture as registered.
REGISTRATION_SIGNAL = "company_registration"

CATEGORY_CAPS: dict[Category, int] = {
    "identity": 100,
    "legal": 100,
    "financial": 200,
    "product": 200,
    "market": 100,
    "team": 150,
    "media": 100,
    "operations": 50,
}

# Rubric v2, the proposed defaults from the TRD of 5 October 2026.
RUBRIC_V2 = Rubric(
    version="v2",
    category_caps=CATEGORY_CAPS,
    signals=(
        # Identity (100)
        SignalDef("company_registration", "identity", "Company registration matched to the founder", "fixed", 50, 50, "source"),
        SignalDef("government_id", "identity", "Government ID verified", "fixed", 30, 30, "source"),
        SignalDef("operating_tenure", "identity", "Months operating", "months", 1, 20, "ai"),
        # Legal (100)
        SignalDef("tax_registration", "legal", "Tax registration", "fixed", 50, 50, "ai"),
        SignalDef("legal_documents", "legal", "Legal documents such as IP filings, contracts or licences", "per_item", 10, 50, "ai"),
        # Financial (200)
        SignalDef("revenue", "financial", "Verified revenue, last 12 months", "revenue", 1, 80, "human", usd_per_point=100),
        SignalDef("financial_records", "financial", "Months of verified financial records", "months", 4, 40, "ai"),
        SignalDef("business_account", "financial", "Verified business bank or mobile money account", "fixed", 50, 50, "source"),
        SignalDef("financial_statements", "financial", "Verified financial statements", "per_item", 10, 30, "ai"),
        # Product (200)
        SignalDef(
            "product_stage", "product", "Product stage with evidence", "stage", 0, 130, "ai",
            stage_points={"idea": 0, "mvp": 50, "revenue": 90, "scaling": 130},
        ),
        SignalDef("customer_evidence", "product", "Customer evidence such as signed orders or usage data", "per_item", 10, 70, "ai"),
        # Market (100)
        SignalDef("customer_interviews", "market", "Documented customer interviews", "per_item", 5, 40, "ai"),
        SignalDef("pilot_letters", "market", "Signed pilot or intent letters", "per_item", 10, 40, "ai"),
        SignalDef("market_research", "market", "Market research document", "fixed", 20, 20, "ai"),
        # Team (150)
        SignalDef("team_members", "team", "Verified team members", "per_item", 5, 40, "ai"),
        SignalDef("team_credentials", "team", "Verified team credentials", "per_item", 15, 60, "ai"),
        SignalDef("student_status", "team", "Student or graduate status verified", "fixed", 20, 20, "ai"),
        SignalDef("programme_completed", "team", "Recognised programme completed", "per_item", 15, 30, "ai"),
        # Media (100)
        SignalDef("website_live", "media", "Live website, checked automatically", "fixed", 20, 20, "source"),
        SignalDef("social_profile", "media", "Verified social profile", "fixed", 20, 20, "ai"),
        SignalDef("pitch_deck", "media", "One-pager or pitch deck", "fixed", 20, 20, "ai"),
        SignalDef("press_coverage", "media", "Verified press coverage", "per_item", 10, 40, "ai"),
        # Operations (50)
        SignalDef(
            "operational_evidence", "operations",
            "Operational evidence such as supplier contracts, premises or tools", "per_item", 10, 50, "ai",
        ),
    ),
)
