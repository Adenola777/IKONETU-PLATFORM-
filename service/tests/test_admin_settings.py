"""The Settings page: its forms, the rules the app then holds founders and investors to, and maintenance mode."""

from __future__ import annotations

import json

import httpx

from app import admin_settings as aset
from app import platform
from app.forms import parse_pitch
from app.platform import Rules

from .test_investor_register import ORIGIN, sign_in

SETTINGS = {"pitch_types": ["video/mp4", "video/webm", "video/quicktime"], "pitch_max_mb": 50, "pitch_max_seconds": 90,
            "introductions_on": True, "introductions_per_day": 10, "mode": "live",
            "maintenance_message": "IkonetU is being updated and will be back shortly.", "updated_at": "2026-10-24T09:00:00Z"}
STAFF = [{"user_id": "u-1", "full_name": "Ada Admin", "email": "ada@ikonetu.test", "role": "admin", "since": "2026-10-24T09:00:00Z"},
         {"user_id": "22222222-2222-4222-8222-222222222222", "full_name": "Rex Reviewer", "email": "rex@ikonetu.test",
          "role": "reviewer", "since": "2026-10-25T09:00:00Z"}]
STATUS = {"mode": "live", "maintenance_message": "Back at noon.", "pitch_types": ["video/mp4"], "pitch_max_mb": 20,
          "pitch_max_seconds": 60, "introductions_on": True, "introductions_per_day": 3}


def settings_signed_in(client, fake, settings: dict | None = None, role: str = "admin"):
    sign_in(client, fake, role=role)
    fake.on("POST", "/rest/v1/rpc/admin_settings", httpx.Response(200, json=[settings or SETTINGS]))
    fake.on("POST", "/rest/v1/rpc/admin_staff", httpx.Response(200, json=STAFF))


# ---------------------------------------------------------------- the forms
def test_the_pitch_rules_need_a_type_and_whole_numbers_in_range():
    assert aset.parse_pitch_rules([], "50", "90").error == "Allow at least one file type."
    assert aset.parse_pitch_rules(["mp4"], "51", "90").error == "Give the largest file as a whole number from 1 to 50 MB."
    assert aset.parse_pitch_rules(["mp4"], "2.5", "90").error == "Give the largest file as a whole number from 1 to 50 MB."
    assert aset.parse_pitch_rules(["mp4"], "10", "0").error == "Give the longest pitch as a whole number from 1 to 90 seconds."
    assert aset.parse_pitch_rules(["mov", "mp4", "avi"], " 10 ", "60").data == {
        "p_types": ["video/mp4", "video/quicktime"], "p_max_mb": 10, "p_max_seconds": 60}


def test_the_daily_limit_is_needed_only_while_introductions_are_on():
    assert aset.parse_introduction_rules(True, "0").error == "Give the daily limit as a whole number of 1 or more."
    assert aset.parse_introduction_rules(True, "12").data == {"p_on": True, "p_per_day": 12}
    assert aset.parse_introduction_rules(False, "").data == {"p_on": False, "p_per_day": None}


def test_maintenance_needs_a_message_of_no_more_than_280_characters():
    assert aset.parse_mode("maintenance", "  ").error == "Write the message people will see."
    assert aset.parse_mode("maintenance", "x" * 281).error == "Keep the message to 280 characters."
    assert aset.parse_mode("closed", "x").error == "Choose live or maintenance."
    assert aset.parse_mode("live", "").data == {"p_mode": "live", "p_message": None}


def test_a_new_password_is_typed_twice_and_supabases_refusals_are_explained():
    assert aset.parse_password("", "").error == "Type the new password."
    assert aset.parse_password("a-long-one", "another").error == "The two passwords do not match."
    assert aset.password_refusal("weak_password", 422) == "This password is too weak. Choose a longer one."
    assert aset.password_refusal("same_password", 422) == "This is the password you use now. Choose a new one."
    assert aset.password_refusal(None, 429).startswith("Too many changes were tried.")


def test_staff_are_added_by_the_email_of_an_existing_account():
    assert aset.parse_staff_add("not an email", "reviewer").error == "Enter the email address of an existing account."
    assert aset.parse_staff_add(" Rex@IkonetU.test ", "admin").data == {"p_email": "rex@ikonetu.test", "p_role": "admin"}
    assert aset.staff_refusal("no account uses this email address", "x@y.z") == "No account uses this email address."
    assert aset.staff_refusal("this account is on the staff list already", "x@y.z") == "x@y.z is already on the staff list."
    assert aset.removed_text("rex@ikonetu.test", "suspended").startswith("Removed rex@ikonetu.test from staff. The account is suspended")


