"""Sign-in, the email link, sessions and their refresh, signing out, the origin check and the headers."""

from __future__ import annotations

import json
import urllib.parse

import httpx

from app.session import ACCESS_COOKIE, REFRESH_COOKIE
from app.signin import PENDING_COOKIE, VERIFIER_COOKIE, Pending, now_ms
from app.supabase import pkce_challenge

from .conftest import jwt


def session_body(access: str | None = None, refresh: str = "r-new") -> dict:
    return {"access_token": access or jwt(), "refresh_token": refresh, "expires_at": 0, "user": {"id": "u-1"}}


def set_cookie_headers(response) -> list[str]:
    return response.headers.get_list("set-cookie")


def cookie(response, name: str) -> str | None:
    for h in set_cookie_headers(response):
        if h.startswith(f"{name}="):
            return h
    return None


# ---------------------------------------------------------------- the email step
def test_the_sign_in_page_asks_for_an_email_and_stays_out_of_search(client):
    r = client.get("/signin")
    assert r.status_code == 200
    assert 'id="s-email"' in r.text and '<meta name="robots" content="noindex">' in r.text
    assert "<title>Sign in | IkonetU</title>" in r.text


def test_a_bad_email_and_a_missing_age_box_are_named_under_their_fields(client, fake):
    r = client.post("/signin", data={"method": "email", "email": "amara@"})
    assert r.status_code == 200
    assert '<p class="status status-err" role="alert">Please check the form.</p>' in r.text
    assert '<p id="email-err" class="err">Enter a valid email address.</p>' in r.text
    assert '<p id="confirmedAdult-err" class="err">You must be 18 or older to join.</p>' in r.text
    assert 'value="amara@"' in r.text
    assert fake.requests == []


def test_a_good_email_asks_supabase_for_a_code_with_a_pkce_challenge(client, fake):
    fake.on("POST", "/auth/v1/otp", httpx.Response(200, json={}))
    r = client.post("/signin", data={"method": "email", "email": " Amara@Example.com ", "confirmedAdult": "on"})
    assert r.status_code == 303 and r.headers["location"] == "/signin/code"
    sent = fake.sent("POST", "/auth/v1/otp")[0]
    body = json.loads(sent.content)
    assert body["email"] == "amara@example.com"
    assert body["data"] == {"confirmed_adult": True} and body["create_user"] is True
    assert body["code_challenge_method"] == "s256" and len(body["code_challenge"]) == 43
    assert sent.url.params["redirect_to"] == "http://localhost:3000/auth/callback"
    assert sent.headers["apikey"] == "sb_publishable_test"
    pending = cookie(r, PENDING_COOKIE)
    verifier = cookie(r, VERIFIER_COOKIE)
    assert "HttpOnly" in pending and "Path=/signin" in pending and "SameSite=lax" in pending
    assert "HttpOnly" in verifier and "Path=/;" in verifier
    value = verifier.split(";")[0].split("=", 1)[1]
    assert len(value) == 112 and pkce_challenge(value) == body["code_challenge"]


def test_too_many_codes_is_said_plainly(client, fake):
    fake.on("POST", "/auth/v1/otp", httpx.Response(429, json={"code": 429, "error_code": "over_email_send_rate_limit", "msg": "x"}))
    r = client.post("/signin", data={"method": "email", "email": "amara@example.com", "confirmedAdult": "on"})
    assert "Too many codes were requested. Please wait a few minutes and try again." in r.text


# ---------------------------------------------------------------- the code step
def pending_cookie(email: str = "amara@example.com", sent_at: int | None = None) -> str:
    return Pending(kind="email", email=email, sent_at=sent_at if sent_at is not None else now_ms()).encode()


def test_the_code_page_needs_a_sign_in_under_way(client):
    r = client.get("/signin/code")
    assert r.status_code == 307 and r.headers["location"] == "/signin"


def test_the_code_page_says_where_the_email_went_and_counts_down(client):
    client.cookies.set(PENDING_COOKIE, pending_cookie(), path="/signin")
    r = client.get("/signin/code")
    assert "We sent an email to amara@example.com." in r.text
    assert "The code expires in 5:00." in r.text or "The code expires in 4:59." in r.text


