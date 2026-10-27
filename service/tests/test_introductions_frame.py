"""The app frame and the introduction pages built on it (screens 08, 08.1, 09, 14 and 15), through HTTP."""

from __future__ import annotations

import re
from urllib.parse import parse_qs

import httpx

from app.product import day_month, initials
from app.routes.introductions import thread_items
from app.session import ACCESS_COOKIE

from .conftest import jwt
from .test_founder_score_pages import VENTURE

ME = "u-1"
INTRO = "6f1c1a3e-1111-4222-8333-944455556666"
OTHER = "7a2d2b4f-2222-4333-8444-a55566667777"


def intro(status: str, **extra) -> dict:
    row = {
        "id": INTRO, "venture_id": VENTURE["id"], "founder_id": ME, "investor_id": "u-2", "status": status,
        "note": "We back payments companies serving traders in Lagos.", "investor_name": "Ife Adeyemi",
        "investor_type": "fund", "investor_firm": "Savannah Seed", "venture_name": "Kola Pay", "founder_name": "Kemi Bello",
        "created_at": "2026-07-12T09:00:00Z", "decided_at": "2026-07-13T10:00:00Z" if status != "pending" else None,
    }
    row.update(extra)
    return row


def sign_in(client, fake, role: str, introductions, messages=None, count: int = 0):
    client.cookies.set(ACCESS_COOKIE, jwt())
    fake.on("GET", "/auth/v1/user", httpx.Response(200, json={"id": ME, "user_metadata": {"confirmed_adult": True}}))
    fake.on("GET", "/rest/v1/profiles", httpx.Response(200, json=[{"role": role, "status": "active", "full_name": "Kemi Bello"}]))
    fake.on("GET", "/rest/v1/ventures", httpx.Response(200, json=[VENTURE]))
    fake.on("GET", "/rest/v1/introductions", lambda r: httpx.Response(200, json=introductions(parse_qs(r.url.query.decode()))))
    fake.on("GET", "/rest/v1/introduction_messages", httpx.Response(200, json=messages or []))
    fake.on("HEAD", "/rest/v1/introduction_messages",
            httpx.Response(200, headers={"content-range": f"0-{max(count - 1, 0)}/{count}" if count else "*/0"}))


def test_initials_and_the_short_date():
    assert initials("Kemi Bello") == "KB"
    assert initials("ife adeyemi okoro") == "IA"
    assert initials("") == "?" and initials(None) == "?"
    assert day_month("2026-07-12T23:30:00Z") == "12 Jul"
    assert day_month(None) == ""


def test_the_thread_puts_a_day_before_each_new_day_and_marks_whose_each_item_is():
    i = intro("accepted")
    items = thread_items(i, [
        {"sender_id": ME, "body": "Thank you.", "created_at": "2026-07-13T11:00:00Z"},
        {"sender_id": "u-2", "body": "Tell me more.", "created_at": "2026-07-14T08:00:00Z"},
    ], ME)
    assert [x["kind"] for x in items] == ["day", "note", "day", "accepted", "msg", "day", "msg"]
    assert [x["body"] for x in items if x["kind"] == "day"] == ["12 July 2026", "13 July 2026", "14 July 2026"]
    note, accepted, mine, theirs = (x for x in items if x["kind"] != "day")
    assert not note["mine"] and accepted["mine"] and mine["mine"] and not theirs["mine"]
    # The investor's view of the same thread: their own note, and the founder's acceptance.
    seen = thread_items(i, [], "u-2")
    assert seen[1]["mine"] and not seen[3]["mine"]


def test_founder_pages_carry_the_app_frame_with_the_sidebar_and_the_bottom_bar(client, fake):
    sign_in(client, fake, "founder", lambda q: [])
    body = client.get("/dashboard/introductions").text
    assert '<link rel="stylesheet" href="/static/css/frame.css">' in body
    assert body.count('aria-label="Sections"') == 2 and 'class="fr-side"' in body and 'class="fr-tabs"' in body
    side = body.split('class="fr-nav"')[1].split("</nav>")[0]
    assert re.search(r'href="/dashboard/introductions" aria-current="page">.*?<span>Introductions</span>', side)
    tabs = body.split('class="fr-tabs"')[1].split("</nav>")[0]
    assert re.findall(r"</span>(\w+)</a>", tabs) == ["Home", "Pitch", "Evidence", "Activity", "Intros"]
    assert re.search(r'aria-current="page"><span class="fr-pill">.*?</span>Intros</a>', tabs)
    assert '<span class="fr-av" aria-hidden="true">KB</span>' in body


