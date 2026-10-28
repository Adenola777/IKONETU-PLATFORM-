"""The founder's pages in the app frame (screens 04 to 07.1), through HTTP."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from app.session import ACCESS_COOKIE

from .conftest import jwt
from .test_founder_score_pages import VENTURE, evidence_row, sign_in

NOW = datetime.now(timezone.utc).isoformat()


def test_the_founder_sign_up_uses_the_plain_frame_and_three_cards(client, fake):
    client.cookies.set(ACCESS_COOKIE, jwt())
    fake.on("GET", "/auth/v1/user", httpx.Response(200, json={"id": "u-1", "user_metadata": {"confirmed_adult": True}}))
    fake.on("GET", "/rest/v1/profiles", httpx.Response(200, json=[]))
    body = client.get("/onboarding/founder").text
    assert 'class="site pg-app frame frame-plain app-f"' in body
    assert 'class="fr-tabs"' not in body and 'class="fr-side"' not in body
    assert body.count('<section class="card2 form"') == 3
    assert 'name="studentFounder"' in body and 'name="acceptedPrivacy"' in body


def test_home_without_a_pitch_says_the_profile_is_hidden_and_keeps_publish_off(client, fake):
    sign_in(client, fake)
    body = client.get("/dashboard").text
    assert "Welcome, Kemi" in body and "Your profile is hidden" in body
    assert re.search(r'<button type="submit" class="btn btn-f btn-wide" disabled aria-describedby="pub-need">Publish my profile</button>', body)
    assert 'id="pub-need"' in body
    assert re.search(r'href="/dashboard" aria-current="page"><span class="fr-pill">', body)


def test_home_with_a_published_profile_offers_to_hide_it(client, fake):
    sign_in(client, fake)
    fake.on("GET", "/rest/v1/ventures", httpx.Response(200, json=[{**VENTURE, "published_at": "2026-10-20T10:00:00Z"}]))
    fake.on("GET", "/rest/v1/pitches", httpx.Response(200, json=[{"duration_seconds": 58, "updated_at": "2026-10-20T09:00:00Z"}]))
    body = client.get("/dashboard").text
    assert "Your profile is published" in body and "since 20 October 2026" in body
    assert '<button type="submit" class="btn btn-n btn-wide">Hide my profile</button>' in body
    assert 'id="pub-need"' not in body


def test_home_counts_the_eleven_areas_by_level(client, fake):
    sign_in(client, fake)
    counts = re.findall(r"<li><b>(\d+)</b><span>(Strong|Building|Gap)</span></li>", client.get("/dashboard").text)
    assert [c[1] for c in counts] == ["Strong", "Building", "Gap"] and sum(int(c[0]) for c in counts) == 11


def test_the_evidence_page_counts_added_approved_and_waiting(client, fake):
    sign_in(client, fake, evidence=[evidence_row("revenue"), evidence_row("customer_count", status="submitted"),
                                    evidence_row("company_registration", status="needs_more")])
    body = client.get("/dashboard/evidence").text
    stats = re.findall(r"<li><b(?: class=\"ok\")?>(\d+)</b><span>(\w+)</span></li>", body)
    assert stats == [("3", "Added"), ("1", "Approved"), ("1", "Waiting")]
    assert '<a href="#add-h" class="btn btn-f ev-add-jump">' in body and 'id="add-h"' in body
    assert body.count('<li>\n<h3 class="ev-name">') == 3


def test_the_pitch_page_without_a_pitch_offers_the_upload_form(client, fake):
    sign_in(client, fake)
    body = client.get("/dashboard/pitch").text
    assert "You have no pitch yet" in body and "data-pitch-upload" in body
    assert 'id="p-video"' in body and 'id="p-transcript"' in body
    assert "/dashboard/pitch/remove" not in body


def test_founders_no_longer_post_updates_and_the_old_address_leads_to_the_feed(client, fake):
    sign_in(client, fake)
    r = client.get("/dashboard/updates", follow_redirects=False)
    assert r.status_code == 307 and r.headers["location"] == "/activity"
    r = client.post("/dashboard/updates", data={"body": "We signed our tenth trader."}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/activity"
    assert fake.sent("POST", "/rest/v1/venture_updates") == []
