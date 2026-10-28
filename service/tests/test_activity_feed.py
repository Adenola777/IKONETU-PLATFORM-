"""The activity feed: its sentences, the page for founders and investors, the live check, and what
replaced the founder's posted updates, through HTTP.

The database's own rules for the feed (who reads which entry, and what makes one) are checked in
supabase/tests/07_activity_checks.sql. Here the fake answers activity_feed() as the database would.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone

import httpx

from app.activity import ago_text, entry_text, feed_entry

from .test_founder_score_pages import VENTURE
from .test_founder_score_pages import sign_in as founder_sign_in
from .test_investor_frame import sign_in as investor_sign_in
from .test_investor_frame import venture as investor_venture

NOW = datetime.now(timezone.utc)


def row(kind: str, n: int = 1, venture: str = "Kola Farms", detail: dict | None = None, at: datetime | None = None) -> dict:
    return {
        "id": n, "kind": kind, "venture_id": "9f000000-0000-0000-0000-00000000000f", "venture_name": venture,
        "sector": "Agritech", "country": "GH", "detail": detail or {}, "created_at": (at or NOW).isoformat(),
    }


FEED = [
    row("introduction_accepted", 6, detail={"investor_type": "angel"}),
    row("evidence_approved", 5, detail={"signal_code": "company_registration", "outside": True}),
    row("evidence_approved", 4, detail={"signal_code": "revenue", "outside": False}),
    row("ask_set", 3),
    row("published", 2),
    row("pitch_added", 1, at=NOW - timedelta(days=3)),
]


def feed(fake, rows=None, status: int = 200):
    fake.on("POST", "/rest/v1/rpc/activity_feed",
            httpx.Response(status, json=FEED if rows is None else rows) if status == 200 else httpx.Response(status, json={"message": "down"}))


def sent_args(fake) -> list[dict]:
    return [json.loads(r.content) for r in fake.sent("POST", "/rest/v1/rpc/activity_feed")]


# ---------------------------------------------------------------- the sentences
def test_each_kind_of_entry_reads_as_one_sentence_that_starts_with_the_venture():
    assert [entry_text(r) for r in FEED] == [
        "Kola Farms accepted an introduction from an angel investor.",
        "Kola Farms has third-party evidence in Registration.",
        "Kola Farms has platform-reviewed evidence in Financial.",
        "Kola Farms set out what it is raising.",
        "Kola Farms published its profile.",
        "Kola Farms added a pitch.",
    ]
    assert entry_text(row("pitch_replaced")) == "Kola Farms recorded a new pitch."
    assert entry_text(row("introduction_accepted", detail={"investor_type": "fund"})) == "Kola Farms accepted an introduction from a fund."
    assert entry_text(row("introduction_accepted", detail={"investor_type": "individual"})) == \
        "Kola Farms accepted an introduction from an individual investor."


def test_an_entry_says_where_the_venture_is_and_only_an_investor_may_open_it():
    e = feed_entry(FEED[0], can_open=True)
    assert e["place"] == "Agritech · Ghana" and e["icon"] == "handshake"
    assert e["href"] == "/investor/ventures/9f000000-0000-0000-0000-00000000000f"
    assert feed_entry(FEED[0], can_open=False)["href"] is None
    assert [feed_entry(r, False)["icon"] for r in FEED[1:3]] == ["link", "shield-check"]


def test_the_time_of_an_entry_reads_as_today_yesterday_days_or_a_date():
    assert ago_text(NOW.isoformat(), NOW) == "Today"
    assert ago_text((NOW - timedelta(days=1)).isoformat(), NOW) == "Yesterday"
    assert ago_text((NOW - timedelta(days=9)).isoformat(), NOW) == "9 days ago"
    assert ago_text("2026-01-05T10:00:00Z", datetime(2026, 10, 27, tzinfo=timezone.utc)) == "5 January 2026"


# ---------------------------------------------------------------- the page
def test_a_founder_sees_every_entry_without_links_to_other_founders_profiles(client, fake):
    founder_sign_in(client, fake)
    feed(fake)
    body = client.get("/activity").text
    assert '<h1 class="fr-h1">Activity</h1>' in body
    assert body.count("<li class=\"act-") == 6 and "View profile" not in body
    assert "Kola Farms accepted an introduction from an angel investor." in body
    assert body.count("<span>Agritech · Ghana</span>") == 6 and "3 days ago" in body
    assert re.search(r'href="/activity" aria-current="page">.*?<span>Activity</span>', body.split('class="fr-nav"')[1])
    assert re.search(r'aria-current="page"><span class="fr-pill">.*?</span>Activity</a>', body.split('class="fr-tabs"')[1])
    assert '<script src="/static/js/app/feed-live.js" defer></script>' in body
    assert f'data-newest="{FEED[0]["created_at"]}"' in body
    assert sent_args(fake) == [{"p_limit": 30}]


def test_an_investor_can_open_each_venture_from_the_feed(client, fake):
    investor_sign_in(client, fake)
    feed(fake)
    body = client.get("/activity").text
    assert body.count('<a href="/investor/ventures/9f000000-0000-0000-0000-00000000000f">View profile</a>') == 6
    assert 'class="site pg-app frame app-i"' in body
    tabs = re.findall(r"</span>(\w+)</a>", body.split('class="fr-tabs"')[1].split("</nav>")[0])
    assert tabs == ["Discover", "Activity", "Intros", "Profile"]


def test_the_page_names_no_investor_and_escapes_what_a_founder_typed(client, fake):
    founder_sign_in(client, fake)
    feed(fake, [row("published", venture='<script>alert("x")</script> Farms')])
    body = client.get("/activity").text
    assert '<script>alert("x")</script>' not in body and "&lt;script&gt;alert(&#34;x&#34;)&lt;/script&gt; Farms published its profile." in body


def test_an_empty_feed_says_so_and_still_listens_for_new_entries(client, fake):
    founder_sign_in(client, fake)
    feed(fake, [])
    body = client.get("/activity").text
    assert "Nothing has happened yet." in body and '<p class="fr-empty" data-activity-empty>' in body
    assert 'data-newest="1970-01-01T00:00:00Z" hidden' in body


def test_a_full_page_links_to_older_entries_and_an_older_page_reads_before_its_oldest(client, fake):
    founder_sign_in(client, fake)
    rows = [row("ask_set", n, at=NOW - timedelta(minutes=n)) for n in range(1, 31)]
    feed(fake, rows)
    body = client.get("/activity").text
    oldest = rows[-1]["created_at"]
    assert f'href="/activity?before={oldest.replace(":", "%3A").replace("+", "%2B")}"' in body
    body = client.get("/activity", params={"before": oldest}).text
    assert sent_args(fake)[-1] == {"p_limit": 30, "p_before": oldest}
    assert "Back to the newest entries" in body and "feed-live.js" not in body


def test_a_before_that_is_not_a_moment_is_ignored(client, fake):
    founder_sign_in(client, fake)
    feed(fake)
    client.get("/activity", params={"before": "yesterday'; drop table"})
    assert sent_args(fake) == [{"p_limit": 30}]


def test_a_feed_that_cannot_be_read_says_so(client, fake):
    founder_sign_in(client, fake)
    feed(fake, status=500)
    body = client.get("/activity").text
    assert "The activity feed could not be loaded. Please try again in a moment." in body and "feed-live.js" not in body


def test_only_founders_and_approved_investors_reach_the_feed(client, fake):
    r = client.get("/activity")
    assert r.status_code == 307 and r.headers["location"] == "/signin"
    investor_sign_in(client, fake, status="pending")
    r = client.get("/activity")
    assert r.status_code == 307 and r.headers["location"] == "/investor/pending"
    assert fake.sent("POST", "/rest/v1/rpc/activity_feed") == []


# ---------------------------------------------------------------- the live check
def test_the_live_check_answers_new_entries_as_list_items(client, fake):
    founder_sign_in(client, fake)
    feed(fake, FEED[:2])
    after = (NOW - timedelta(minutes=5)).isoformat()
    r = client.get("/activity/new", params={"after": after})
    assert r.status_code == 200 and r.headers["X-Activity-Feed"] == "1"
    assert r.headers["X-Activity-Newest"] == FEED[0]["created_at"]
    assert r.text.count('<li class="act-') == 2 and "<html" not in r.text
    assert sent_args(fake) == [{"p_limit": 30, "p_after": after}]


def test_the_live_check_answers_204_when_nothing_is_new_or_the_moment_is_not_one(client, fake):
    founder_sign_in(client, fake)
    feed(fake, [])
    r = client.get("/activity/new", params={"after": NOW.isoformat()})
    assert r.status_code == 204 and r.headers["X-Activity-Feed"] == "1"
    r = client.get("/activity/new", params={"after": "not a time"})
    assert r.status_code == 204 and len(sent_args(fake)) == 1


def test_the_live_check_sends_a_signed_out_person_to_sign_in_without_the_feed_header(client, fake):
    r = client.get("/activity/new", params={"after": NOW.isoformat()})
    assert r.status_code == 307 and "X-Activity-Feed" not in r.headers


# ---------------------------------------------------------------- what replaced posted updates
def test_a_profile_lists_its_own_entries_and_counts_its_active_weeks(client, fake):
    investor_sign_in(client, fake)
    investor_venture(fake)
    feed(fake, [row("published", 2), row("pitch_added", 1, at=NOW - timedelta(days=15))])
    body = client.get(f"/investor/ventures/{VENTURE['id']}").text
    assert '<h2 id="up-h" class="c-lbl">Activity</h2>' in body and "Progress updates" not in body
    assert "Kola Farms published its profile." in body and "View profile" not in body
    assert "Active in 2 of the last 13 weeks" in body
    assert 'aria-label="Activity in 2 of the last 13 weeks"' in body
    assert sent_args(fake) == [{"p_limit": 100, "p_venture": VENTURE["id"]}]
    assert fake.sent("GET", "/rest/v1/venture_updates") == []


def test_the_founders_home_points_to_the_feed_instead_of_an_update_form(client, fake):
    founder_sign_in(client, fake)
    feed(fake, [row("published", 2, at=NOW - timedelta(days=2))])
    body = client.get("/dashboard").text
    assert '<a href="/activity">Your latest step in the activity feed: 2 days ago.</a>' in body
    assert "/dashboard/updates" not in body
    assert sent_args(fake) == [{"p_limit": 1, "p_venture": VENTURE["id"]}]
