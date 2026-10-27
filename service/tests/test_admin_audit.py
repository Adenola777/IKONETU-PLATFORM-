"""The Audit log page: the register's entries with the staff actions, its cards, filters, pages and CSV.

The names below are made up. The real register's history is read from the database and kept out of the repository.
"""

from __future__ import annotations

import csv
import io

import httpx

from .test_investor_register import sign_in

HISTORY = {
    "responses": [
        {"response_id": "f902", "record_id": "p901", "responded_at": "2026-02-01T08:00:00+00:00", "first": False,
         "full_name": "Ama Mensah", "email": "ama@example.test", "phone": "+233000", "country": "Ghana",
         "university": "University of Ghana", "startup": "Pilot Again", "sector": "Fintech", "response_count": 2},
        {"response_id": "f901", "record_id": "p901", "responded_at": "2026-01-13T21:16:55+00:00", "first": True,
         "full_name": "Ama Mensah", "email": "ama@example.test", "phone": "+233000", "country": "Ghana",
         "university": "University of Ghana", "startup": "Pilot One", "sector": "Fintech", "response_count": 2},
    ],
    "investors": [{"register_no": "001", "full_name": "Ada Okafor", "registered_on": "2026-07-01"}],
}
LOG = [{"id": 9, "actor_id": "u-1", "action": "settings.mode", "entity": "platform_settings", "entity_id": None,
        "before": {"mode": "live", "maintenance_message": "Back soon."},
        "after": {"mode": "maintenance", "maintenance_message": "Back soon."}, "created_at": "2026-10-26T10:00:00Z"}]


def audit_signed_in(client, fake, role: str = "admin"):
    sign_in(client, fake, role=role)
    fake.on("POST", "/rest/v1/rpc/admin_register_history", httpx.Response(200, json=HISTORY))
    fake.on("GET", "/rest/v1/audit_log", httpx.Response(200, json=LOG))


def test_the_audit_log_mixes_the_register_with_staff_actions_newest_first(client, fake):
    audit_signed_in(client, fake)
    body = client.get("/admin/audit").text
    assert "4 entries from 13 Jan 2026 to 26 Oct 2026" in body
    order = [body.index(t) for t in ("Changed the platform mode", "Added to the investor register as number 001",
                                     "Sent the register form again with Pilot Again", "Joined the register with Pilot One")]
    assert order == sorted(order)
    assert "<dt>Changed</dt><dd>Mode: Live to Maintenance</dd>" in body
    assert "<dt>Register responses from this founder</dt><dd>2</dd>" in body
    assert '<a href="/admin/founders/p901" class="a-link">Open the record</a>' in body


def test_each_card_counts_its_kind_and_filters_the_list(client, fake):
    audit_signed_in(client, fake)
    body = client.get("/admin/audit?kind=investor").text
    assert '<a href="/admin/audit" class="a-scard" aria-current="true">' in body
    assert "<span class=\"a-scard-range\">1 Jul 2026 to 1 Jul 2026</span>" in body
    assert "Added to the investor register as number 001" in body and "Pilot One" not in body.split('id="log-h"')[1]
    assert "1 of 4 entries" in body


def test_words_dates_and_the_order_narrow_and_turn_the_list(client, fake):
    audit_signed_in(client, fake)
    body = client.get("/admin/audit?q=ama%40example&from=2026-01-01&to=2026-01-31").text
    assert "Joined the register with Pilot One" in body and "Pilot Again" not in body.split('id="log-h"')[1]
    body = client.get("/admin/audit?order=old").text
    assert body.index("Joined the register with Pilot One") < body.index("Changed the platform mode")
    assert "No entry matches these filters." in client.get("/admin/audit?q=nobody").text


def test_a_bad_date_or_kind_is_left_out_rather_than_refused(client, fake):
    audit_signed_in(client, fake)
    body = client.get("/admin/audit?kind=everything&from=yesterday").text
    assert "4 entries</span>" in body


def test_the_csv_has_the_boards_columns_and_the_filtered_entries(client, fake):
    audit_signed_in(client, fake)
    r = client.get("/admin/audit.csv?kind=waitlist")
    assert r.headers["content-disposition"] == 'attachment; filename="ikonetu-audit-log.csv"'
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert rows == [["When", "Who", "Action", "What"],
                    ["2026-01-13 21:16:55", "Ama Mensah", "Joined the register", "Joined the register with Pilot One"]]


def test_a_reviewer_cannot_open_the_audit_log(client, fake):
    audit_signed_in(client, fake, role="reviewer")
    for path in ("/admin/audit", "/admin/audit.csv"):
        r = client.get(path)
        assert r.status_code == 307 and r.headers["location"] == "/admin", path