# ---------------------------------------------------------------- the page
def test_the_settings_page_shows_the_rules_the_account_and_the_staff(client, fake):
    settings_signed_in(client, fake)
    body = client.get("/admin/settings").text
    assert '<input type="checkbox" name="types" value="webm" checked> WebM' in body
    assert 'name="per_day" class="a-input" inputmode="numeric" value="10">' in body
    assert '<input type="radio" name="mode" value="live" checked> Live: everyone can sign in' in body
    assert "<dt>Role</dt><dd>Admin</dd>" in body
    assert '<span class="a-note">You</span>' in body
    assert 'action="/admin/settings/staff/22222222-2222-4222-8222-222222222222/remove"' in body
    assert "Maintenance mode is on." not in body


def test_maintenance_is_said_at_the_top_of_the_settings(client, fake):
    settings_signed_in(client, fake, {**SETTINGS, "mode": "maintenance", "maintenance_message": "Back at noon."})
    assert "<strong>Maintenance mode is on.</strong> Founders and investors see: Back at noon." in client.get("/admin/settings").text


def test_saving_the_pitch_rules_sends_them_and_says_saved(client, fake):
    settings_signed_in(client, fake)
    fake.on("POST", "/rest/v1/rpc/admin_set_pitch_rules", httpx.Response(204))
    r = client.post("/admin/settings/pitch", data={"types": ["mp4", "webm"], "max_mb": "20", "max_seconds": "60"}, headers=ORIGIN)
    assert r.status_code == 303 and r.headers["location"] == "/admin/settings#pitch"
    assert json.loads(fake.sent("POST", "/rest/v1/rpc/admin_set_pitch_rules")[0].content) == {
        "p_types": ["video/mp4", "video/webm"], "p_max_mb": 20, "p_max_seconds": 60}
    assert '<p class="a-say a-say-ok" role="status">Saved.</p>' in client.get("/admin/settings").text


def test_a_rule_with_a_problem_is_shown_again_as_typed_and_nothing_is_sent(client, fake):
    settings_signed_in(client, fake)
    r = client.post("/admin/settings/pitch", data={"types": ["mov"], "max_mb": "80", "max_seconds": "60"}, headers=ORIGIN)
    assert r.status_code == 400
    assert "Give the largest file as a whole number from 1 to 50 MB." in r.text
    assert 'name="max_mb" class="a-input" inputmode="numeric" value="80">' in r.text
    assert '<input type="checkbox" name="types" value="mp4"> MP4' in r.text
    assert not fake.sent("POST", "/rest/v1/rpc/admin_set_pitch_rules")


def test_switching_introductions_off_and_putting_the_platform_in_maintenance(client, fake):
    settings_signed_in(client, fake)
    fake.on("POST", "/rest/v1/rpc/admin_set_introduction_rules", httpx.Response(204))
    fake.on("POST", "/rest/v1/rpc/admin_set_platform_mode", httpx.Response(204))
    assert client.post("/admin/settings/introductions", data={}, headers=ORIGIN).status_code == 303
    assert json.loads(fake.sent("POST", "/rest/v1/rpc/admin_set_introduction_rules")[0].content) == {"p_on": False, "p_per_day": None}
    r = client.post("/admin/settings/mode", data={"mode": "maintenance", "message": " Back at noon. "}, headers=ORIGIN)
    assert r.status_code == 303 and r.headers["location"] == "/admin/settings#status"
    assert json.loads(fake.sent("POST", "/rest/v1/rpc/admin_set_platform_mode")[0].content) == {
        "p_mode": "maintenance", "p_message": "Back at noon."}


def test_the_database_refusal_of_a_setting_is_shown_in_its_words(client, fake):
    settings_signed_in(client, fake)
    fake.on("POST", "/rest/v1/rpc/admin_set_platform_mode", httpx.Response(400, json={
        "code": "22023", "message": "keep the message to 280 characters"}))
    r = client.post("/admin/settings/mode", data={"mode": "live", "message": "Short."}, headers=ORIGIN)
    assert r.status_code == 400 and "Keep the message to 280 characters." in r.text


def test_the_admin_changes_their_own_password_through_supabase(client, fake):
    settings_signed_in(client, fake)
    fake.on("PUT", "/auth/v1/user", httpx.Response(200, json={"id": "u-1"}))
    r = client.post("/admin/settings/password", data={"password": "correct horse", "again": "correct horse"}, headers=ORIGIN)
    assert r.status_code == 303 and r.headers["location"] == "/admin/settings#account"
    sent = fake.sent("PUT", "/auth/v1/user")[0]
    assert json.loads(sent.content) == {"password": "correct horse"} and sent.headers["authorization"].startswith("Bearer ")
    assert "Password changed." in client.get("/admin/settings").text


