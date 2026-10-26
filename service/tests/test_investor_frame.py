"""The investor's pages in the app frame (screens 10 to 13), through HTTP."""

from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from app.session import ACCESS_COOKIE

from .conftest import jwt
from .test_founder_score_pages import VENTURE

NOW = datetime.now(timezone.utc).isoformat()
INTRO = "6f1c1a3e-1111-4222-8333-944455556666"
DETAILS = {
    "investor_type": "angel", "firm": None, "website": None, "based_in": "NG", "sectors": ["Fintech"], "stages": [],
    "countries": [], "cheque_size": "Under $25,000", "thesis": "Payments for traders.", "created_at": "2026-10-20T10:00:00Z",
}
CARD = {
    "venture_id": VENTURE["id"], "name": "Kola Pay", "sector": "Fintech", "stage": "revenue", "country": "NG",
    "description": "Market traders take card payments by phone.", "ask": "A pre-seed round", "founder_name": "Kemi Bello",
    "city": "Lagos", "pitch_seconds": 58, "last_activity": NOW, "updates_90d": 3, "areas": [], "total_count": 1,
}


def sign_in(client, fake, status: str = "active", profile: bool = True):
    client.cookies.set(ACCESS_COOKIE, jwt())
    fake.on("GET", "/auth/v1/user", httpx.Response(200, json={"id": "u-1", "user_metadata": {"confirmed_adult": True}}))
    fake.on("GET", "/rest/v1/profiles", httpx.Response(
        200, json=[{"role": "investor", "status": status, "full_name": "Ngozi Eze"}] if profile else []))
    fake.on("GET", "/rest/v1/investor_profiles", httpx.Response(200, json=[DETAILS] if profile else []))


def venture(fake, intro: dict | None = None):
    """Stands in for everything a founder profile reads, with the investor's own request if there is one."""
    fake.on("GET", "/rest/v1/ventures", httpx.Response(200, json=[{**VENTURE, "founder_id": "u-9", "ask": "A pre-seed round"}]))
    fake.on("GET", "/rest/v1/public_profiles", httpx.Response(200, json=[{"full_name": "Kemi Bello", "city": "Lagos", "country": "NG", "institution": None, "bio": None}]))
    fake.on("GET", "/rest/v1/pitches", httpx.Response(200, json=[]))
    fake.on("POST", "/rest/v1/rpc/venture_evidence", httpx.Response(200, json=[]))
    fake.on("GET", "/rest/v1/venture_updates", httpx.Response(200, json=[]))
    fake.on("GET", "/rest/v1/introductions", httpx.Response(200, json=[intro] if intro else []))


def test_the_investor_sign_up_uses_the_plain_frame_in_the_investor_colour_and_three_cards(client, fake):
    sign_in(client, fake, profile=False)
    body = client.get("/onboarding/investor").text
    assert 'class="site pg-app frame frame-plain app-i"' in body
    assert 'class="fr-tabs"' not in body and 'class="fr-side"' not in body
    assert body.count('<section class="card2 form"') == 3
    # The choices card ends with the sign-up's own boxes, so the privacy box sits inside the third card.
    choices = body[body.index('aria-labelledby="if-choices"'):]
    assert choices.index('name="acceptedPrivacy"') < choices.index("</section>")
    assert "What founders see" in body and ">Send for approval</button>" in body


def test_the_waiting_page_shows_the_three_steps_with_the_date_the_details_were_sent(client, fake):
    sign_in(client, fake, status="pending")
    body = client.get("/investor/pending").text
    assert 'class="site pg-app frame frame-plain app-i"' in body
    assert "Waiting for approval" in body
    steps = re.findall(r"<strong>([^<]+)</strong><small>([^<]+)</small>", body)
    assert steps == [("Details sent", "20 October 2026"), ("Admin check", "In progress"),
                     ("Browse founders", "Sign in again later to see the decision.")]
    assert 'href="/for-investors"' in body and 'href="/terms#terms-investor"' in body


def test_a_declined_investor_is_told_so_and_shown_no_steps(client, fake):
    sign_in(client, fake, status="suspended")
    body = client.get("/investor/pending").text
    assert "Your investor account is not approved" in body
    assert 'class="steps3"' not in body and "mailto:info@ikonetu.com" in body


def test_a_waiting_investor_cannot_reach_discover(client, fake):
    sign_in(client, fake, status="pending")
    r = client.get("/investor")
    assert r.status_code in (302, 303, 307) and r.headers["location"] == "/investor/pending"


