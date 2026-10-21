"""The health check and the waitlist endpoint, ported from apps/web/app/api/*/route.test.ts."""

from __future__ import annotations

import json

import httpx

from app.main import app
from app.routes import system

BODY = {
    "fullName": "Kwame Mensah",
    "contact": "kwame@example.com",
    "country": "GH",
    "role": "mentor",
    "confirmedAdult": True,
    "acceptedPrivacy": True,
}
_n = 0


def post(client, payload, headers=None):
    global _n
    _n += 1
    h = {"content-type": "application/json", "x-forwarded-for": f"10.0.0.{_n}", **(headers or {})}
    data = payload if isinstance(payload, str) else json.dumps(payload)
    return client.post("/api/v1/waitlist", content=data, headers=h)


# ---------------------------------------------------------------- GET /api/health
def test_health_answers_503_when_supabase_is_not_configured(client):
    app.state.supabase = None
    r = client.get("/api/health")
    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "supabase": "not_configured"}


def test_health_answers_200_when_the_database_answers_and_asks_it_through_health(client, fake):
    fake.on("POST", "/rest/v1/rpc/health", httpx.Response(200, json=True))
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"
    assert str(fake.requests[0].url) == "https://example.supabase.co/rest/v1/rpc/health"


def test_health_answers_503_when_supabase_cannot_be_reached(client, fake):
    def down(_r):
        raise httpx.ConnectError("fetch failed")
    fake.on("POST", "/rest/v1/rpc/health", down)
    r = client.get("/api/health")
    assert r.status_code == 503
    assert r.json() == {"status": "degraded", "supabase": "unreachable"}


# ---------------------------------------------------------------- POST /api/v1/waitlist
def setup_function():
    system.waitlist_limit._hits.clear()


def test_waitlist_returns_503_when_supabase_is_not_configured(client):
    app.state.supabase = None
    assert post(client, BODY).status_code == 503


def test_waitlist_writes_the_row_and_returns_201(client, fake):
    fake.on("POST", "/rest/v1/waitlist", httpx.Response(201))
    r = post(client, BODY)
    assert r.status_code == 201
    sent = fake.sent("POST", "/rest/v1/waitlist")[0]
    assert str(sent.url) == "https://example.supabase.co/rest/v1/waitlist"
    assert sent.headers["apikey"] == "service-test" and sent.headers["authorization"] == "Bearer service-test"
    row = json.loads(sent.content)
    assert {k: row[k] for k in ("contact", "contact_type", "country", "role")} == {
        "contact": "kwame@example.com", "contact_type": "email", "country": "GH", "role": "mentor",
    }


def test_waitlist_gives_the_same_reply_for_a_contact_that_already_joined(client, fake):
    fake.on("POST", "/rest/v1/waitlist", httpx.Response(409, json={"code": "23505", "message": "duplicate"}))
    assert post(client, BODY).status_code == 201


def test_waitlist_returns_422_with_field_errors_for_a_bad_form(client):
    r = post(client, {**BODY, "confirmedAdult": False})
    assert r.status_code == 422
    assert r.json()["errors"]["confirmedAdult"]


def test_waitlist_pretends_to_accept_a_bot_and_writes_nothing(client, fake):
    assert post(client, {**BODY, "website": "spam.example"}).status_code == 201
    assert fake.requests == []


def test_waitlist_rejects_non_json_and_oversized_bodies(client):
    assert post(client, "x", {"content-type": "text/plain"}).status_code == 415
    assert post(client, "x" * 5000).status_code == 413
    assert post(client, "{not json").status_code == 400


def test_waitlist_limits_repeated_attempts_from_one_address(client):
    codes = [post(client, {}, {"x-forwarded-for": "203.0.113.9"}).status_code for _ in range(6)]
    assert all(c == 422 for c in codes[:5])
    assert codes[5] == 429


def test_waitlist_limit_cannot_be_bypassed_by_writing_a_new_address_at_the_start(client):
    codes = [post(client, {}, {"x-forwarded-for": f"198.51.100.{i}, 203.0.113.77"}).status_code for i in range(6)]
    assert codes[5] == 429


# ---------------------------------------------------------------- the files search engines read
def test_robots_and_the_site_map_list_what_they_did(client):
    robots = client.get("/robots.txt").text
    assert "Disallow: /admin\nDisallow: /suspended\n\nSitemap: http://localhost:3000/sitemap.xml" in robots
    sitemap = client.get("/sitemap.xml").text
    assert sitemap.count("<loc>") == 8 and "<loc>http://localhost:3000</loc>" in sitemap


def test_the_retired_interest_address_goes_to_for_investors(client):
    r = client.get("/investor-interest")
    assert r.status_code == 308 and r.headers["location"] == "/for-investors"
