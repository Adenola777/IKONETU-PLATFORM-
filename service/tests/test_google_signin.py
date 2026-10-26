"""Sign-in with Google: the button, the start at /signin/google, and the return to /auth/callback, through HTTP.

Google's own screens and Supabase's provider settings are not reached here. The fake answers the code
exchange as the PKCE flow does for an email link, which is the step this app shares with Google sign-in.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
from urllib.parse import parse_qs, urlsplit

import httpx

from app.routes import auth
from app.signin import VERIFIER_COOKIE, VIA_COOKIE
from app.supabase import pkce_challenge

from .conftest import URL
from .test_signin_and_sessions import cookie, session_body


def google_on(monkeypatch):
    monkeypatch.setattr(auth, "settings", replace(auth.settings, google_sign_in=True))


def test_with_google_sign_in_off_there_is_no_button_and_the_start_goes_back(client):
    body = client.get("/signin").text
    assert 'class="au-google"' not in body and "Continue with Google" not in body
    r = client.get("/signin/google")
    assert r.status_code == 303 and r.headers["location"] == "/signin"


def test_with_google_sign_in_on_the_button_stands_above_the_email_form(client, monkeypatch):
    google_on(monkeypatch)
    body = client.get("/signin").text
    assert '<a class="au-google" href="/signin/google"><img src="/static/img/google-g.png" alt="" width="20" height="20">Continue with Google</a>' in body
    assert body.index('class="au-google"') < body.index('<p class="au-or"><span>or</span></p>') < body.index('id="s-email"')
    assert "Continue with Google, or enter your email, to create your account or to sign back in." in body
    assert client.get("/static/img/google-g.png").status_code == 200


def test_the_start_sends_the_browser_to_supabase_with_a_challenge_for_its_own_verifier(client, monkeypatch):
    google_on(monkeypatch)
    r = client.get("/signin/google")
    assert r.status_code == 303
    where = urlsplit(r.headers["location"])
    assert f"{where.scheme}://{where.netloc}{where.path}" == f"{URL}/auth/v1/authorize"
    query = {k: v[0] for k, v in parse_qs(where.query).items()}
    assert query["provider"] == "google" and query["code_challenge_method"] == "s256"
    assert query["redirect_to"] == "http://localhost:3000/auth/callback"
    verifier = re.search(rf"{VERIFIER_COOKIE}=([^;]+)", cookie(r, VERIFIER_COOKIE)).group(1)
    assert query["code_challenge"] == pkce_challenge(verifier)
    via = cookie(r, VIA_COOKIE)
    assert via.startswith(f"{VIA_COOKIE}=google;") and "Path=/auth" in via and "HttpOnly" in via


def test_the_return_from_google_becomes_a_session_and_clears_the_marker(client, fake):
    client.cookies.set(VERIFIER_COOKIE, "ab" * 56, path="/")
    client.cookies.set(VIA_COOKIE, "google", path="/auth")
    fake.on("POST", "/auth/v1/token", httpx.Response(200, json=session_body()))
    r = client.get("/auth/callback?code=xyz")
    assert r.status_code == 307 and r.headers["location"] == "/dashboard"
    sent = fake.sent("POST", "/auth/v1/token")[0]
    assert sent.url.params["grant_type"] == "pkce"
    assert json.loads(sent.content) == {"auth_code": "xyz", "code_verifier": "ab" * 56}
    assert cookie(r, VIA_COOKIE).startswith(f'{VIA_COOKIE}=""')


def test_a_google_sign_in_that_does_not_finish_says_so_and_not_that_a_link_expired(client, fake):
    client.cookies.set(VERIFIER_COOKIE, "ab" * 56, path="/")
    client.cookies.set(VIA_COOKIE, "google", path="/auth")
    r = client.get("/auth/callback?error=access_denied&error_description=The+user+denied")
    assert r.status_code == 307 and r.headers["location"] == "/signin?error=google"
    assert fake.requests == []
    page = client.get("/signin?error=google").text
    assert "Signing in with Google did not finish. Please try again." in page
    assert "That sign-in link has expired" not in page


def test_an_email_link_that_fails_still_speaks_of_the_link(client, fake):
    client.cookies.set(VERIFIER_COOKIE, "ab" * 56, path="/")
    fake.on("POST", "/auth/v1/token", httpx.Response(403, json={"code": 403, "error_code": "bad_code_verifier", "msg": "no"}))
    r = client.get("/auth/callback?code=xyz")
    assert r.headers["location"] == "/signin?error=link"