def test_discover_shows_each_founder_as_a_card_with_its_activity_and_readiness(client, fake):
    sign_in(client, fake)
    fake.on("POST", "/rest/v1/rpc/discover_ventures", httpx.Response(200, json=[CARD]))
    fake.on("GET", "/rest/v1/pitches", httpx.Response(200, json=[]))
    body = client.get("/investor").text
    assert re.search(r'href="/investor" aria-current="page"><span class="fr-pill">', body)
    assert '<button type="button" class="btn btn-n btn-sm ftoggle" aria-expanded="false" aria-controls="disc-filters">Filters</button>' in body
    assert "1 founder is on IkonetU. Sorted by company name." in body
    assert body.count('<li class="dc">') == 1
    assert f'<h3 class="dc-name"><a href="/investor/ventures/{VENTURE["id"]}">Kola Pay</a></h3>' in body
    assert "Kemi Bello, Lagos, Nigeria · 3 updates in 90 days" in body
    assert "<span>0:58 pitch</span>" in body and "<b>Ask:</b> A pre-seed round" in body
    assert 'id="pv-label"' in body


def test_discover_says_so_when_the_list_cannot_be_loaded(client, fake):
    sign_in(client, fake)
    fake.on("POST", "/rest/v1/rpc/discover_ventures", httpx.Response(500, json={"message": "down"}))
    body = client.get("/investor").text
    assert "The list could not be loaded. Please reload the page." in body
    assert '<li class="dc">' not in body


def test_a_founder_profile_offers_the_request_with_the_investing_notice(client, fake):
    sign_in(client, fake)
    venture(fake)
    body = client.get(f"/investor/ventures/{VENTURE['id']}").text
    assert '<a href="/investor" class="back2">' in body
    assert 'id="r-note"' in body and ">Request an introduction</button>" in body
    assert re.search(r'<a class="btn btn-i req-jump" href="#intro-h">.*Request an introduction</a>', body)
    assert '<p class="vp-risk"><b>About investing</b>' in body
    # The request card heads the side column, before the momentum.
    assert body.index('id="intro-h"') < body.index('id="mo-h"') and body.index('id="ev-h"') < body.index('id="intro-h"')


def test_a_waiting_request_offers_withdraw_and_the_jump_reads_see_your_introduction(client, fake):
    sign_in(client, fake)
    venture(fake, {"id": INTRO, "status": "pending", "created_at": "2026-10-21T09:00:00Z", "decided_at": None})
    body = client.get(f"/investor/ventures/{VENTURE['id']}").text
    assert "You asked on 21 October 2026. Kemi Bello has not answered yet." in body
    assert ">Withdraw my request</button>" in body and 'id="r-note"' not in body
    assert re.search(r'<a class="btn btn-i req-jump" href="#intro-h">.*See your introduction</a>', body)


def test_an_accepted_request_opens_the_conversation(client, fake):
    sign_in(client, fake)
    venture(fake, {"id": INTRO, "status": "accepted", "created_at": "2026-10-21T09:00:00Z", "decided_at": "2026-10-22T09:00:00Z"})
    body = client.get(f"/investor/ventures/{VENTURE['id']}").text
    assert "Kemi Bello accepted on 22 October 2026." in body
    assert f'href="/introductions/{INTRO}"' in body and "Open the conversation" in body


def test_the_investor_profile_shows_three_cards_and_what_founders_see_beside_them(client, fake):
    sign_in(client, fake)
    body = client.get("/investor/profile").text
    assert re.search(r'href="/investor/profile" aria-current="page"><span class="fr-pill">', body)
    assert body.count('<section class="card2 form"') == 3
    assert '<aside class="fr-aside" aria-label="About your profile">' in body
    assert "Payments for traders." in body and ">Save changes</button>" in body


def test_saving_the_profile_still_asks_the_investor_to_confirm_the_statement(client, fake):
    sign_in(client, fake)
    form = {"fullName": "Ngozi Eze", "investorType": "angel", "basedIn": "NG", "sectors": "Fintech",
            "chequeSize": "Under $25,000", "thesis": "Payments and bookkeeping."}
    body = client.post("/investor/profile", data=form).text
    assert "Please check the form." in body and "Confirm that this describes you." in body
    assert not fake.sent("PATCH", "/rest/v1/investor_profiles")
