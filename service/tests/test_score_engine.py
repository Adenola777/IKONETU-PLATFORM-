"""The score engine's tests for rubric v3, the specification of March 2026 adopted on 20 October 2026."""

from __future__ import annotations

import itertools
from dataclasses import replace
from datetime import datetime, timezone

import pytest

from app.score_engine import (
    CATEGORIES,
    LANE_TIER,
    LANE_WEIGHT,
    LANES,
    REGISTRATION_SIGNAL,
    RUBRIC_V3,
    UNREGISTERED_CAP,
    EvidenceItem,
    calculate_score,
    is_countable,
    league_for,
    next_best_actions,
)
from app.score_engine.rubric_sql import (
    HINT_MIGRATION,
    MIGRATION,
    SEEDED_HINTS,
    _q,
    rubric_to_sql,
)

NOW = datetime(2026, 10, 20, 12, 0, 0, tzinfo=timezone.utc)
_seq = itertools.count(1)


def ev(signal_code: str, **fields) -> EvidenceItem:
    base = EvidenceItem(id=f"e{next(_seq)}", signal_code=signal_code, status="approved", lane="human")
    return replace(base, **fields)


def score(evidence: list[EvidenceItem]):
    return calculate_score(evidence, RUBRIC_V3, NOW)


def codes(category: str) -> list[str]:
    return [s.code for s in RUBRIC_V3.signals if s.category == category]


def every(lane: str, leave: tuple[str, ...] = ()) -> list[EvidenceItem]:
    return [ev(s.code, lane=lane) for s in RUBRIC_V3.signals if s.category not in leave]


class TestRubric:
    def test_holds_the_specifications_eleven_categories_and_the_non_tech_pathway(self):
        assert [c.code for c in CATEGORIES] == [
            "identity", "business", "infrastructure", "team", "financial", "academic", "technical", "operations",
            "traction", "awards", "governance", "media",
        ]
        assert sum(c.weight for c in CATEGORIES if not c.alternative_to) == 100
        assert RUBRIC_V3.category("operations").alternative_to == "technical"

    def test_holds_175_signals_with_distinct_codes(self):
        assert len(RUBRIC_V3.signals) == 175
        assert len({s.code for s in RUBRIC_V3.signals}) == 175

    def test_gives_each_category_its_maximum_except_the_non_tech_pathway_whose_rows_add_to_270(self):
        for c in CATEGORIES:
            total = sum(s.points for s in RUBRIC_V3.signals if s.category == c.code)
            assert total == (270 if c.code == "operations" else c.max_points), c.code

    def test_tells_the_founder_what_to_send_for_every_signal(self):
        assert all(0 < len(s.hint) <= 200 for s in RUBRIC_V3.signals)

    def test_keeps_the_registration_signal(self):
        assert RUBRIC_V3.signal(REGISTRATION_SIGNAL) is not None

    def test_maps_every_lane_to_one_of_the_four_tiers(self):
        assert set(LANE_TIER) == set(LANES)
        assert LANE_WEIGHT == {"government": 1.0, "source": 0.95, "ai": 0.85, "human": 0.85, "human_confirmed": 0.95, "self": 0.60}

    def test_offers_today_every_signal_except_those_that_need_a_provider(self):
        later = {s.code for s in RUBRIC_V3.signals if not s.offered}
        assert {"face_match", "phone_verified", "bvn", "credit_score", "google_workspace"} <= later
        assert len(later) == 19


class TestLeagues:
    @pytest.mark.parametrize("total,league", [
        (0, "EARLY"), (300, "EARLY"), (301, "RISING"), (600, "RISING"), (601, "INVESTABLE"), (850, "INVESTABLE"),
        (851, "ELITE"), (1000, "ELITE"),
    ])
    def test_places_a_total_in_its_league(self, total, league):
        assert league_for(total) == league