def test_a_wrong_code_is_refused_and_a_right_one_opens_an_http_only_session(client, fake):
    client.cookies.set(PENDING_COOKIE, pending_cookie(), path="/signin")
    fake.on("POST", "/auth/v1/verify", httpx.Response(403, json={"code": 403, "error_code": "otp_expired", "msg": "expired"}))
    r = client.post("/signin/code", data={"code": "123 456"})
    assert "That code is wrong or has expired." in r.text
    assert '<p id="code-err" class="err">Check the code and try again, or ask for a new one.</p>' in r.text
    assert json.loads(fake.sent("POST", "/auth/v1/verify")[0].content)["token"] == "123456"

    fake.on("POST", "/auth/v1/verify", httpx.Response(200, json=session_body()))
    r = client.post("/signin/code", data={"code": "123456"})
    assert r.status_code == 303 and r.headers["location"] == "/dashboard"
    for name in (ACCESS_COOKIE, REFRESH_COOKIE):
        c = cookie(r, name)
        assert c and "HttpOnly" in c and "Path=/" in c and "SameSite=lax" in c
    assert cookie(r, PENDING_COOKIE).startswith(f'{PENDING_COOKIE}="";') or "Max-Age=0" in cookie(r, PENDING_COOKIE)


def test_a_code_that_is_not_six_digits_is_refused_before_supabase(client, fake):
    client.cookies.set(PENDING_COOKIE, pending_cookie(), path="/signin")
    r = client.post("/signin/code", data={"code": "12345"})
    assert '<p id="code-err" class="err">Enter the 6-digit code.</p>' in r.text
    assert fake.requests == []


def test_a_new_code_keeps_the_first_links_verifier(client, fake):
    client.cookies.set(PENDING_COOKIE, pending_cookie(sent_at=now_ms() - 200_000), path="/signin")
    client.cookies.set(VERIFIER_COOKIE, "ab" * 56, path="/")
    fake.on("POST", "/auth/v1/otp", httpx.Response(200, json={}))
    r = client.post("/signin/code/resend", data={})
    assert r.status_code == 303
    body = json.loads(fake.sent("POST", "/auth/v1/otp")[0].content)
    assert body["code_challenge"] == pkce_challenge("ab" * 56)
    assert cookie(r, VERIFIER_COOKIE) is None
    page = client.get("/signin/code")
    assert '<p class="status status-ok" role="status">We sent a new code.</p>' in page.text


# ---------------------------------------------------------------- the link in the email
def test_the_email_link_exchanges_its_code_with_this_browsers_verifier(client, fake):
    client.cookies.set(VERIFIER_COOKIE, "cd" * 56, path="/")
    fake.on("POST", "/auth/v1/token", httpx.Response(200, json=session_body()))
    r = client.get("/auth/callback?code=abc")
    assert r.status_code == 307 and r.headers["location"] == "/dashboard"
    sent = fake.sent("POST", "/auth/v1/token")[0]
    assert sent.url.params["grant_type"] == "pkce"
    assert json.loads(sent.content) == {"auth_code": "abc", "code_verifier": "cd" * 56}
    assert cookie(r, ACCESS_COOKIE)


def test_a_link_opened_in_another_browser_asks_for_a_new_code(client, fake):
    r = client.get("/auth/callback?code=abc")
    assert r.status_code == 307 and r.headers["location"] == "/signin?error=link"
    assert fake.requests == []
    page = client.get("/signin?error=link")
    assert "That sign-in link has expired or was already used." in page.text


# ---------------------------------------------------------------- sessions
def test_a_signed_in_person_is_sent_on_from_the_sign_in_page(client, fake):
    token = jwt()
    client.cookies.set(ACCESS_COOKIE, token)
    fake.on("GET", "/auth/v1/user", httpx.Response(200, json={"id": "u-1"}))
    r = client.get("/signin")
    assert r.status_code == 307 and r.headers["location"] == "/dashboard"
    assert fake.sent("GET", "/auth/v1/user")[0].headers["authorization"] == f"Bearer {token}"


