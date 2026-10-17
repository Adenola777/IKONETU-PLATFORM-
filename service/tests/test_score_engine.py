"""The score engine's tests, ported case for case from packages/score-engine/src/engine.test.ts
and rubric-sql.test.ts. The TypeScript file has 47 cases and so does this one."""

from __future__ import annotations

import itertools
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.score_engine import (
    CATEGORY_CAPS,
    RUBRIC_V2,
    UNREGISTERED_CAP,
    EvidenceItem,
    calculate_score,
    convert_to_usd,
    is_countable,
    league_for,
    next_best_actions,
)
from app.score_engine.rubric_sql import MIGRATION, rubric_to_sql

NOW = datetime(2026, 10, 5, 12, 0, 0, tzinfo=timezone.utc)
_seq = itertools.count(1)


def ev(signal_code: str, **fields) -> EvidenceItem:
    base = EvidenceItem(id=f"e{next(_seq)}", signal_code=signal_code, status="approved", lane="ai")
    return replace(base, **fields)


def score(evidence: list[EvidenceItem]):
    return calculate_score(evidence, RUBRIC_V2, NOW)


def signal(result, code: str):
    return next(s for s in result.signals if s.code == code)


def category(result, name: str):
    return next(c for c in result.categories if c.category == name)


# ---------------------------------------------------------------- rubric v2
def test_category_caps_add_up_to_1000():
    assert sum(CATEGORY_CAPS.values()) == 1000


def test_every_category_can_be_filled_by_its_signals():
    for cat, cap in CATEGORY_CAPS.items():
        top = sum(s.max_points for s in RUBRIC_V2.signals if s.category == cat)
        assert top >= cap, cat


def test_signal_codes_are_unique():
    codes = [s.code for s in RUBRIC_V2.signals]
    assert len(set(codes)) == len(codes)


# ---------------------------------------------------------------- league boundaries
@pytest.mark.parametrize("total,league", [
    (0, "EARLY"), (300, "EARLY"), (301, "RISING"), (600, "RISING"),
    (601, "INVESTABLE"), (850, "INVESTABLE"), (851, "ELITE"), (1000, "ELITE"),
])
def test_league_for_boundaries(total, league):
    assert league_for(total) == league


# ---------------------------------------------------------------- what counts
def test_an_empty_profile_scores_0_in_early():
    r = score([])
    assert r.total == 0
    assert r.league == "EARLY"


def test_self_declared_claims_earn_nothing():
    assert score([ev("tax_registration", lane="self")]).total == 0


@pytest.mark.parametrize("status", ["submitted", "checking", "needs_review", "needs_more", "rejected", "expired"])
def test_evidence_that_is_not_approved_earns_nothing(status):
    assert score([ev("tax_registration", status=status)]).total == 0


def test_expired_evidence_stops_counting_on_its_expiry_date():
    assert is_countable(ev("government_id", expires_at="2026-10-05T12:00:00Z"), NOW) is False
    assert is_countable(ev("government_id", expires_at="2026-10-06T00:00:00Z"), NOW) is True


def test_an_unparseable_expiry_date_does_not_count():
    assert is_countable(ev("government_id", expires_at="not a date"), NOW) is False


def test_unknown_signal_codes_are_ignored():
    assert score([ev("google_maps_listing", lane="source")]).total == 0


# ---------------------------------------------------------------- lane weights
@pytest.mark.parametrize("lane,points", [
    ("government", 50), ("source", 47), ("human_confirmed", 47), ("ai", 42), ("human", 42),
])
def test_tax_registration_through_each_lane(lane, points):
    assert score([ev("tax_registration", lane=lane)]).total == points


# ---------------------------------------------------------------- signal modes and caps
def test_fixed_signals_count_the_best_single_item_only():
    r = score([ev("government_id", lane="ai"), ev("government_id", lane="source")])
    assert signal(r, "government_id").capped == 28.5


def test_per_item_signals_add_up_across_submissions_and_stop_at_the_cap():
    r = score([ev("customer_evidence", item_count=3), ev("customer_evidence", item_count=2)])
    assert signal(r, "customer_evidence").capped == 42.5
    capped = score([ev("customer_evidence", item_count=20)])
    assert signal(capped, "customer_evidence").weighted == 170
    assert signal(capped, "customer_evidence").capped == 70


def test_per_item_evidence_without_a_count_counts_as_one_item():
    assert signal(score([ev("press_coverage")]), "press_coverage").capped == 8.5


def test_revenue_earns_1_point_per_usd_100_up_to_80():
    assert signal(score([ev("revenue", lane="human", revenue_usd=4_250)]), "revenue").capped == 35.7
    assert signal(score([ev("revenue", lane="human", revenue_usd=50_000)]), "revenue").capped == 80


def test_revenue_counts_the_best_item_not_the_sum():
    r = score([ev("revenue", lane="human", revenue_usd=2_000), ev("revenue", lane="human", revenue_usd=3_000)])
    assert signal(r, "revenue").capped == 25.5


