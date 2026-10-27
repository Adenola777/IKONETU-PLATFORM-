"""The investor register: reading a pasted list, the wording, and the admin pages through HTTP.

The names below are made up. The real register is added through the admin page and is not kept in the repository.
"""

from __future__ import annotations

import json
import re
from datetime import date

import httpx

from app.register import added_text, number_ranges, parse_register, refusal_text, register_lines
from app.session import ACCESS_COOKIE

from .conftest import jwt

TODAY = date(2026, 10, 24)

# The shape of the register the owner gave on 24 October 2026: a title, a header row, tab-separated rows with a row
# number in front, and the monthly totals under the list.
AS_GIVEN = "\n".join([
    "Ikonetu investor register — July to September 2026",
    "S/N\tUnique ID\tInvestor name\tRegistration date",
    "1\t001\tAda Okafor\t2026-07-01",
    "2\t002\tBayo Lawal\t2026-07-02",
    "3\t003\tDr Chidi  Eze\t2026-08-01",
    "4\t004\tFemi (S.O.A) Ade\t2026-09-01",
    "Monthly progression",
    "July 2026",
    "IDs 001–002",
    "2",
    "August 2026",
    "IDs 003–003",
    "1",
])


# ---------------------------------------------------------------- reading the list
def test_the_register_as_given_gives_its_entries_and_leaves_out_headings_and_totals():
    p = parse_register(AS_GIVEN, TODAY)
    assert p.ok and p.errors == []
    assert [e["register_no"] for e in p.entries] == ["001", "002", "003", "004"]
    assert p.entries[2] == {"register_no": "003", "full_name": "Dr Chidi Eze", "registered_on": "2026-08-01"}
    assert p.entries[3]["full_name"] == "Femi (S.O.A) Ade"
    assert p.skipped == 9


def test_a_list_without_row_numbers_and_a_list_with_commas_or_spaces_are_read_the_same_way():
    for text in ("001\tAda Okafor\t2026-07-01", "001, Ada Okafor, 2026-07-01", '1,001,"Okafor, Ada",2026-07-01',
                 "001 Ada Okafor 2026-07-01", "1 001 Ada Okafor 2026-07-01"):
        p = parse_register(text, TODAY)
        assert p.ok, text
        assert p.entries[0]["register_no"] == "001" and p.entries[0]["registered_on"] == "2026-07-01", text
    assert parse_register('1,001,"Okafor, Ada",2026-07-01', TODAY).entries[0]["full_name"] == "Okafor, Ada"


def test_each_problem_is_reported_with_its_line():
    text = "\n".join([
        "001\tAda Okafor\t01/07/2026",
        "002\tBayo Lawal\t2026-02-30",
        "003\tChidi Eze\t2026-10-25",
        "04\tDayo Ade\t2026-07-04",
        "005\tE\t2026-07-05",
        "006\tFemi Obi\t2026-07-06",
        "006\tGbenga Obi\t2026-07-07",
        "x\t007\tHadiza Bello\t2026-07-08",
    ])
    p = parse_register(text, TODAY)
    assert not p.ok and p.entries[0]["register_no"] == "006"
    assert p.errors == [
        "Line 1: write the date as 2026-07-01.",
        "Line 2: 2026-02-30 is not a real date.",
        "Line 3: the registration date is after today.",
        "Line 4: the register number must be 3 to 6 digits, such as 001.",
        "Line 5: the name must be 2 to 120 characters.",
        "Line 7: register number 006 is also on line 6.",
        "Line 8: give the register number, the name and the date, in that order.",
    ]


def test_a_list_with_no_entry_is_refused():
    p = parse_register("S/N\tUnique ID\tInvestor name\tRegistration date\n\nJuly 2026", TODAY)
    assert not p.ok and p.entries == []
    assert p.errors[0].startswith("No entries were found.")


def test_more_than_a_thousand_entries_are_refused():
    text = "\n".join(f"{n:04d}\tPerson {n}\t2026-07-01" for n in range(1, 1002))
    p = parse_register(text, TODAY)
    assert not p.ok and p.errors == ["Add at most 1,000 entries at a time."]


# ---------------------------------------------------------------- wording
def test_register_numbers_are_written_as_runs():
    assert number_ranges(["001", "002", "003"]) == "001 to 003"
    assert number_ranges(["001", "002", "004", "006", "007"]) == "001 to 002, 004 and 006 to 007"
    assert number_ranges(["009", "010", "0011"]) == "009 to 010 and 0011"
    assert number_ranges(["001"]) == "001"
    assert number_ranges([]) == ""


def test_an_addition_reads_as_counts_and_numbers_in_the_audit_log():
    assert register_lines({"added": 53, "unchanged": 0, "numbers": [f"{n:03d}" for n in range(1, 54)]}) == [
        "Entries added: 53", "Register numbers: 001 to 053"]
    assert register_lines({"added": 1, "unchanged": 2, "numbers": ["054"]}) == [
        "Entries added: 1", "Already in the register and left as they were: 2", "Register numbers: 054"]


