"""The form rules of the founder and staff pages. Ported from apps/web/lib/account.test.ts and forms.test.ts."""

import pytest

from app.forms import (
    parse_decision,
    parse_evidence,
    parse_introduction_note,
    parse_onboarding,
    parse_pitch,
    parse_venture,
)
from app.waitlist import PRIVACY_VERSION

VALID = {
    "fullName": "  Amara Okafor ",
    "country": "NG",
    "city": "Lagos",
    "institution": "University of Lagos",
    "graduateStatus": "Final-year student",
    "bio": "",
    "ventureName": "LearnLoop",
    "sector": "Edtech",
    "stage": "mvp",
    "description": "",
    "website": "learnloop.ng",
    "linkedin": "",
    "x": "",
    "instagram": "https://instagram.com/learnloop",
    "studentFounder": "on",
    "confirmedAdult": "on",
    "acceptedPrivacy": "on",
    "consent_evidence_processing": "on",
}


def without(key: str) -> dict:
    return {k: v for k, v in VALID.items() if k != key}


class TestOnboarding:
    def test_builds_the_profile_consent_and_venture_rows_from_a_valid_form(self):
        result = parse_onboarding(VALID)
        assert result.ok
        assert result.data == {
            "profile": {
                "full_name": "Amara Okafor", "country": "NG", "city": "Lagos", "institution": "University of Lagos",
                "graduate_status": "Final-year student", "bio": None, "confirmed_adult": True,
            },
            "consents": [
                {"consent_type": "profile", "granted": True, "policy_version": PRIVACY_VERSION},
                {"consent_type": "evidence_processing", "granted": True, "policy_version": PRIVACY_VERSION},
                {"consent_type": "notifications", "granted": False, "policy_version": PRIVACY_VERSION},
            ],
            "venture": {
                "name": "LearnLoop", "sector": "Edtech", "stage": "mvp", "country": "NG", "ask": None,
                "description": None, "website": "https://learnloop.ng",
                "social_links": {"instagram": "https://instagram.com/learnloop"},
            },
        }

    def test_does_not_ask_for_the_adult_box_again_when_sign_in_recorded_it(self):
        assert parse_onboarding(without("confirmedAdult"), True).ok

    def test_requires_the_adult_box_when_sign_in_did_not_record_it(self):
        result = parse_onboarding(without("confirmedAdult"))
        assert not result.ok
        assert result.errors["confirmedAdult"] == "You must be 18 or older to join."

    def test_requires_the_privacy_policy_box(self):
        result = parse_onboarding(without("acceptedPrivacy"))
        assert not result.ok
        assert "acceptedPrivacy" in result.errors

    # Founders can be in any country since 21 October 2026, so only a code outside ISO 3166-1 is refused.
    @pytest.mark.parametrize("country", ["GB", "US", "ZA", "IN"])
    def test_takes_a_founder_in_any_country(self, country):
        result = parse_onboarding({**VALID, "country": country})
        assert result.ok
        assert result.data["profile"]["country"] == result.data["venture"]["country"] == country

    @pytest.mark.parametrize("country", ["", "XX", "gb", "Nigeria", "other"])
    def test_refuses_a_country_code_outside_iso_3166(self, country):
        result = parse_onboarding({**VALID, "country": country})
        assert result.errors["country"] == "Choose your country."

    def test_requires_a_student_founder_to_confirm_it(self):
        result = parse_onboarding(without("studentFounder"))
        assert not result.ok
        assert result.errors["studentFounder"].startswith("IkonetU is for student founders.")

    @pytest.mark.parametrize("key", ["institution", "graduateStatus"])
    def test_requires_the_institution_and_the_student_or_graduate_status(self, key):
        assert key in parse_onboarding({**VALID, key: " "}).errors

    def test_refuses_a_stage_the_database_does_not_hold(self):
        result = parse_onboarding({**VALID, "stage": "unicorn"})
        assert result.errors["stage"] == "Choose your stage."

    def test_refuses_a_description_or_bio_longer_than_the_database_allows(self):
        assert not parse_onboarding({**VALID, "description": "x" * 281}).ok
        assert not parse_onboarding({**VALID, "bio": "x" * 601}).ok

    @pytest.mark.parametrize("website", ["javascript:alert(1)", "not a site", "ftp://files.example.com"])
    def test_refuses_an_address_that_is_not_a_website(self, website):
        result = parse_onboarding({**VALID, "website": website})
        assert not result.ok
        assert "website" in result.errors

    def test_never_takes_a_role_or_status_from_the_form(self):
        result = parse_onboarding({**VALID, "role": "admin", "status": "active"})
        assert result.ok
        assert "role" not in result.data["profile"]
        assert "status" not in result.data["profile"]

    def test_names_each_missing_answer_of_an_empty_form(self):
        result = parse_onboarding({"country": "NG", "stage": "idea"})
        assert set(result.errors) == {"fullName", "institution", "graduateStatus", "ventureName", "sector", "studentFounder",
                                      "confirmedAdult", "acceptedPrivacy"}


