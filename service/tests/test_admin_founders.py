"""The founder register's pages for records that came from a list rather than the register form, and the audit log's
words for a load of the register and a dated video link.

The names below are made up. The real register is read from the database and kept out of the repository.
"""

from __future__ import annotations

import httpx

from app.routes.admin import describe_staff

from .test_investor_register import sign_in


def record(record_id: str, name: str, responses: int, joined_at: str) -> dict:
    return {"record_id": record_id, "full_name": name, "email": "", "phone": "", "country": "Ghana", "country_key": "Ghana",
            "university": "University of Ghana", "startup": "Pilot One", "sector": "Fintech", "stage": "", "amount": "",
            "study_year": "", "degree": "", "problem": "", "target_market": "", "unique_answer": "",
            "support": ["Business planning"], "joined_at": joined_at, "last_response_at": joined_at, "responses": responses,
            "video_status": "none"}


FROM_FORM = record("p901", "Ama Mensah", 2, "2026-01-13T21:16:55+00:00")
FROM_LIST = record("p917", "KOFI ADJEI", 0, "2026-06-01T00:00:00+00:00")


def founders_signed_in(client, fake, rows: list[dict]):
    sign_in(client, fake, role="admin")
    fake.on("POST", "/rest/v1/rpc/admin_shell", httpx.Response(200, json={
        "founders": len(rows), "investors": 54, "introductions": 24, "waitlist": 239, "sample": False}))
    fake.on("POST", "/rest/v1/rpc/admin_founder_records", httpx.Response(200, json=rows))
    fake.on("POST", "/rest/v1/rpc/admin_unfinished_signups", httpx.Response(200, json=[]))


def test_the_subtitle_says_how_many_founders_answered_the_form_once_a_list_is_loaded(client, fake):
    founders_signed_in(client, fake, [FROM_FORM, FROM_LIST])
    assert "2 founders on the register, 1 of them from 239 waitlist responses" in client.get("/admin/founders").text


def test_the_subtitle_keeps_the_boards_words_while_every_founder_answered_the_form(client, fake):
    founders_signed_in(client, fake, [FROM_FORM])
    assert "1 founder on the register, from 239 waitlist responses" in client.get("/admin/founders").text


def test_a_record_from_a_list_holds_no_responses_and_carries_no_sample_wording(client, fake):
    founders_signed_in(client, fake, [FROM_LIST])
    fake.on("POST", "/rest/v1/rpc/admin_founder_record", httpx.Response(200, json={
        **FROM_LIST, "sample": False, "responses": [], "introductions": [], "video": None}))
    body = client.get("/admin/founders/p917").text
    assert "Register number FND-917 · joined 1 Jun 2026, 00:00" in body
    assert "Register responses (0)" in body and "This record holds no responses." in body
    assert "sample" not in body.lower()


def test_a_load_of_the_register_is_described_by_its_counts():
    text, details, _ = describe_staff({"action": "register.import", "entity": "register_imports", "entity_id": None,
                                       "before": None, "after": {"founders": 220, "responses_received": 239,
                                                                 "responses_kept": 238, "introductions": 24,
                                                                 "investors_added": 1, "pitch_videos": 92}})
    assert text == "Loaded the founder register, the introductions and the pitch videos from the admin design"
    assert details == [("Founders", "220"), ("Form responses received", "239"), ("Form responses kept", "238"),
                       ("Introductions", "24"), ("Investor register entries added", "1"), ("Pitch videos", "92")]


def test_a_list_added_to_the_register_names_the_list():
    text, details, _ = describe_staff({"action": "register.import_list", "entity": "register_imports", "entity_id": None,
                                       "before": None, "after": {"founders": 60, "list": "The June list"}})
    assert text == "Added founders to the register from a list"
    assert details == [("Founders", "60"), ("List", "The June list")]


def test_a_video_link_shows_the_record_and_the_approval_date_it_was_given():
    _, details, _ = describe_staff({"action": "video.link", "entity": "pitch_video_files", "entity_id": "t01",
                                    "before": {"record_id": None, "decided_at": "2026-10-27T07:57:03+00:00"},
                                    "after": {"record_id": "p008", "decided_at": "2026-01-15T12:37:37+00:00"}})
    assert details == [("Changed", "Founder record: none to p008"),
                       ("Changed", "Approval date: 27 Oct 2026, 07:57 to 15 Jan 2026, 12:37"),
                       ("Record", "pitch_video_files t01")]


def intro(intro_id: str, record_id: str, email: str) -> dict:
    return {"intro_id": intro_id, "sample": False, "investor_no": "054", "investor_name": "Ada Okafor, Pilot Seed",
            "investor_registered_on": "2026-07-01", "record_id": record_id, "founder_name": "Kofi Adjei", "founder_email": email,
            "founder_phone": "", "startup": "Pilot One", "sector": "Fintech", "country_key": "Ghana",
            "founder_joined_at": "2026-06-01T00:00:00+00:00", "founder_sample": False, "made_on": "2026-10-23",
            "status": "pending", "note": "", "messages": 0, "accepted_on": None, "changed_at": None}


def test_a_founder_with_no_email_shows_the_register_number_alone_in_the_introductions(client, fake):
    founders_signed_in(client, fake, [])
    fake.on("POST", "/rest/v1/rpc/admin_register_introductions", httpx.Response(200, json=[
        intro("n901", "p917", ""), intro("n902", "p918", "kofi@example.test")]))
    body = client.get("/admin/introductions").text
    assert ">FND-917</span>" in body and "FND-917 ·" not in body
    assert "FND-918 · kofi@example.test" in body


def test_introductions_added_for_one_investor_name_the_investor_and_the_messages():
    text, details, _ = describe_staff({"action": "register.intros_add", "entity": "register_introductions", "entity_id": None,
                                       "before": None, "after": {"introductions": 41, "investor": "054", "messages_added": 240}})
    assert text == "Added introductions for one register investor"
    assert details == [("Introductions", "41"), ("Investor register number", "054"), ("Messages added", "240")]


def test_spreading_the_messages_names_the_introductions_that_hold_them():
    text, details, _ = describe_staff({"action": "register.messages", "entity": "register_introductions", "entity_id": None,
                                       "before": {"introductions": 4, "messages": 360},
                                       "after": {"introductions": 51, "messages": 360}})
    assert text == "Spread the messages over the accepted introductions"
    assert details == [("Changed", "Introductions with messages: 4 to 51")]