def test_the_confirmation_counts_what_was_added_kept_and_left_out():
    assert added_text(53, 0, 11) == ("53 entries added to the register. 11 lines without a date, such as headings or totals, "
                                     "were left out.")
    assert added_text(1, 1, 1) == ("One entry added to the register. One entry was already there with the same name and date, "
                                   "and it stayed as it was. One line without a date, such as headings or totals, was left out.")
    assert added_text(0, 53, 0) == "0 entries added to the register. 53 entries were already there with the same name and " \
                                   "date, and they stayed as they were."


def test_the_databases_refusals_are_explained():
    assert refusal_text("already in the register with a different name or date: 002, 003, 007") == (
        "Nothing was added. These register numbers are already in the register with a different name or date: 002 to 003 "
        "and 007. Correct those lines, or take them out, and add the list again.")
    assert refusal_text("entry 4: the registration date is after today") == (
        "Nothing was added. Entry 4 was refused: the registration date is after today.")
    assert refusal_text("only admins can add to the investor register") == "Only an admin can add to the investor register."
    assert refusal_text("TypeError") == "Nothing was added. Please try again."


# ---------------------------------------------------------------- the Investors page
ENTRIES = [
    {"register_no": "001", "full_name": "Ada Okafor", "registered_on": "2026-07-01", "added_at": "2026-10-24T09:00:00Z",
     "account_id": None, "account_name": None, "account_email": None, "linked_at": None, "introductions": 1, "total_count": 3},
    {"register_no": "002", "full_name": "Bayo Lawal", "registered_on": "2026-07-02", "added_at": "2026-10-24T09:00:00Z",
     "account_id": None, "account_name": None, "account_email": None, "linked_at": None, "introductions": 0, "total_count": 3},
    {"register_no": "003", "full_name": "Chidi Eze", "registered_on": "2026-09-01", "added_at": "2026-10-24T09:00:00Z",
     "account_id": None, "account_name": None, "account_email": None, "linked_at": None, "introductions": 0, "total_count": 3},
]
SHELL = {"founders": 216, "investors": 3, "introductions": 24, "waitlist": 239, "sample": False}
ORIGIN = {"origin": "http://testserver"}


def sign_in(client, fake, role: str = "admin", entries: list | None = None):
    client.cookies.set(ACCESS_COOKIE, jwt())
    fake.on("GET", "/auth/v1/user", httpx.Response(200, json={"id": "u-1", "user_metadata": {"confirmed_adult": True}}))

    def profiles(request: httpx.Request) -> httpx.Response:
        # The session reads the role; the Investors page reads the investor accounts; the audit log reads names.
        if request.url.params.get("role") == "eq.investor":
            return httpx.Response(200, json=[])
        if "user_id" in request.url.params.get("select", ""):
            return httpx.Response(200, json=[{"user_id": "u-1", "full_name": "Ada Admin"}])
        return httpx.Response(200, json=[{"role": role, "status": "active", "full_name": "Ada Admin"}])

    fake.on("GET", "/rest/v1/profiles", profiles)
    fake.on("POST", "/rest/v1/rpc/admin_shell", httpx.Response(200, json=SHELL))
    fake.on("POST", "/rest/v1/rpc/admin_register", httpx.Response(200, json=ENTRIES if entries is None else entries))


def test_the_investors_page_shows_each_month_with_its_running_total_and_the_entries(client, fake):
    sign_in(client, fake)
    r = client.get("/admin/investors")
    assert r.status_code == 200
    body = r.text
    assert "3 on the register · 1 introduced to founders" in body
    assert re.search(r'<span class="a-scard-label">July 2026</span>\n<span class="a-scard-count">2</span>\n'
                     r'<span class="a-scard-range">Running total 2</span>', body)
    assert re.search(r'<span class="a-scard-label">September 2026</span>\n<span class="a-scard-count">1</span>\n'
                     r'<span class="a-scard-range">Running total 3</span>', body)
    assert '<td class="a-num" style="font-weight:600">001</td>\n<td>Ada Okafor</td>\n<td>1 Jul 2026</td>' in body
    assert '<a href="/admin/investors" class="adm-link" aria-current="page">' in body
    assert json.loads(fake.sent("POST", "/rest/v1/rpc/admin_register")[0].content) == {"p_limit": 1000, "p_offset": 0}


def test_a_search_a_month_and_the_account_filter_narrow_the_list(client, fake):
    sign_in(client, fake)
    assert "Bayo Lawal" not in client.get("/admin/investors?q=okafor").text
    body = client.get("/admin/investors?month=2026-09").text
    assert "Chidi Eze" in body and "Ada Okafor" not in body
    assert "No register entry is linked to an account yet." in client.get("/admin/investors?account=linked").text


def test_an_empty_register_says_so(client, fake):
    sign_in(client, fake, entries=[])
    body = client.get("/admin/investors").text
    assert "The register is empty. Add entries to start it." in body
    assert "No register entry matches these filters." in body


