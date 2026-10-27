"""The staff pages' rules and wording. Ported from apps/web/lib/admin.test.ts, with the JavaScript formats
the staff pages show and the chart the overview draws."""

from app.jsfmt import month_long, month_short, parse_int, search_params, to_fixed, when_text
from app.routes.staff import evidence_state
from app.staff import (
    action_text,
    change_lines,
    entity_href,
    entry_reason,
    parse_hold,
    parse_lift,
    parse_role_change,
    parse_status_change,
    refusal_text,
    roles_for,
)
from app.supabase import js_json

ID = "9b000000-0000-0000-0000-00000000000f"


def test_offers_founder_only_with_a_venture_and_investor_only_with_an_investor_profile():
    assert roles_for("founder", True, False) == ["reviewer", "admin"]
    assert roles_for("reviewer", True, False) == ["founder", "admin"]
    assert roles_for("investor", False, True) == ["reviewer", "admin"]
    assert roles_for("admin", False, False) == ["reviewer"]


class TestHolds:
    def test_needs_a_reason_of_five_to_280_characters_because_the_founder_reads_it(self):
        assert not parse_hold({"id": ID, "reason": "no"}).ok
        assert not parse_hold({"id": ID, "reason": "x" * 281}).ok
        r = parse_hold({"id": ID, "reason": "  The revenue figure does not match.  "})
        assert r.ok and r.data["reason"] == "The revenue figure does not match."

    def test_refuses_an_id_that_is_not_a_record_id(self):
        assert not parse_hold({"id": "1 or 1=1", "reason": "A real reason"}).ok

    def test_lets_the_note_on_lifting_a_hold_be_empty(self):
        r = parse_lift({"id": ID, "note": ""})
        assert r.ok and r.data["note"] is None


class TestRolesAndStatus:
    def test_accepts_the_four_roles_an_admin_can_give_and_nothing_else(self):
        assert parse_role_change({"id": ID, "role": "reviewer", "reason": ""}).ok
        assert not parse_role_change({"id": ID, "role": "mentor", "reason": ""}).ok

    def test_needs_a_reason_to_suspend_and_none_to_make_an_account_active_again(self):
        assert not parse_status_change({"id": ID, "status": "suspended", "reason": ""}).ok
        assert parse_status_change({"id": ID, "status": "suspended", "reason": "Reported for spam."}).ok
        assert parse_status_change({"id": ID, "status": "active", "reason": ""}).ok
        assert not parse_status_change({"id": ID, "status": "pending", "reason": ""}).ok


class TestAuditLog:
    def test_names_each_action_and_links_each_record_to_its_page(self):
        assert action_text("venture.hide") == "hid a profile from investors"
        assert action_text("something.new") == "something.new"
        assert entity_href("profiles", ID) == f"/admin/people/{ID}"
        assert entity_href("ventures", ID) == f"/admin/founders/{ID}"
        assert entity_href("evidence", ID) == f"/admin/evidence/{ID}"
        assert entity_href("profiles", "not-an-id") is None

    def test_describes_what_changed_in_words_and_keeps_the_reason_apart(self):
        assert change_lines({"status": "pending"}, {"status": "active"}) == ["Status: Waiting for approval to Active"]
        assert change_lines({"role": "founder", "status": "active"},
                            {"role": "reviewer", "status": "active", "reason": "Joins", "profiles_hidden": 1}) == ["Role: Founder to Reviewer"]
        assert change_lines({"published_at": "2026-10-17T10:00:00Z"}, {"published_at": None, "reason": "Misleading"}) == \
            ["Published to investors: yes to no"]
        assert change_lines({"hidden_at": "2026-10-17T10:00:00Z", "reason": "Misleading"}, {"hidden_at": None, "note": "Fixed"}) == \
            ["Hold: on to off"]
        assert change_lines({"status": "submitted", "lane": None}, {"status": "needs_more", "lane": None}) == \
            ["Status: Waiting for review to More asked for"]
        assert change_lines({"status": "submitted", "lane": None}, {"status": "approved", "lane": "human", "public_note": "Compared"}) == \
            ["Status: Waiting for review to Approved", "Checked by: none to an IkonetU reviewer", "Note for investors: none to Compared"]
        assert entry_reason({"reason": "Misleading"}) == "Misleading"
        assert entry_reason({"note": "Corrected"}) == "Corrected"
        assert entry_reason({"status": "active"}) is None

    def test_turns_the_databases_refusals_into_plain_sentences(self):
        assert "your own role" in refusal_text("nobody can change their own role")
        assert "no venture" in refusal_text("this person has no venture, so they cannot be a founder")
        assert refusal_text("connection reset") == "The change was not saved. Please try again."

    def test_names_the_state_of_each_piece_of_evidence(self):
        assert evidence_state({"status": "submitted"}) == "Waiting for review"
        assert evidence_state({"status": "approved", "lane": "government"}) == "Third-party evidence: a government record"
        assert evidence_state({"status": "approved", "lane": "ai"}) == "Approved"
        assert evidence_state({"status": "odd"}) == "odd"


class TestJavaScriptFormats:
    def test_writes_dates_and_months_as_intl_did_in_node_22(self):
        assert month_short("2026-09-01T00:00:00Z") == "Sept"
        assert month_long("2026-10-01T00:00:00Z") == "October 2026"
        assert when_text("2026-07-04T09:07:00.5+01:00") == "4 July 2026 at 08:07"

    def test_rounds_a_half_up_as_to_fixed_does(self):
        assert to_fixed(262144 / 1024 / 1024, 1) == "0.3"
        assert to_fixed(1 / 1024 / 1024, 1) == "0.0"
        assert to_fixed(10.0, 1) == "10.0"

    def test_reads_a_page_number_as_parse_int_does(self):
        assert [parse_int(t) for t in ("2abc", " 3", "-1", "0x10", "", "x")] == [2, 3, -1, 0, None, None]

    def test_writes_a_query_string_as_url_search_params_does(self):
        assert search_params([("q", "a b~c*d"), ("state", "all")]) == "q=a+b%7Ec*d&state=all"

    def test_writes_json_as_json_stringify_does(self):
        assert js_json({"revenue": 18000.0, "duration": 58.2, "bad": float("inf"), "text": "é"}) == \
            '{"revenue":18000,"duration":58.2,"bad":null,"text":"é"}'
