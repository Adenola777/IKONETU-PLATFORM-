"""The waitlist rules, the caller's address, retries, request keys, logs and Sentry scrubbing.

Ported from apps/web/lib/waitlist.test.ts and resilience.test.ts. The two
resilience tests of fetch time limits are replaced by tests of the httpx time
limits each call carries.
"""

from __future__ import annotations

import asyncio
import json

import httpx
import pytest

from app import log
from app.guards import client_address, is_repeat, request_key, with_retry
from app.supabase import QUICK_SECONDS, UPLOAD_SECONDS, ApiError, Supabase
from app.waitlist import normalise_contact, parse_waitlist

VALID = {
    "fullName": "Amara Okafor",
    "contact": "0803 123 4567",
    "country": "NG",
    "role": "founder",
    "confirmedAdult": True,
    "acceptedPrivacy": True,
    "website": "",
}


# ---------------------------------------------------------------- normalise_contact
def test_adds_the_country_code_to_a_local_nigerian_number():
    c = normalise_contact("0803 123 4567", "NG")
    assert (c.value, c.type) == ("+2348031234567", "phone")


def test_adds_the_kenyan_code_to_a_local_kenyan_number():
    assert normalise_contact("0712-345-678", "KE").value == "+254712345678"


def test_keeps_an_international_number_as_typed():
    assert normalise_contact("+233 24 123 4567", "NG").value == "+233241234567"


def test_treats_a_00_prefix_as_international():
    assert normalise_contact("00233241234567", "NG").value == "+233241234567"


def test_lower_cases_an_email():
    c = normalise_contact(" Amara@Example.COM ", "GH")
    assert (c.value, c.type) == ("amara@example.com", "email")


def test_rejects_text_that_is_neither():
    assert normalise_contact("call me maybe", "NG") is None
    assert normalise_contact("12345", "NG") is None
    assert normalise_contact("amara@", "NG") is None


# ---------------------------------------------------------------- parse_waitlist
def test_builds_a_database_row_from_a_valid_form():
    r = parse_waitlist(VALID)
    assert r["ok"] is True
    assert r["row"] == {
        "full_name": "Amara Okafor", "contact": "+2348031234567", "contact_type": "phone", "country": "NG",
        "role": "founder", "confirmed_adult": True, "privacy_version": "2026-10-15", "source": "landing",
    }


def test_flags_a_filled_honeypot_as_a_bot():
    assert parse_waitlist({**VALID, "website": "http://spam"}) == {"ok": False, "bot": True}


def test_requires_the_age_and_privacy_boxes():
    r = parse_waitlist({**VALID, "confirmedAdult": False, "acceptedPrivacy": False})
    assert r["errors"] == {
        "acceptedPrivacy": "Please confirm you have read the privacy policy.",
        "confirmedAdult": "You must be 18 or older to join.",
    }


def test_rejects_countries_outside_season_1():
    assert parse_waitlist({**VALID, "country": "ZA"})["errors"]["country"]


def test_rejects_unknown_fields_so_callers_cannot_set_staff_only_columns():
    assert parse_waitlist({**VALID, "source": "admin"})["ok"] is False


def test_reports_a_bad_contact():
    assert parse_waitlist({**VALID, "contact": "not a contact"})["errors"]["contact"] == "Enter a valid phone number or email."


# ---------------------------------------------------------------- the caller's address
def test_reads_the_entry_the_nearest_proxy_added_not_the_one_the_caller_wrote():
    assert client_address({"x-forwarded-for": "1.1.1.1, 9.9.9.9"}, None, None) == "9.9.9.9"
    assert client_address({"x-forwarded-for": "2.2.2.2, 9.9.9.9"}, None, None) == "9.9.9.9"


def test_counts_back_as_many_entries_as_there_are_trusted_proxies():
    assert client_address({"x-forwarded-for": "6.6.6.6, 7.7.7.7, 10.0.0.1"}, "2", None) == "7.7.7.7"


def test_treats_a_request_that_skipped_the_proxies_as_unknown():
    assert client_address({}, None, None) == "unknown"
    assert client_address({"x-forwarded-for": "7.7.7.7"}, "2", None) == "unknown"


def test_reads_a_single_named_header_when_one_is_configured():
    h = {"x-forwarded-for": "1.1.1.1", "cf-connecting-ip": "5.5.5.5"}
    assert client_address(h, None, "CF-Connecting-IP") == "5.5.5.5"


# ---------------------------------------------------------------- time limits on calls to Supabase
def _timeouts(fake_reply):
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append((request.url.path, request.extensions["timeout"]["read"]))
        return fake_reply

    return seen, handler


