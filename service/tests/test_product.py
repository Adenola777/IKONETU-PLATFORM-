"""Names, dates, the readiness check, captions, momentum and next steps.

Ported from apps/web/lib/product.test.ts and next-steps.test.ts. The discovery filters move
with the investor pages.
"""

from datetime import datetime, timezone

from app.captions import caption_chunks, cues_from_transcript
from app.product import (
    AREA_WHY,
    AREAS,
    activity_text,
    area_cells,
    clock_text,
    date_text,
    evidence_added_text,
    is_recent,
    level_of,
    momentum,
    readiness_text,
    summarise_areas,
)
from app.scoring import next_steps
from app.validate import js_len
from app.venture_profile import list_text, profile_areas

NOW = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)


class TestActivityAndDates:
    def test_counts_whole_days(self):
        assert activity_text("2026-10-15T01:00:00Z", NOW) == "Updated today"
        assert activity_text("2026-10-14T23:59:00Z", NOW) == "Updated yesterday"
        assert activity_text("2026-10-06T12:00:00Z", NOW) == "Updated 9 days ago"
        assert activity_text(None, NOW) == "No activity yet"

    def test_calls_30_days_recent_and_31_days_not(self):
        assert is_recent("2026-09-15T12:00:00Z", NOW)
        assert not is_recent("2026-09-14T12:00:00Z", NOW)

    def test_writes_a_pitch_length_and_a_uk_date(self):
        assert clock_text(58.4) == "0:58"
        assert clock_text(90) == "1:30"
        assert clock_text("58.5") == "0:59"
        assert date_text("2026-10-15T00:00:00Z") == "15 October 2026"
        assert date_text("2026-10-15T23:30:00+00:00") == "15 October 2026"


AREAS_SEEN = [
    {"category": "financial", "status": "reviewed", "count": 2},
    {"category": "identity", "status": "third_party", "count": 1},
    {"category": "team", "status": "submitted", "count": 1},
]


class TestEvidenceByArea:
    def test_gives_one_cell_per_area_in_rubric_order(self):
        cells = area_cells(AREAS_SEEN)
        assert [c["code"] for c in cells] == ["identity", "legal", "financial", "product", "market", "team", "media", "operations"]
        assert cells[0]["level"] == "strong"
        assert cells[1]["level"] == "gap"
        assert cells[2]["count"] == 2
        assert cells[5]["level"] == "building"

    def test_says_the_readiness_check_in_words(self):
        assert readiness_text(AREAS_SEEN) == "Strong in 2 of 8 areas, building in 1, with a gap in 5."
        assert readiness_text([]) == "No evidence yet, so all eight areas are gaps."

    def test_calls_an_area_strong_only_with_reviewed_or_third_party_evidence(self):
        assert level_of("third_party") == "strong"
        assert level_of("reviewed") == "strong"
        assert level_of("submitted") == "building"
        assert level_of(None) == "gap"

    def test_summarises_the_rows_investors_see_by_their_best_status(self):
        rows = [
            {"category": "financial", "shown_status": "submitted"},
            {"category": "financial", "shown_status": "reviewed"},
            {"category": "financial", "shown_status": "submitted"},
            {"category": "legal", "shown_status": "not_a_status"},
        ]
        assert summarise_areas(rows) == [{"category": "financial", "status": "reviewed", "count": 3}]

    def test_groups_a_profiles_evidence_by_area_in_rubric_order(self):
        evidence = [
            {"category": "team", "status": "submitted"},
            {"category": "identity", "status": "submitted"},
            {"category": "identity", "status": "third_party"},
        ]
        areas = profile_areas(evidence)
        assert [(a["category"], a["status"], a["count"]) for a in areas] == [("identity", "third_party", 2), ("team", "submitted", 1)]

    def test_writes_a_list_as_a_sentence(self):
        assert list_text([]) == ""
        assert list_text(["Legal"]) == "Legal"
        assert list_text(["Legal", "Product", "Team"]) == "Legal, Product and Team"


class TestCaptions:
    def test_splits_sentences_and_long_sentences_at_word_breaks(self):
        long = ("We help traders in Lagos markets take card payments on a phone they already own without buying a "
                "terminal or opening a new bank account.")
        chunks = caption_chunks(f"Hello. {long}")
        assert chunks[0] == "Hello."
        assert " ".join(chunks[1:]) == long
        assert all(js_len(c) <= 84 for c in chunks)

    def test_shares_the_length_out_and_ends_at_the_end(self):
        cues = cues_from_transcript("One two three. Four five six seven eight nine.", 10)
        assert len(cues) == 2
        assert cues[0]["start"] == 0
        assert cues[0]["end"] == cues[1]["start"]
        assert cues[1]["end"] == 10
        assert cues[0]["end"] < cues[1]["end"] - cues[1]["start"]

    def test_makes_nothing_from_an_empty_transcript_or_a_zero_length(self):
        assert cues_from_transcript("   ", 10) == []
        assert cues_from_transcript("Hello there.", 0) == []


class TestMomentum:
    def test_counts_updates_in_90_days_and_marks_the_weeks_that_had_one(self):
        m = momentum(["2026-10-14T09:00:00Z", "2026-10-13T09:00:00Z", "2026-09-20T09:00:00Z", "2026-06-01T09:00:00Z"], NOW)
        assert m["in90"] == 3
        assert m["consistencyText"] == "3 updates in 90 days"
        assert len(m["weeks"]) == 13
        assert m["weeks"][12] == {"ago": 0, "active": True}
        assert [w["ago"] for w in m["weeks"] if w["active"]] == [3, 0]
        assert m["activeWeeks"] == 2

    def test_says_so_when_there_is_no_update(self):
        assert momentum([], NOW)["consistencyText"] == "No updates in 90 days"
        assert momentum(["2026-10-01T00:00:00Z"], NOW)["consistencyText"] == "1 update in 90 days"

    def test_counts_the_evidence_added_in_90_days_and_its_areas(self):
        def e(category, created_at):
            return {"category": category, "createdAt": created_at}
        assert evidence_added_text([], NOW) == "None in 90 days"
        assert evidence_added_text([e("financial", "2026-10-01T00:00:00Z"), e("financial", "2026-09-01T00:00:00Z"),
                                    e("legal", "2026-06-01T00:00:00Z")], NOW) == "2 pieces in 90 days, in 1 of 8 areas"
        assert evidence_added_text([e("team", "2026-10-14T00:00:00Z")], NOW) == "1 piece in 90 days, in 1 of 8 areas"

    def test_gives_every_area_a_reason_it_matters(self):
        assert all(len(AREA_WHY[a["code"]]) > 20 for a in AREAS)


def row(signal_code: str, status: str, lane: str | None = None) -> dict:
    return {"id": signal_code, "signal_code": signal_code, "status": status, "lane": lane, "expires_at": None,
            "item_count": None, "months": None, "revenue_usd": None, "stage": None}


class TestNextSteps:
    def test_gives_three_steps_to_a_founder_with_no_evidence(self):
        steps = next_steps([])
        assert len(steps) == 3
        assert len({s.code for s in steps}) == 3

    def test_leaves_out_evidence_already_waiting_for_a_reviewer(self):
        first = next_steps([])[0]
        assert first.code not in [s.code for s in next_steps([row(first.code, "submitted")])]

    def test_leaves_out_a_fixed_signal_that_is_already_approved(self):
        steps = next_steps([row("company_registration", "approved", "government")], 30)
        assert "company_registration" not in [s.code for s in steps]
