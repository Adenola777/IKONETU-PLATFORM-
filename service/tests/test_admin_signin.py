"""The admin sign-in at /admin/signin: an email address and a password, for admins only, through HTTP."""

from __future__ import annotations

import json

import httpx
import pytest

from app.routes import auth
from app.session import ACCESS_COOKIE

from .conftest import jwt

ORIGIN = {"origin": "http://testserver"}
SESSION = {"access_token": jwt(sub="u-9"), "refresh_token": "r-9", "expires_at": 4_102_444_800, "user": {"id": "u-9"}}


@pytest.fixture(autouse=True)
def fresh_limits():
    auth.admin_by_address._hits.clear()
    auth.admin_by_email._hits.clear()
    yield
    auth.admin_by_address._hits.clear()
    auth.admin_by_email._hits.clear()


def profile_reply(role: str | None, status: str = "active"):
    return httpx.Response(200, json=[{"role": role, "status": status}] if role else [])


def test_the_admin_sign_in_is_a_page_of_its_own_with_a_password_and_no_code():
    from fastapi.testclient import TestClient

    from app.main import app
    with TestClient(app) as c:
        body = c.get("/admin/signin").text
    assert '<div class="site pg-signin pg-admin">' in body
    assert "Sign in to the admin dashboard" in body and "For IkonetU admins only." in body
    assert 'type="password" autocomplete="current-password"' in body
    assert "Send my code" not in body and "I am 18 or older." not in body and "6-digit code" not in body
    assert '<a href="/signin">main sign-in page</a>' in body


def test_a_signed_out_visit_to_any_admin_page_goes_to_the_admin_sign_in(client):
    for path in ("/admin", "/admin/register", "/admin/people", "/admin/evidence"):
        r = client.get(path)
        assert r.status_code == 307 and r.headers["location"] == "/admin/signin", path


def test_an_admin_signs_in_with_the_email_address_and_password(client, fake):
    fake.on("POST", "/auth/v1/token", httpx.Response(200, json=SESSION))
    fake.on("GET", "/rest/v1/profiles", profile_reply("admin"))
    r = client.post("/admin/signin", data={"email": " Admin@IkonetU.com ", "password": " a pass phrase "}, headers=ORIGIN)
    assert r.status_code == 303 and r.headers["location"] == "/admin"
    assert f"{ACCESS_COOKIE}=" in r.headers["set-cookie"]
    sent = fake.sent("POST", "/auth/v1/token")[0]
    assert sent.url.params["grant_type"] == "password"
    body = json.loads(sent.content)
    assert body["email"] == "admin@ikonetu.com" and body["password"] == " a pass phrase "
    assert not fake.sent("POST", "/auth/v1/logout")


def test_a_wrong_password_is_refused_without_saying_whether_the_account_exists(client, fake):
    fake.on("POST", "/auth/v1/token", httpx.Response(400, json={"code": 400, "error_code": "invalid_credentials",
                                                                 "msg": "Invalid login credentials"}))
    r = client.post("/admin/signin", data={"email": "admin@ikonetu.com", "password": "wrong"}, headers=ORIGIN)
    assert r.status_code == 200
    assert "That email address and password do not match an admin account." in r.text
    assert 'value="admin@ikonetu.com"' in r.text and 'value="wrong"' not in r.text
    assert ACCESS_COOKIE not in r.headers.get("set-cookie", "")


@pytest.mark.parametrize("role,status", [("founder", "active"), ("investor", "active"), ("reviewer", "active"),
                                         ("admin", "suspended"), (None, "active")])
def test_an_account_that_is_not_an_active_admin_is_signed_out_again_and_told_the_same(client, fake, role, status):
    fake.on("POST", "/auth/v1/token", httpx.Response(200, json=SESSION))
    fake.on("GET", "/rest/v1/profiles", profile_reply(role, status))
    fake.on("POST", "/auth/v1/logout", httpx.Response(204))
    r = client.post("/admin/signin", data={"email": "someone@ikonetu.com", "password": "right"}, headers=ORIGIN)
    assert r.status_code == 200
    assert "That email address and password do not match an admin account." in r.text
    assert ACCESS_COOKIE not in r.headers.get("set-cookie", "")
    assert len(fake.sent("POST", "/auth/v1/logout")) == 1


def test_a_form_with_problems_is_shown_again_and_nothing_is_sent(client, fake):
    r = client.post("/admin/signin", data={"email": "admin@", "password": ""}, headers=ORIGIN)
    assert r.status_code == 200
    assert "Enter a valid email address." in r.text and "Enter your password." in r.text
    assert not fake.sent("POST", "/auth/v1/token")


def test_five_tries_for_one_address_then_a_wait(client, fake):
    fake.on("POST", "/auth/v1/token", httpx.Response(400, json={"error_code": "invalid_credentials", "msg": "x"}))
    for _ in range(5):
        assert client.post("/admin/signin", data={"email": "admin@ikonetu.com", "password": "guess"}, headers=ORIGIN).status_code == 200
    r = client.post("/admin/signin", data={"email": "admin@ikonetu.com", "password": "guess"}, headers=ORIGIN)
    assert r.status_code == 429 and "Too many attempts. Please wait 15 minutes and try again." in r.text
    assert len(fake.sent("POST", "/auth/v1/token")) == 5


def test_supabases_own_limit_is_explained(client, fake):
    fake.on("POST", "/auth/v1/token", httpx.Response(429, json={"error_code": "over_request_rate_limit", "msg": "x"}))
    r = client.post("/admin/signin", data={"email": "admin@ikonetu.com", "password": "guess"}, headers=ORIGIN)
    assert r.status_code == 429 and "Too many attempts." in r.text


def test_an_admin_signs_out_to_the_admin_sign_in_and_everyone_else_to_the_home_page(client, fake):
    r = client.post("/signout", data={"next": "/admin/signin"}, headers=ORIGIN)
    assert r.status_code == 303 and r.headers["location"] == "/admin/signin?done=out"
    assert "You are signed out." in client.get("/admin/signin?done=out").text
    for data in ({}, {"next": "https://evil.example"}):
        r = client.post("/signout", data=data, headers=ORIGIN)
        assert r.headers["location"] == "/", data


def test_the_admin_pages_sign_out_returns_to_the_admin_sign_in(client, fake):
    client.cookies.set(ACCESS_COOKIE, jwt())
    fake.on("GET", "/auth/v1/user", httpx.Response(200, json={"id": "u-1", "user_metadata": {"confirmed_adult": True}}))
    fake.on("GET", "/rest/v1/profiles", httpx.Response(200, json=[{"role": "admin", "status": "active", "full_name": "Ada"}]))
    fake.on("POST", "/rest/v1/rpc/admin_register_months", httpx.Response(200, json=[]))
    fake.on("POST", "/rest/v1/rpc/admin_register", httpx.Response(200, json=[]))
    body = client.get("/admin/register").text
    assert '<input type="hidden" name="next" value="/admin/signin">' in body
    assert client.get("/admin/signin").headers["location"] == "/admin"