def test_gives_uploads_to_storage_longer_than_everything_else():
    seen, handler = _timeouts(httpx.Response(200, json={"signedURL": "/object/sign/p/u/f?token=t"}))
    sb = Supabase("https://x.supabase.co", "k", httpx.AsyncClient(transport=httpx.MockTransport(handler)))

    async def calls():
        await sb.storage_as("t").upload("evidence", "u/f", b"x", "application/pdf")
        await sb.storage_as("t").signed_url("pitches", "u/f", 60)
        await sb.as_user("t").table("evidence").insert({"a": 1})
    asyncio.run(calls())
    assert seen == [
        ("/storage/v1/object/evidence/u/f", UPLOAD_SECONDS),
        ("/storage/v1/object/sign/pitches/u/f", QUICK_SECONDS),
        ("/rest/v1/evidence", QUICK_SECONDS),
    ]


def test_a_call_that_never_answers_becomes_a_network_error():
    def handler(_r):
        raise httpx.ReadTimeout("timed out")
    sb = Supabase("https://x.supabase.co", "k", httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    r = asyncio.run(sb.as_user("t").table("evidence").select("id"))
    assert r.error.code == "network" and r.error.message == "ReadTimeout"


# ---------------------------------------------------------------- retries
def test_waits_250_500_and_so_on_between_attempts_and_stops_at_the_first_success():
    waits, n = [], {"i": 0}

    async def step():
        n["i"] += 1
        return (False, "busy") if n["i"] < 3 else (True, n["i"])

    async def sleep(s):
        waits.append(s)
    r = asyncio.run(with_retry(step, sleep=sleep))
    assert (r.ok, r.value, r.attempts) == (True, 3, 3)
    assert waits == [0.25, 0.5]


def test_reports_the_last_error_after_the_last_attempt_and_counts_a_thrown_error_as_a_failure():
    n = {"i": 0}

    async def step():
        n["i"] += 1
        raise RuntimeError(f"down {n['i']}")

    async def sleep(_s):
        return None
    r = asyncio.run(with_retry(step, attempts=2, sleep=sleep))
    assert (r.ok, r.error, r.attempts) == (False, "down 2", 2)


# ---------------------------------------------------------------- request keys
def test_accepts_a_uuid_and_ignores_anything_else():
    assert request_key("0B6C2F4E-1111-4222-8333-944455556666") == "0b6c2f4e-1111-4222-8333-944455556666"
    assert request_key("abc") is None
    assert request_key(None) is None


def test_recognises_only_the_request_keys_own_unique_index():
    assert is_repeat(ApiError(409, "23505", 'duplicate key value violates unique constraint "venture_updates_request_key"'))
    assert not is_repeat(ApiError(409, "23505", 'duplicate key value violates unique constraint "introductions_once"'))
    assert not is_repeat(None)


# ---------------------------------------------------------------- structured logs
def test_writes_one_line_of_json_with_the_time_level_event_and_fields(capsys):
    log.log_error("evidence.save_failed", {"venture": "v1", "code": "42501"})
    line = json.loads(capsys.readouterr().err.strip())
    assert {k: line[k] for k in ("level", "event", "venture", "code")} == {
        "level": "error", "event": "evidence.save_failed", "venture": "v1", "code": "42501",
    }
    assert line["time"].endswith("Z") and len(line["time"]) == 24


def test_logs_information_on_standard_output(capsys):
    log.log_info("introduction.request_refused", {"code": "23505"})
    assert json.loads(capsys.readouterr().out.strip())["event"] == "introduction.request_refused"


# ---------------------------------------------------------------- what reaches Sentry
def test_keeps_the_method_and_path_and_drops_cookies_headers_form_text_user_and_breadcrumbs():
    e = log.scrub({
        "message": "update.post_failed",
        "request": {"method": "POST", "url": "http://localhost:3100/dashboard/updates?x=1",
                    "cookies": {"ik_access": "secret"}, "headers": {"cookie": "ik_access=secret"},
                    "data": "We signed a supplier"},
        "user": {"id": "u1", "email": "a@b.test"},
        "breadcrumbs": [{"message": "x"}],
    })
    assert e["request"] == {"method": "POST", "url": "http://localhost:3100/dashboard/updates"}
    assert "user" not in e and "breadcrumbs" not in e
    assert not any(w in json.dumps(e) for w in ("secret", "supplier", "a@b.test"))


@pytest.mark.parametrize("dsn", [None, ""])
def test_sentry_stays_off_without_a_dsn(dsn):
    from app.config import load_settings
    assert log.start_sentry(load_settings({"SENTRY_DSN": dsn} if dsn is not None else {})) is False