PDF = {"name": "statements.pdf", "type": "application/pdf", "size": 2_000_000}


class TestEvidence:
    def test_needs_a_file_or_a_link(self):
        r = parse_evidence("revenue", "Twelve months of bank statements", "", [])
        assert r.errors["files"] == "Add a file or a link, so a reviewer can check it."

    def test_accepts_a_link_alone_and_adds_https(self):
        r = parse_evidence("press_coverage", "An article about Kola Pay", "news.example.com/kola", [])
        assert r.ok and r.data["link"] == "https://news.example.com/kola"

    def test_refuses_large_files_other_types_and_unknown_signals(self):
        summary = "Twelve months of statements"
        assert not parse_evidence("revenue", summary, "", [{**PDF, "size": 11 * 1024 * 1024}]).ok
        assert not parse_evidence("revenue", summary, "", [{**PDF, "type": "text/html"}]).ok
        assert not parse_evidence("made_up", summary, "", [PDF]).ok
        assert parse_evidence("revenue", summary, "", [PDF]).ok

    def test_asks_only_what_it_shows_when_the_signal_is_missing(self):
        # The rule across fields waits until every field passes, as zod's refine did.
        r = parse_evidence("", "Twelve months of statements", "", [])
        assert r.errors == {"signal": "Choose what this evidence shows."}

    def test_takes_a_statement_alone_for_a_self_declared_signal(self):
        r = parse_evidence("team_diversity", "Two of our five staff are women.", "news.example.com", [PDF])
        assert r.ok and r.data["statement"] is True
        assert (r.data["link"], r.data["files"]) == (None, [])
        assert parse_evidence("team_diversity", "Two", "", []).errors == {"summary": "Write your statement in at least 10 characters."}

    def test_refuses_a_signal_that_needs_a_provider_ikonetu_does_not_have(self):
        assert parse_evidence("face_match", "A selfie video of me", "", [PDF]).errors == {"signal": "Choose what this evidence shows."}


PITCH = {
    "path": "77777777-7777-7777-7777-777777777777/0b6c2f4e-1111-4222-8333-944455556666.mp4",
    "mimeType": "video/mp4",
    "size": 12_000_000,
    "duration": 58.2,
    "transcript": "Kola Pay lets market traders take card payments on their phones.",
}


class TestPitch:
    def test_accepts_a_one_minute_pitch_with_a_transcript(self):
        assert parse_pitch(PITCH).ok

    def test_refuses_a_long_video_a_large_file_a_short_transcript_and_a_path_outside_the_pattern(self):
        assert not parse_pitch({**PITCH, "duration": 120}).ok
        assert not parse_pitch({**PITCH, "size": 60 * 1024 * 1024}).ok
        assert not parse_pitch({**PITCH, "transcript": "Too short"}).ok
        assert not parse_pitch({**PITCH, "path": "../../etc/passwd"}).ok

    def test_refuses_a_body_that_is_not_an_object(self):
        assert not parse_pitch(None).ok
        assert not parse_pitch(["a"]).ok


class TestNotesVentureAndDecisions:
    def test_asks_for_a_note_of_at_least_20_characters(self):
        assert not parse_introduction_note("Hi").ok
        assert parse_introduction_note("We back payments companies in Lagos.").ok

    def test_keeps_the_sector_to_the_list(self):
        assert not parse_venture("Kola Pay", "Payments", "revenue", "", "").ok
        assert parse_venture("Kola Pay", "Fintech", "revenue", "", "kolapay.ng").ok
        assert not parse_venture("Kola Pay", "Fintech", "revenue", "", "", ask="Yes").ok
        with_ask = parse_venture("Kola Pay", "Fintech", "revenue", "", "", ask=" $150,000 to reach 5,000 paying merchants ")
        assert with_ask.ok and with_ask.data["ask"] == "$150,000 to reach 5,000 paying merchants"

    def test_an_empty_ask_is_no_ask(self):
        assert parse_venture("Kola Pay", "Fintech", "revenue", "", "", ask="  ").data["ask"] is None

    def test_needs_a_lane_and_a_note_to_approve_and_a_reason_to_reject(self):
        assert not parse_decision({"decision": "approve", "lane": "human", "publicNote": ""}).ok
        ok = parse_decision({"decision": "approve", "lane": "human", "publicNote": "Compared with bank statements",
                             "revenueUsd": "18,000"})
        assert ok.ok and ok.data["decision"] == "approve" and ok.data["revenueUsd"] == 18000
        assert not parse_decision({"decision": "approve", "lane": "human", "publicNote": "Compared with statements",
                                   "months": "twelve"}).ok
        assert not parse_decision({"decision": "reject", "reason": ""}).ok
        assert parse_decision({"decision": "needs_more", "reason": "Add the last three months."}).ok
        assert not parse_decision({"decision": "delete"}).ok