def test_a_reviewer_cannot_open_the_investors_page(client, fake):
    sign_in(client, fake, role="reviewer")
    for path in ("/admin/investors", "/admin/register", "/admin/register/add"):
        r = client.get(path)
        assert r.status_code == 307 and r.headers["location"] == "/admin", path
    r = client.post("/admin/investors/register", data={"entries": "001\tAda Okafor\t2026-07-01"}, headers=ORIGIN)
    assert r.status_code == 303 and r.headers["location"] == "/admin"
    assert not fake.sent("POST", "/rest/v1/rpc/admin_register_add")


def test_the_old_register_addresses_lead_to_the_investors_page(client, fake):
    sign_in(client, fake)
    assert client.get("/admin/register").headers["location"] == "/admin/investors"
    assert client.get("/admin/register/add").headers["location"] == "/admin/investors?add=1"
    assert '<textarea id="add-text" name="entries"' in client.get("/admin/investors?add=1").text


def test_a_pasted_list_is_sent_as_entries_and_the_admin_sees_the_counts(client, fake):
    sign_in(client, fake)
    fake.on("POST", "/rest/v1/rpc/admin_register_add", httpx.Response(200, json=[{"added": 4, "unchanged": 0}]))
    r = client.post("/admin/investors/register", data={"entries": AS_GIVEN}, headers=ORIGIN)
    assert r.status_code == 303 and r.headers["location"] == "/admin/investors"
    sent = json.loads(fake.sent("POST", "/rest/v1/rpc/admin_register_add")[0].content)
    assert [e["register_no"] for e in sent["p_entries"]] == ["001", "002", "003", "004"]
    assert sent["p_entries"][0] == {"register_no": "001", "full_name": "Ada Okafor", "registered_on": "2026-07-01"}
    body = client.get("/admin/investors").text
    assert "4 entries added to the register. 9 lines without a date, such as headings or totals, were left out." in body


def test_a_list_with_problems_is_shown_again_with_each_line_and_nothing_is_sent(client, fake):
    sign_in(client, fake)
    text = "001\tAda Okafor\t01/07/2026\n002\tBayo Lawal\t2026-07-02"
    r = client.post("/admin/investors/register", data={"entries": text}, headers=ORIGIN)
    assert r.status_code == 422
    assert "Nothing was added. Please correct the list." in r.text
    assert "<li>Line 1: write the date as 2026-07-01.</li>" in r.text
    assert "002\tBayo Lawal\t2026-07-02</textarea>" in r.text
    assert not fake.sent("POST", "/rest/v1/rpc/admin_register_add")


def test_a_number_already_there_with_another_name_is_explained(client, fake):
    sign_in(client, fake)
    fake.on("POST", "/rest/v1/rpc/admin_register_add", httpx.Response(400, json={
        "code": "P0001", "message": "already in the register with a different name or date: 002", "details": None, "hint": None}))
    r = client.post("/admin/investors/register", data={"entries": "002\tBayo Lawal Jr\t2026-07-02"}, headers=ORIGIN)
    assert r.status_code == 422
    assert ("Nothing was added. These register numbers are already in the register with a different name or date: 002."
            in r.text)


def test_an_entry_links_to_an_investor_account_by_email(client, fake):
    sign_in(client, fake)
    fake.on("POST", "/rest/v1/rpc/admin_register_link", httpx.Response(204))
    r = client.post("/admin/investors/link", data={"no": "001", "email": "ada@fund.test"}, headers=ORIGIN)
    assert r.status_code == 303 and r.headers["location"] == "/admin/investors"
    assert json.loads(fake.sent("POST", "/rest/v1/rpc/admin_register_link")[0].content) == {"p_no": "001", "p_email": "ada@fund.test"}
    assert "Linked register entry 001 to the account of ada@fund.test." in client.get("/admin/investors").text


def test_an_email_no_investor_account_uses_is_explained(client, fake):
    sign_in(client, fake)
    fake.on("POST", "/rest/v1/rpc/admin_register_link", httpx.Response(400, json={
        "code": "P0002", "message": "no investor account uses this email address", "details": None, "hint": None}))
    r = client.post("/admin/investors/link", data={"no": "001", "email": "nobody@fund.test"}, headers=ORIGIN)
    assert r.status_code == 422 and "No investor account uses nobody@fund.test." in r.text
    r = client.post("/admin/investors/link", data={"no": "001", "email": "not an email"}, headers=ORIGIN)
    assert r.status_code == 422 and "Enter the email address of the investor&#39;s account." in r.text


def test_the_audit_log_shows_an_addition_with_its_numbers(client, fake):
    sign_in(client, fake)
    fake.on("GET", "/rest/v1/audit_log", httpx.Response(200, json=[{
        "id": 7, "actor_id": "u-1", "action": "register.add", "entity": "investor_register", "entity_id": None,
        "before": None, "after": {"added": 53, "unchanged": 0, "numbers": [f"{n:03d}" for n in range(1, 54)]},
        "created_at": "2026-10-24T09:00:00Z",
    }]))
    body = client.get("/admin/audit?group=register").text
    assert "Ada Admin added entries to the investor register." in body
    assert "<li>Entries added: 53</li>" in body and "<li>Register numbers: 001 to 053</li>" in body
    assert '<option value="register" selected>Investor register</option>' in body
