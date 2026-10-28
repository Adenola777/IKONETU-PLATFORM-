"""Sign in, Enter your code and Founder or investor (screens 01 to 03), through HTTP."""

from __future__ import annotations

import re
from dataclasses import replace

import httpx

from app.routes import auth
from app.session import ACCESS_COOKIE
from app.signin import PENDING_COOKIE, Pending, now_ms

from .conftest import jwt


def phone_on(monkeypatch):
    monkeypatch.setattr(auth, "settings", replace(auth.settings, phone_sign_in=True))


def signed_in(client, fake, profile: dict | None = None):
    client.cookies.set(ACCESS_COOKIE, jwt())
    fake.on("GET", "/auth/v1/user", httpx.Response(200, json={"id": "u-1", "user_metadata": {"confirmed_adult": True}}))
    fake.on("GET", "/rest/v1/profiles", httpx.Response(200, json=[profile] if profile else []))


def test_the_sign_in_page_uses_the_app_layout_with_its_button_at_the_foot(client):
    body = client.get("/signin").text
    assert '<div class="site pg-app pg-auth">' in body
    assert '<a class="au-logo" href="/" aria-label="IkonetU home">' in body and 'class="au-back"' not in body
    assert "<h1>Sign in or create your account</h1>" in body
    assert 'class="au-seg"' not in body and 'id="s-email"' in body
    foot = body[body.index('<div class="au-foot">'):]
    assert foot.index(">Send my code</button>") < foot.index('href="/terms"') < foot.index("</form>")


def test_with_phone_sign_in_on_phone_and_email_are_two_links_with_phone_chosen(client, monkeypatch):
    phone_on(monkeypatch)
    body = client.get("/signin").text
    links = re.findall(r'<a href="/signin\?method=(\w+)"( aria-current="true")?>(\w+)</a>', body)
    assert links == [("phone", ' aria-current="true"', "Phone"), ("email", "", "Email")]
    assert 'id="s-phone"' in body and 'name="country"' in body and 'id="s-email"' not in body
    body = client.get("/signin?method=email").text
    assert '<a href="/signin?method=email" aria-current="true">Email</a>' in body and 'id="s-email"' in body


def test_the_code_page_has_a_back_button_and_draws_the_code_as_boxes(client):
    client.cookies.set(PENDING_COOKIE, Pending(kind="email", email="amara@example.com", sent_at=now_ms()).encode(), path="/signin")
    body = client.get("/signin/code").text
    assert '<a class="au-back" href="/signin" aria-label="Back">' in body
    assert '<label for="c-code" class="sr-only">6-digit code</label>' in body
    assert re.search(r'<div class="cb" data-code-boxes>\s*<input id="c-code" name="code"', body)
    assert '<script src="/static/js/code-boxes.js" defer></script>' in body
    # Continue closes the code's form, and the new code and the other address follow it.
    assert body.index(">Continue</button>") < body.index('action="/signin/code/resend"') < body.index(">Use a different email</a>")


def test_a_phone_sign_in_offers_sms_and_a_different_number(client):
    pending = Pending(kind="phone", phone="+2348012345678", channel="whatsapp", sent_at=now_ms())
    client.cookies.set(PENDING_COOKIE, pending.encode(), path="/signin")
    body = client.get("/signin/code").text
    assert "We sent a 6-digit code by WhatsApp to a number ending 5678." in body
    assert ">Send the code by SMS instead</button>" in body and ">Use a different number</a>" in body


def test_the_choice_shows_two_cards_with_founder_chosen_and_asks_onboarding_again(client, fake):
    signed_in(client, fake)
    body = client.get("/onboarding").text
    assert 'class="site pg-app frame frame-plain app-f"' in body
    assert '<form class="fr-page rp-form" method="get" action="/onboarding">' in body
    assert '<input type="radio" name="role" value="founder" checked>' in body
    assert '<input type="radio" name="role" value="investor">' in body
    assert "lucide-rocket" in body and "lucide-briefcase" in body
    assert "Each account is either a founder account or an investor account." in body
    assert '<button type="submit" class="btn btn-f btn-wide rp-go">Continue</button>' in body


def test_the_choice_sends_a_new_account_to_the_sign_up_it_chose(client, fake):
    signed_in(client, fake)
    for chosen in ("founder", "investor"):
        r = client.get(f"/onboarding?role={chosen}")
        assert r.status_code in (302, 303, 307) and r.headers["location"] == f"/onboarding/{chosen}"


def test_any_other_choice_shows_the_cards_again(client, fake):
    signed_in(client, fake)
    r = client.get("/onboarding?role=admin")
    assert r.status_code == 200 and 'name="role" value="founder" checked' in r.text


def test_an_account_with_a_role_is_not_moved_by_the_choice(client, fake):
    signed_in(client, fake, {"role": "investor", "status": "active", "full_name": "Ngozi Eze"})
    r = client.get("/onboarding?role=founder")
    assert r.status_code in (302, 303, 307) and r.headers["location"] == "/investor"