def test_a_password_supabase_refuses_is_explained_and_never_shown_again(client, fake):
    settings_signed_in(client, fake)
    fake.on("PUT", "/auth/v1/user", httpx.Response(422, json={"code": 422, "error_code": "weak_password",
                                                                 "msg": "Password should be at least 6 characters."}))
    r = client.post("/admin/settings/password", data={"password": "abc", "again": "abc"}, headers=ORIGIN)
    assert r.status_code == 400 and "This password is too weak. Choose a longer one." in r.text
    assert 'value="abc"' not in r.text and '<details class="a-pw" open>' in r.text


def test_staff_are_added_and_removed(client, fake):
    settings_signed_in(client, fake)
    fake.on("POST", "/rest/v1/rpc/admin_staff_add", httpx.Response(200, json="33333333-3333-4333-8333-333333333333"))
    fake.on("POST", "/rest/v1/rpc/admin_staff_remove", httpx.Response(200, json="founder"))
    r = client.post("/admin/settings/staff", data={"email": "New@IkonetU.test", "role": "reviewer"}, headers=ORIGIN)
    assert r.status_code == 303
    assert "Added new@ikonetu.test as reviewer." in client.get("/admin/settings").text
    r = client.post("/admin/settings/staff/22222222-2222-4222-8222-222222222222/remove", headers=ORIGIN)
    assert r.status_code == 303
    assert json.loads(fake.sent("POST", "/rest/v1/rpc/admin_staff_remove")[0].content) == {
        "p_user": "22222222-2222-4222-8222-222222222222"}
    assert "Removed rex@ikonetu.test from staff. The account is a founder account again." in client.get("/admin/settings").text


def test_an_admin_cannot_remove_themselves(client, fake):
    settings_signed_in(client, fake)
    r = client.post("/admin/settings/staff/u-1/remove", headers=ORIGIN)
    assert r.status_code == 404 and not fake.sent("POST", "/rest/v1/rpc/admin_staff_remove")


def test_a_reviewer_cannot_open_or_change_the_settings(client, fake):
    settings_signed_in(client, fake, role="reviewer")
    assert client.get("/admin/settings").headers["location"] == "/admin"
    r = client.post("/admin/settings/mode", data={"mode": "maintenance", "message": "x"}, headers=ORIGIN)
    assert r.status_code == 303 and r.headers["location"] == "/admin"
    assert not fake.sent("POST", "/rest/v1/rpc/admin_set_platform_mode")


# ---------------------------------------------------------------- the rules where they apply
def test_the_pitch_form_holds_a_founder_to_the_rules_an_admin_set():
    rules = Rules(pitch_types=("video/webm",), pitch_max_mb=20, pitch_max_seconds=60)
    body = {"path": "11111111-1111-4111-8111-111111111111/22222222-2222-4222-8222-222222222222.mp4",
            "mimeType": "video/mp4", "size": 21 * 1024 * 1024, "duration": 61, "transcript": "x" * 30}
    errors = parse_pitch(body, rules).errors
    assert errors["mimeType"] == "Upload a WebM video."
    assert errors["size"] == "The video must be 20 MB or smaller."
    assert errors["duration"] == "Keep the pitch to 60 seconds or less."
    assert parse_pitch(body).errors.get("size") is None


def test_the_rules_are_read_once_and_kept_for_a_few_seconds(client, fake):
    fake.on("POST", "/rest/v1/rpc/platform_status", httpx.Response(200, json=[STATUS]))
    import asyncio
    from app.main import app
    first = asyncio.run(platform.rules(app.state.supabase))
    second = asyncio.run(platform.rules(app.state.supabase))
    assert first.pitch_max_mb == 20 and first.type_names == ["MP4"] and second is first
    assert len(fake.sent("POST", "/rest/v1/rpc/platform_status")) == 1


def test_the_rules_fall_back_to_the_databases_defaults_when_they_cannot_be_read(client, fake):
    from app.main import app
    import asyncio
    assert asyncio.run(platform.rules(app.state.supabase)) == Rules()


def test_in_maintenance_a_founder_sees_the_message_and_staff_pages_stay_open(client, fake):
    sign_in(client, fake, role="founder")
    fake.on("POST", "/rest/v1/rpc/platform_status", httpx.Response(200, json=[{**STATUS, "mode": "maintenance"}]))
    r = client.get("/dashboard")
    assert r.status_code == 503 and "Back at noon." in r.text and "IkonetU is closed for a short while." in r.text