class TestCalculation:
    def test_gives_nothing_for_no_evidence(self):
        r = score([])
        assert (r.total, r.league, r.pathway) == (0, "EARLY", "technical")

    @pytest.mark.parametrize("status", ["submitted", "checking", "needs_review", "needs_more", "rejected", "expired"])
    def test_counts_approved_evidence_only(self, status):
        assert score([ev("revenue", status=status)]).total == 0

    def test_matches_the_specifications_example_of_a_perfect_financial_category(self):
        # Page 16: 300 of 300 in Financial, and nothing else, gives 140.
        assert score([ev(c, lane="government") for c in codes("financial")]).total == 140

    @pytest.mark.parametrize("lane,points", [("government", 30), ("source", 28.5), ("human", 25.5), ("ai", 25.5), ("self", 18)])
    def test_weights_a_signal_by_its_lane(self, lane, points):
        assert next(s for s in score([ev("revenue", lane=lane)]).signals if s.code == "revenue").effective == points

    def test_counts_a_signal_once_at_its_best_lane(self):
        r = score([ev("revenue", lane="human"), ev("revenue", lane="government"), ev("revenue", lane="self")])
        s = next(s for s in r.signals if s.code == "revenue")
        assert (s.effective, s.lane, len(s.evidence_ids)) == (30, "government", 3)

    def test_caps_a_category_at_its_maximum(self):
        r = score([ev(c, lane="government") for c in codes("operations")])
        c = r.category("operations")
        assert (c.uncapped, c.earned, c.share, c.contribution) == (270, 250, 1, 120)

    def test_counts_the_higher_of_technical_output_and_business_operations(self):
        r = score([ev(c, lane="government") for c in codes("technical")[:3]] + [ev(c, lane="government") for c in codes("operations")[:6]])
        assert r.pathway == "operations"
        assert r.category("technical").counted is False and r.category("technical").contribution == 0
        assert r.category("operations").counted is True
        assert r.total == int(r.category("operations").contribution)

    def test_prefers_technical_output_when_the_two_pathways_tie(self):
        assert score([ev("github_account"), ev("whatsapp_business")]).pathway == "technical"

    def test_caps_an_unregistered_venture_at_600(self):
        r = score([e for e in every("government") if e.signal_code != REGISTRATION_SIGNAL])
        assert (r.total, r.unregistered_cap_applied, r.is_registered) == (UNREGISTERED_CAP, True, False)

    def test_gives_1000_for_every_signal_from_a_government_record(self):
        r = score(every("government"))
        assert (r.total, r.league, r.unregistered_cap_applied) == (1000, "ELITE", False)

    def test_reaches_at_most_850_when_every_signal_is_reviewed_from_a_document(self):
        assert score(every("human", leave=("operations",))).total == 850

    def test_passes_850_through_the_non_tech_pathway_whose_rows_exceed_its_maximum(self):
        # 270 points at 0.85 is 229.5 of a maximum of 250, a share of 0.918 where every other category stops at 0.85.
        r = score(every("human", leave=("technical",)))
        assert (r.pathway, r.total, r.league) == ("operations", 858, "ELITE")

    def test_rounds_the_total_down(self):
        # 15 of 200 in Identity at 0.85 is 12.75 points, which adds 5.74 to the 1,000.
        assert score([ev("passport")]).total == 5

    @pytest.mark.parametrize("expires,counts", [("2027-01-01", True), ("2026-10-20T11:00:00Z", False), ("not a date", False), (None, True)])
    def test_counts_unexpired_evidence_only(self, expires, counts):
        assert is_countable(ev("revenue", expires_at=expires), NOW) is counts

    def test_gives_the_tier_mix_of_the_counted_points(self):
        r = score([ev("revenue", lane="government"), ev("team_diversity", lane="self")])
        mix = r.tier_mix()
        assert mix["T1"] == pytest.approx(30 / 36 * 100, abs=0.01) and mix["T4"] == pytest.approx(6 / 36 * 100, abs=0.01)
        assert score([]).tier_mix() == {"T1": 0.0, "T2": 0.0, "T3": 0.0, "T4": 0.0}

    def test_records_each_category_with_its_maximum_weight_share_and_contribution(self):
        record = score([ev(c, lane="government") for c in codes("financial")]).category("financial").as_record()
        assert record == {"category": "financial", "max": 300, "weight": 14, "uncapped": 300, "earned": 300, "share": 100,
                          "contribution": 140, "counted": True}


class TestNextBestActions:
    def test_suggests_the_signals_that_add_most_first(self):
        actions = next_best_actions(score([]), RUBRIC_V3, 5)
        assert len(actions) == 5
        gains = [a.estimated_gain for a in actions]
        assert gains == sorted(gains, reverse=True)
        # Customer count: 30 points at 0.85 in Traction, which has 300 points worth 14% of the 1,000.
        assert actions[0].estimated_gain == pytest.approx(30 * 0.85 / 300 * 140, abs=0.01)

    def test_never_suggests_a_signal_that_needs_a_provider(self):
        offered = {s.code for s in RUBRIC_V3.signals if s.offered}
        assert all(a.code in offered for a in next_best_actions(score([]), RUBRIC_V3, 200))

    def test_leaves_out_what_the_caller_asks_and_what_is_already_earned(self):
        first = next_best_actions(score([]), RUBRIC_V3, 1)[0].code
        assert first not in [a.code for a in next_best_actions(score([]), RUBRIC_V3, 200, leave_out={first})]
        assert first not in [a.code for a in next_best_actions(score([ev(first, lane="government")]), RUBRIC_V3, 200)]

    def test_values_a_self_declared_signal_at_the_self_declared_weight(self):
        a = next(a for a in next_best_actions(score([]), RUBRIC_V3, 200) if a.code == "team_diversity")
        assert a.estimated_gain == pytest.approx(10 * 0.60 / 200 * 90, abs=0.01)

    def test_values_the_pathway_that_does_not_count_by_how_far_it_would_pass_the_other(self):
        r = score([ev(c, lane="government") for c in codes("technical")])
        assert r.pathway == "technical"
        assert all(a.category != "operations" for a in next_best_actions(r, RUBRIC_V3, 200))


def test_the_rubric_v3_migration_matches_the_rubric_with_the_hints_it_seeded():
    assert MIGRATION.read_text() == rubric_to_sql(RUBRIC_V3, SEEDED_HINTS)


def test_the_any_country_migration_sets_each_replaced_hint_to_the_rubrics_own():
    sql = HINT_MIGRATION.read_text()
    for code in SEEDED_HINTS:
        hint = RUBRIC_V3.signal(code).hint
        assert hint != SEEDED_HINTS[code]
        assert f"update public.rubric_signals set hint = {_q(hint)} where rubric_version = 'v3' and code = {_q(code)};" in sql
