"""The founder's score on the dashboard, statements on the evidence page, and the reviewer's notes, through HTTP."""

from __future__ import annotations

import json

import httpx

from app.session import ACCESS_COOKIE

from .conftest import jwt

VENTURE = {
    "id": "11111111-1111-1111-1111-111111111111", "name": "Kola Pay", "sector": "Fintech", "stage": "revenue",
    "country": "NG", "description": None, "website": None, "ask": None, "published_at": None, "hidden_at": None,
    "hidden_reason": None,
}


def evidence_row(code: str, status: str = "approved", lane: str | None = "human") -> dict:
    return {
        "id": f"e-{code}", "signal_code": code, "status": status, "lane": lane, "expires_at": None, "summary": "A sentence.",
        "source_ref": None, "public_note": None, "reason": None, "decided_at": None, "created_at": "2026-10-20T10:00:00Z",
        "evidence_files": [],
    }


def sign_in(client, fake, role: str = "founder", evidence: list[dict] | None = None, snapshots: list[dict] | None = None):
    token = jwt()
    client.cookies.set(ACCESS_COOKIE, token)
    fake.on("GET", "/auth/v1/user", httpx.Response(200, json={"id": "u-1", "user_metadata": {"confirmed_adult": True}}))
    fake.on("GET", "/rest/v1/profiles", httpx.Response(200, json=[{"role": role, "status": "active", "full_name": "Kemi Ade"}]))
    fake.on("GET", "/rest/v1/ventures", httpx.Response(200, json=[VENTURE]))
    fake.on("GET", "/rest/v1/pitches", httpx.Response(200, json=[]))
    fake.on("GET", "/rest/v1/evidence", httpx.Response(200, json=evidence or []))
    fake.on("GET", "/rest/v1/venture_updates", httpx.Response(200, json=[]))
    fake.on("GET", "/rest/v1/introductions", httpx.Response(200, json=[]))
    fake.on("POST", "/rest/v1/rpc/venture_evidence", httpx.Response(200, json=[]))
    fake.on("GET", "/rest/v1/score_snapshots", httpx.Response(200, json=snapshots or []))
    return token


def test_the_dashboard_shows_the_score_its_league_the_eleven_areas_and_the_next_steps(client, fake):
    sign_in(client, fake, evidence=[evidence_row("company_registration", lane="government"), evidence_row("revenue"),
                                    evidence_row("team_diversity", lane="self")])
    r = client.get("/dashboard")
    assert r.status_code == 200
    body = r.text
    # Business: 30 of 250 at 1.0 adds 13.2. Financial: 30 of 300 at 0.85 adds 11.9. Team: 10 of 200 at 0.6 adds 2.7.
    assert '<span class="sc-num">27</span>' in body
    assert "Early league" in body and "274 points to Rising" in body
    assert body.count('<li><span title="') == 11
    assert '<svg class="radar"' in body
    assert body.count('<span class="gain">about +') == 3
    assert "Investors do not see your score." in body


def test_the_monthly_record_lists_each_month_with_its_change(client, fake):
    sign_in(client, fake, snapshots=[{"month": "2026-10-01", "total": 340, "league": "RISING"},
                                     {"month": "2026-09-01", "total": 280, "league": "EARLY"}])
    body = client.get("/dashboard").text
    assert "<td>October 2026</td><td>Rising</td><td class=\"n\">340</td><td class=\"n\">+60</td>" in body
    assert "<td>September 2026</td><td>Early</td><td class=\"n\">280</td><td class=\"n\"></td>" in body


def test_the_evidence_page_says_a_self_declared_signal_needs_no_file(client, fake):
    sign_in(client, fake)
    body = client.get("/dashboard/evidence?signal=team_diversity").text
    assert "What to send: say how many of the team are women and how many are men." in body
    assert 'data-statement-note>' in body
    assert "(your own statement)" in body
    assert 'value="face_match"' not in body


def test_a_statement_is_saved_as_the_founder_and_the_score_is_recorded_by_the_server(client, fake):
    token = sign_in(client, fake, evidence=[evidence_row("team_diversity", lane="self")])
    fake.on("POST", "/rest/v1/rpc/declare_evidence", httpx.Response(200, json="e-new"))
    fake.on("POST", "/rest/v1/rpc/record_score", httpx.Response(204))
    r = client.post("/dashboard/evidence", data={
        "signal": "team_diversity", "summary": "Two of our five staff are women.",
        "requestKey": "22222222-2222-4222-8222-222222222222",
    })
    assert r.status_code == 303
    declared = fake.sent("POST", "/rest/v1/rpc/declare_evidence")[0]
    assert declared.headers["authorization"] == f"Bearer {token}"
    assert json.loads(declared.content) == {
        "p_venture": VENTURE["id"], "p_signal": "team_diversity", "p_summary": "Two of our five staff are women.",
        "p_request_key": "22222222-2222-4222-8222-222222222222",
    }
    recorded = fake.sent("POST", "/rest/v1/rpc/record_score")[0]
    assert recorded.headers["authorization"] == "Bearer service-test"
    sent = json.loads(recorded.content)
    assert (sent["p_total"], sent["p_league"], sent["p_rubric"], sent["p_cause"]) == (2, "EARLY", "v3", "e-new")
    assert sent["p_tiers"] == {"T1": 0.0, "T2": 0.0, "T3": 0.0, "T4": 100.0}


def test_a_signal_that_needs_a_provider_cannot_be_added(client, fake):
    sign_in(client, fake)
    r = client.post("/dashboard/evidence", data={"signal": "face_match", "summary": "A selfie video of me.", "link": "youtu.be/x"})
    assert r.status_code == 200 and "Choose what this evidence shows." in r.text
    assert not fake.sent("POST", "/rest/v1/rpc/submit_evidence")


def test_the_review_page_tells_the_reviewer_a_statement_stands_in_for_an_api(client, fake):
    sign_in(client, fake, role="reviewer")
    fake.on("GET", "/rest/v1/evidence", httpx.Response(200, json=[{
        "id": "33333333-3333-3333-3333-333333333333", "venture_id": VENTURE["id"], "signal_code": "monthly_inflow",
        "status": "submitted", "summary": "Six months of statements.", "source_ref": None,
        "created_at": "2026-10-20T10:00:00Z", "ventures": {"name": "Kola Pay", "founder_id": "u-2"}, "evidence_files": [],
    }]))
    body = client.get("/admin/evidence/33333333-3333-3333-3333-333333333333").text
    assert "The founder was asked for: bank statements for the last six months." in body
    assert "stands in for a connection to the founder" in body
    assert 'name="itemCount"' not in body
