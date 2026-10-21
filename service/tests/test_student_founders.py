"""Student founders in any country, through HTTP: the owner's ruling of 21 October 2026.

A founder can be in any country in ISO 3166-1, and must confirm being enrolled at a higher education
institution or a graduate of one in the last three years. The profile records when they confirmed it.
"""

from __future__ import annotations

import json

import httpx

from app.countries import COUNTRIES
from app.session import ACCESS_COOKIE

from .conftest import jwt

FORM = {
    "fullName": "Ella Hughes", "country": "GB", "city": "Leeds", "institution": "University of Leeds",
    "graduateStatus": "Second-year student", "bio": "", "ventureName": "Shelf Swap", "sector": "Other", "stage": "idea",
    "description": "", "ask": "", "website": "", "linkedin": "", "x": "", "instagram": "", "studentFounder": "on",
    "acceptedPrivacy": "on",
}


def signed_in_without_a_profile(client, fake):
    client.cookies.set(ACCESS_COOKIE, jwt())
    fake.on("GET", "/auth/v1/user", httpx.Response(200, json={"id": "u-1", "user_metadata": {"confirmed_adult": True}}))
    fake.on("GET", "/rest/v1/profiles", httpx.Response(200, json=[]))
    fake.on("GET", "/rest/v1/ventures", httpx.Response(200, json=[]))
    for table in ("profiles", "consents", "ventures"):
        fake.on("POST", f"/rest/v1/{table}", httpx.Response(201))


def test_the_sign_up_form_offers_every_country_and_asks_the_founder_to_confirm_being_a_student(client, fake):
    signed_in_without_a_profile(client, fake)
    body = client.get("/onboarding/founder").text
    assert len(COUNTRIES) == 249
    assert body.count('<option value="') - body.count('<option value="" ') >= 249
    assert '<option value="GB">United Kingdom</option>' in body
    assert 'name="studentFounder"' in body
    assert "I study at a university, college or other higher education institution, or I graduated from one in the last three years." in body


def test_a_student_founder_in_the_united_kingdom_can_join_and_the_profile_records_the_declaration(client, fake):
    signed_in_without_a_profile(client, fake)
    r = client.post("/onboarding/founder", data=FORM)
    assert (r.status_code, r.headers["location"]) == (303, "/dashboard")
    profile = json.loads(fake.sent("POST", "/rest/v1/profiles")[0].content)
    assert profile["country"] == "GB" and profile["institution"] == "University of Leeds"
    assert profile["student_declared_at"].endswith("Z")
    venture = json.loads(fake.sent("POST", "/rest/v1/ventures")[0].content)
    assert venture["country"] == "GB"


def test_a_founder_who_does_not_confirm_being_a_student_is_not_saved(client, fake):
    signed_in_without_a_profile(client, fake)
    r = client.post("/onboarding/founder", data={k: v for k, v in FORM.items() if k != "studentFounder"})
    assert r.status_code == 200 and "IkonetU is for student founders." in r.text
    assert fake.sent("POST", "/rest/v1/profiles") == []