def test_a_request_waiting_opens_the_requests_tab_with_decline_and_accept(client, fake):
    sign_in(client, fake, "founder", lambda q: [intro("pending")])
    body = client.get("/dashboard/introductions").text
    assert 'href="/dashboard/introductions?tab=requests" aria-current="true">Requests<span class="n has">1</span>' in body
    assert "Ife Adeyemi" in body and "Fund investor · Savannah Seed" in body and '<span class="ic-date">12 Jul</span>' in body
    assert body.count('action="/dashboard/introductions/answer"') == 2
    assert '<input type="hidden" name="answer" value="declined"><button type="submit" class="btn btn-n">Decline</button>' in body
    assert '<input type="hidden" name="answer" value="accepted"><button type="submit" class="btn btn-f">Accept</button>' in body


def test_with_no_request_waiting_the_chats_tab_shows_the_latest_message_and_the_count(client, fake):
    sign_in(client, fake, "founder", lambda q: [intro("accepted")],
            messages=[{"sender_id": ME, "body": "We will both be there.", "created_at": "2026-07-24T12:00:00Z"}], count=37)
    body = client.get("/dashboard/introductions").text
    assert 'href="/dashboard/introductions?tab=chats" aria-current="true">Chats' in body
    assert "You wrote on 24 July 2026" in body and "We will both be there." in body
    assert "You accepted on 13 July 2026, and the conversation holds 37 messages." in body
    assert f'href="/introductions/{INTRO}"' in body
    # The count comes from a HEAD request that asks for an exact count.
    head = fake.sent("HEAD", "/rest/v1/introduction_messages")[0]
    assert head.headers["prefer"] == "count=exact" and f"introduction_id=eq.{INTRO}" in str(head.url)


def test_the_closed_tab_says_who_closed_each_request_and_when(client, fake):
    sign_in(client, fake, "founder", lambda q: [intro("declined"), intro("withdrawn", id=OTHER, investor_name="Tunde Bakare")])
    body = client.get("/dashboard/introductions?tab=closed").text
    assert "You declined on 13 July 2026." in body
    assert "The investor withdrew the request on 13 July 2026." in body


def test_the_investor_list_counts_each_tab_and_offers_the_right_action(client, fake):
    rows = [intro("pending", id=OTHER, venture_name="Market Day Pay"), intro("accepted")]
    sign_in(client, fake, "investor", lambda q: rows)
    body = client.get("/investor/introductions").text
    assert re.findall(r'\?tab=(\w+)"(?: aria-current="true")?>\w+<span class="n(?: has)?">(\d+)</span>', body) == [
        ("all", "2"), ("waiting", "1"), ("accepted", "1")]
    assert "Withdraw this request" in body and f'href="/introductions/{INTRO}"' in body
    waiting = client.get("/investor/introductions?tab=waiting").text
    assert "Market Day Pay" in waiting and f'href="/introductions/{INTRO}"' not in waiting


def test_the_conversation_lays_out_the_thread_lists_the_others_and_offers_the_report(client, fake):
    def introductions(q):
        return [intro("accepted")] if "id" in q else [intro("accepted"), intro("accepted", id=OTHER, investor_name="Tunde Bakare")]
    sign_in(client, fake, "founder", introductions,
            messages=[{"id": "m1", "sender_id": ME, "body": "Thank you for reaching out.", "created_at": "2026-07-13T11:00:00Z"}])
    body = client.get(f"/introductions/{INTRO}").text
    assert 'class="site pg-app frame app-f frame-chat"' in body
    assert body.count('class="ch-day"') == 2
    assert '<li class="ch-req theirs"><span>Introduction request</span>' in body
    assert '<li class="ch-event">You accepted this introduction.</li>' in body
    assert '<li class="bub mine"><span class="sr-only">You: </span>Thank you for reaching out.</li>' in body
    assert f'<a href="/introductions/{INTRO}" aria-current="page">' in body and f'<a href="/introductions/{OTHER}">' in body
    assert 'href="mailto:info@ikonetu.com?subject=Report%20about%20conversation%20' in body
    assert f'action="/introductions/{INTRO}/message"' in body and 'aria-label="Send"' in body
    # Only the conversations the person is part of and that are open are listed beside it.
    listed = [r for r in fake.sent("GET", "/rest/v1/introductions") if "status=eq.accepted" in str(r.url)]
    assert listed and f"founder_id=eq.{ME}" in str(listed[0].url)


def test_a_request_not_accepted_shows_no_box_to_write_in(client, fake):
    sign_in(client, fake, "founder", lambda q: [intro("declined")])
    body = client.get(f"/introductions/{INTRO}").text
    assert "Kemi Bello declined this request. There is no conversation." in body
    assert 'name="body"' not in body