def test_in_maintenance_the_sign_in_page_says_only_staff_can_sign_in(client, fake):
    fake.on("POST", "/rest/v1/rpc/platform_status", httpx.Response(200, json=[{**STATUS, "mode": "maintenance"}]))
    body = client.get("/signin").text
    assert "Back at noon. Only IkonetU staff can sign in until then." in body


def test_in_maintenance_a_staff_member_still_reaches_the_admin_pages(client, fake):
    settings_signed_in(client, fake)
    fake.on("POST", "/rest/v1/rpc/platform_status", httpx.Response(200, json=[{**STATUS, "mode": "maintenance"}]))
    assert client.get("/admin/settings").status_code == 200


# ---------------------------------------------------------------- introductions and sign-in under the rules
def test_an_investor_over_the_daily_limit_is_told_the_limit_an_admin_set(client, fake):
    from .test_founder_score_pages import VENTURE
    from .test_investor_frame import sign_in as investor_in, venture

    investor_in(client, fake)
    venture(fake)
    fake.on("POST", "/rest/v1/introductions", httpx.Response(400, json={
        "code": "P0001", "message": "you have reached the limit of 3 requests a day"}))
    r = client.post(f"/investor/ventures/{VENTURE['id']}/introduction",
                    data={"venture": VENTURE["id"], "note": "We back payments for market traders in Lagos."}, headers=ORIGIN)
    assert "You have reached the limit of three requests a day. Please try again tomorrow." in r.text


def test_an_investor_is_told_when_introductions_are_paused(client, fake):
    from .test_founder_score_pages import VENTURE
    from .test_investor_frame import sign_in as investor_in, venture

    investor_in(client, fake)
    venture(fake)
    fake.on("POST", "/rest/v1/rpc/platform_status", httpx.Response(200, json=[{**STATUS, "introductions_on": False}]))
    body = client.get(f"/investor/ventures/{VENTURE['id']}").text
    assert "IkonetU has paused introduction requests for now." in body
    assert f'action="/investor/ventures/{VENTURE["id"]}/introduction"' not in body
    fake.on("POST", "/rest/v1/introductions", httpx.Response(400, json={
        "code": "P0001", "message": "introduction requests are switched off"}))
    r = client.post(f"/investor/ventures/{VENTURE['id']}/introduction",
                    data={"venture": VENTURE["id"], "note": "We back payments for market traders in Lagos."}, headers=ORIGIN)
    assert "IkonetU has paused introduction requests for now. Please try again later." in r.text


def test_the_investors_introductions_page_states_the_daily_limit(client, fake):
    from .test_investor_frame import sign_in as investor_in

    investor_in(client, fake)
    fake.on("GET", "/rest/v1/introductions", httpx.Response(200, json=[]))
    fake.on("POST", "/rest/v1/rpc/platform_status", httpx.Response(200, json=[STATUS]))
    assert "You can send up to three requests a day." in client.get("/investor/introductions").text


def test_in_maintenance_a_founders_new_sign_in_is_signed_out_again(client, fake):
    from app.session import ACCESS_COOKIE
    from app.signin import PENDING_COOKIE

    from .test_signin_and_sessions import cookie, pending_cookie, session_body

    fake.on("POST", "/rest/v1/rpc/platform_status", httpx.Response(200, json=[{**STATUS, "mode": "maintenance"}]))
    fake.on("POST", "/auth/v1/verify", httpx.Response(200, json=session_body()))
    fake.on("GET", "/rest/v1/profiles", httpx.Response(200, json=[{"role": "founder", "status": "active"}]))
    fake.on("POST", "/auth/v1/logout", httpx.Response(204))
    client.cookies.set(PENDING_COOKIE, pending_cookie(), path="/signin")
    r = client.post("/signin/code", data={"code": "123456"})
    assert r.status_code == 503 and "Back at noon." in r.text
    assert cookie(r, ACCESS_COOKIE) is None and fake.sent("POST", "/auth/v1/logout")


def test_in_maintenance_a_reviewer_still_signs_in(client, fake):
    from .test_signin_and_sessions import pending_cookie, session_body
    from app.signin import PENDING_COOKIE

    fake.on("POST", "/rest/v1/rpc/platform_status", httpx.Response(200, json=[{**STATUS, "mode": "maintenance"}]))
    fake.on("POST", "/auth/v1/verify", httpx.Response(200, json=session_body()))
    fake.on("GET", "/rest/v1/profiles", httpx.Response(200, json=[{"role": "reviewer", "status": "active"}]))
    client.cookies.set(PENDING_COOKIE, pending_cookie(), path="/signin")
    r = client.post("/signin/code", data={"code": "123456"})
    assert r.status_code == 303 and r.headers["location"] == "/dashboard"
    assert not fake.sent("POST", "/auth/v1/logout")
