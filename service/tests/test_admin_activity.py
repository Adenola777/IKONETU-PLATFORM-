"""The Activity page, reached from the sidebar, and the dashboard without the activity it listed until 27 October 2026.

The names below are made up. The real register's history is read from the database and kept out of the repository.
"""

from __future__ import annotations

import httpx

from .test_admin_audit import HISTORY, LOG
from .test_investor_register import sign_in

DASHBOARD = {
    "waitlist": 239, "founders": 2, "founders_with_support": 1, "investors": 1, "videos": 0, "videos_pending": 0,
    "intros": 0, "intros_register": 0, "intros_pending": 0, "intros_accepted": 0, "messages": 0, "conversations": 0,
    "admins": 1, "reviewers": 0, "evidence_waiting": 0, "reports_open": 0, "investors_awaiting": 0, "unfinished": 0,
    "months": [], "countries": [["Ghana", 2]], "support": [], "sample": False,
}


def activity_signed_in(client, fake, role: str = "admin"):
    sign_in(client, fake, role=role)
    fake.on("POST", "/rest/v1/rpc/admin_register_history", httpx.Response(200, json=HISTORY))
    fake.on("GET", "/rest/v1/audit_log", httpx.Response(200, json=LOG))
    fake.on("POST", "/rest/v1/rpc/admin_dashboard", httpx.Response(200, json=DASHBOARD))


def test_the_sidebar_links_to_activity_beneath_the_dashboard(client, fake):
    activity_signed_in(client, fake)
    body = client.get("/admin").text
    dashboard, activity = body.index('href="/admin"'), body.index('href="/admin/activity"')
    assert dashboard < activity < body.index('href="/admin/founders"')
    assert '<span class="adm-name">Activity</span>' in body


def test_the_dashboard_no_longer_lists_the_activity(client, fake):
    activity_signed_in(client, fake)
    body = client.get("/admin").text
    assert "Recent activity" not in body and "a-recent" not in body
    assert not fake.sent("POST", "/rest/v1/rpc/admin_register_history")
    assert not fake.sent("GET", "/rest/v1/audit_log")


def test_the_activity_page_lists_every_entry_newest_first(client, fake):
    activity_signed_in(client, fake)
    body = client.get("/admin/activity").text
    assert '<h1 class="a-h1">Activity</h1>' in body and "4 entries, newest first" in body
    assert 'aria-current="page"' in body.split('href="/admin/activity"')[1][:80]
    staff, response = body.index("Changed the platform mode"), body.index("Pilot Again")
    assert staff < response
    assert '<a href="/admin/audit" class="a-btn a-btn-n">Open the audit log</a>' in body


def test_the_activity_comes_in_pages_of_25(client, fake):
    sign_in(client, fake)
    log = [{**LOG[0], "id": n, "created_at": f"2026-10-{1 + n % 27:02d}T10:00:00Z"} for n in range(30)]
    fake.on("POST", "/rest/v1/rpc/admin_register_history", httpx.Response(200, json={"responses": [], "investors": []}))
    fake.on("GET", "/rest/v1/audit_log", httpx.Response(200, json=log))
    first, second = client.get("/admin/activity").text, client.get("/admin/activity?page=2").text
    assert first.count('class="a-recent"') == 25 and second.count('class="a-recent"') == 5
    assert 'href="/admin/activity?page=2">Next</a>' in first


def test_a_reviewer_cannot_open_the_activity(client, fake):
    activity_signed_in(client, fake, role="reviewer")
    r = client.get("/admin/activity")
    assert r.status_code == 307 and r.headers["location"] == "/admin"