def test_an_expired_access_token_is_refreshed_before_it_is_used(client, fake):
    client.cookies.set(ACCESS_COOKIE, jwt(exp_in=-10))
    client.cookies.set(REFRESH_COOKIE, "r-old")
    fresh = jwt(exp_in=900)
    fake.on("POST", "/auth/v1/token", httpx.Response(200, json=session_body(fresh, "r-next")))
    fake.on("GET", "/auth/v1/user", httpx.Response(200, json={"id": "u-1"}))
    r = client.get("/signin")
    assert r.status_code == 307
    assert json.loads(fake.sent("POST", "/auth/v1/token")[0].content) == {"refresh_token": "r-old"}
    assert fake.sent("GET", "/auth/v1/user")[0].headers["authorization"] == f"Bearer {fresh}"
    assert cookie(r, REFRESH_COOKIE).startswith(f"{REFRESH_COOKIE}=r-next;")


def test_a_refused_refresh_signs_the_person_out(client, fake):
    client.cookies.set(ACCESS_COOKIE, jwt(exp_in=-10))
    client.cookies.set(REFRESH_COOKIE, "r-revoked")
    fake.on("POST", "/auth/v1/token", httpx.Response(400, json={"error_code": "refresh_token_not_found", "msg": "x"}))
    r = client.get("/signin")
    assert r.status_code == 200
    assert "Max-Age=0" in cookie(r, ACCESS_COOKIE) and "Max-Age=0" in cookie(r, REFRESH_COOKIE)


def test_a_token_supabase_refuses_is_refreshed_once(client, fake):
    client.cookies.set(ACCESS_COOKIE, jwt())
    client.cookies.set(REFRESH_COOKIE, "r-old")
    calls = {"n": 0}

    def user(_r):
        calls["n"] += 1
        return httpx.Response(401, json={"msg": "bad"}) if calls["n"] == 1 else httpx.Response(200, json={"id": "u-1"})
    fake.on("GET", "/auth/v1/user", user)
    fake.on("POST", "/auth/v1/token", httpx.Response(200, json=session_body()))
    assert client.get("/signin").status_code == 307
    assert calls["n"] == 2


def test_signing_out_ends_the_session_at_supabase_and_clears_the_cookies(client, fake):
    token = jwt()
    client.cookies.set(ACCESS_COOKIE, token)
    fake.on("GET", "/auth/v1/user", httpx.Response(200, json={"id": "u-1"}))
    fake.on("POST", "/auth/v1/logout", httpx.Response(204))
    r = client.post("/signout")
    assert r.status_code == 303 and r.headers["location"] == "/"
    sent = fake.sent("POST", "/auth/v1/logout")[0]
    assert sent.headers["authorization"] == f"Bearer {token}" and sent.url.params["scope"] == "global"
    assert "Max-Age=0" in cookie(r, ACCESS_COOKIE)


# ---------------------------------------------------------------- the origin check and the headers
def test_a_form_sent_from_another_site_is_refused(client, fake):
    r = client.post("/signin", data={"email": "a@b.co", "confirmedAdult": "on"}, headers={"origin": "https://evil.example"})
    assert r.status_code == 403
    assert fake.requests == []
    ok = client.post("/signin", data={"email": "amara@"}, headers={"origin": "http://testserver"})
    assert ok.status_code == 200


def test_every_response_carries_the_security_headers(client):
    r = client.get("/signin")
    csp = r.headers["content-security-policy"]
    assert "script-src 'self';" in csp and "'unsafe-inline'" not in csp.split("style-src")[0]
    assert "frame-ancestors 'none'" in csp and "form-action 'self'" in csp
    assert r.headers["x-frame-options"] == "DENY"
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["strict-transport-security"].startswith("max-age=63072000")
    assert client.get("/no-such-page").headers["x-frame-options"] == "DENY"



def test_static_files_are_checked_with_the_server_before_reuse(client):
    # A browser kept an old stylesheet on 28 October 2026, and the new pricing page drew a bullet beside each tick.
    r = client.get("/static/css/site.css")
    assert r.status_code == 200 and r.headers["cache-control"] == "no-cache"
    again = client.get("/static/css/site.css", headers={"if-none-match": r.headers["etag"]})
    assert again.status_code == 304 and again.content == b""
    assert client.get("/media/tour-music.mp3").headers["cache-control"] == "no-cache"

def test_an_unknown_address_answers_404_with_the_not_found_page(client):
    r = client.get("/no-such-page")
    assert r.status_code == 404 and "This page does not exist." in r.text