def test_months_signals_use_the_best_item():
    r = score([ev("financial_records", months=6), ev("financial_records", months=9)])
    assert signal(r, "financial_records").capped == 30.6


def test_product_stage_uses_the_stage_points_table():
    assert signal(score([ev("product_stage", stage="idea")]), "product_stage").capped == 0
    assert signal(score([ev("product_stage", stage="mvp")]), "product_stage").capped == 42.5
    assert signal(score([ev("product_stage", stage="scaling", lane="government")]), "product_stage").capped == 130


def test_categories_stop_at_their_cap():
    r = score([
        ev("customer_interviews", item_count=20, lane="government"),
        ev("pilot_letters", item_count=10, lane="government"),
        ev("market_research", lane="government"),
    ])
    assert category(r, "market").uncapped == 100
    assert category(r, "market").earned == 100


# ---------------------------------------------------------------- registration and the unregistered cap
def strong_unregistered() -> list[EvidenceItem]:
    return [
        ev("government_id", lane="government"),
        ev("operating_tenure", months=30, lane="government"),
        ev("tax_registration", lane="government"),
        ev("legal_documents", item_count=5, lane="government"),
        ev("revenue", revenue_usd=100_000, lane="government"),
        ev("financial_records", months=12, lane="government"),
        ev("business_account", lane="government"),
        ev("product_stage", stage="scaling", lane="government"),
        ev("customer_evidence", item_count=7, lane="government"),
        ev("team_members", item_count=8, lane="government"),
        ev("team_credentials", item_count=4, lane="government"),
        ev("website_live", lane="government"),
        ev("pitch_deck", lane="government"),
    ]


def test_caps_an_unregistered_venture_at_600_the_top_of_rising():
    r = score(strong_unregistered())
    assert r.is_registered is False
    assert r.unregistered_cap_applied is True
    assert r.total == UNREGISTERED_CAP
    assert r.league == "RISING"


def test_lifts_the_cap_once_registration_is_approved():
    r = score([*strong_unregistered(), ev("company_registration", lane="source")])
    assert r.is_registered is True
    assert r.unregistered_cap_applied is False
    assert r.total > UNREGISTERED_CAP
    assert r.league == "INVESTABLE"


def test_does_not_treat_registration_under_review_as_registered():
    assert score([ev("company_registration", status="needs_review")]).is_registered is False


# ---------------------------------------------------------------- maximum score
def everything(lane: str) -> list[EvidenceItem]:
    return [
        ev(s.code, lane=lane, item_count=100, months=100, revenue_usd=1_000_000, stage="scaling")
        for s in RUBRIC_V2.signals
    ]


def test_reaches_exactly_1000_only_when_everything_is_verified_at_government_level():
    r = score(everything("government"))
    assert r.total == 1000
    assert r.league == "ELITE"


def test_stays_below_1000_when_the_best_evidence_comes_through_source_checks():
    assert score(everything("source")).total < 1000


# ---------------------------------------------------------------- worked example from the screens
def test_adds_up_the_founder_home_examples_quick_wins():
    assert score([ev("company_registration", lane="source")]).total == 47
    assert score([ev("business_account", lane="source")]).total == 47
    assert score([ev("customer_evidence", item_count=2)]).total == 17
    assert score([ev("website_live", lane="source")]).total == 19
    assert score([ev("student_status")]).total == 17


# ---------------------------------------------------------------- convert_to_usd
def test_converts_with_the_stated_rate_and_rounds_to_cents():
    assert convert_to_usd(1_140_000, 0.0077) == 8778


def test_rejects_a_missing_or_non_positive_rate():
    with pytest.raises(ValueError):
        convert_to_usd(100, 0)
    with pytest.raises(ValueError):
        convert_to_usd(float("nan"), 0.01)


# ---------------------------------------------------------------- next best actions
def test_puts_the_largest_quick_wins_first_for_an_empty_profile():
    actions = next_best_actions(score([]), RUBRIC_V2, 3)
    assert [a.code for a in actions] == ["business_account", "company_registration", "product_stage"]
    assert actions[0].estimated_gain == 47


def test_drops_signals_that_are_already_full():
    r = score([ev("company_registration", lane="government")])
    assert not any(a.code == "company_registration" for a in next_best_actions(r, RUBRIC_V2, 50))


def test_respects_the_room_left_in_a_category():
    r = score([
        ev("customer_interviews", item_count=8, lane="government"),
        ev("pilot_letters", item_count=4, lane="government"),
        ev("market_research", lane="government"),
    ])
    assert not any(a.category == "market" for a in next_best_actions(r, RUBRIC_V2, 50))


# ---------------------------------------------------------------- the rubric seed migration
def test_the_rubric_seed_migration_matches_the_rubric_the_engine_uses():
    assert MIGRATION.read_text() == rubric_to_sql(RUBRIC_V2)
