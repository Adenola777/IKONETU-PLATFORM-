"""The investor's form and the discovery filters.

Ported from the investor part of apps/web/lib/forms.test.ts and the discovery part of
apps/web/lib/product.test.ts, with the report link of a conversation.
"""

from urllib.parse import parse_qs, urlsplit

from app.discovery import FILTER_GROUPS, PAGE_SIZE, filter_count, match_text, parse_filters, query_string, rpc_args
from app.investor import parse_investor_edit, parse_investor_signup
from app.routes.introductions import report_link


class Params(dict):
    """A query string as a multi-dict, as Starlette's QueryParams gives it."""

    def getlist(self, key):
        v = self.get(key, [])
        return v if isinstance(v, list) else [v]


BASE = {
    "fullName": "Ife Investor", "basedIn": "other", "investorType": "angel", "sectors": ["Fintech", "Health"],
    "stages": "revenue", "countries": "NG", "chequeSize": "Prefer not to say", "confirmedStatement": "on",
    "acceptedPrivacy": "on",
}


class TestInvestorSignUp:
    def test_makes_a_pending_investor_profile_with_the_consents_recorded(self):
        r = parse_investor_signup(BASE, True)
        assert r.ok
        assert r.data["profile"] == {"full_name": "Ife Investor", "country": None, "role": "investor", "status": "pending",
                                     "confirmed_adult": True}
        assert r.data["investor"]["sectors"] == ["Fintech", "Health"]
        assert r.data["investor"]["based_in"] == "other"
        assert [(c["consent_type"], c["granted"]) for c in r.data["consents"]] == [("profile", True), ("notifications", False)]

    def test_asks_a_fund_investor_for_the_funds_name(self):
        r = parse_investor_signup({**BASE, "investorType": "fund"}, True)
        assert r.errors["firm"] == "Enter the name of your fund or firm."

    def test_needs_a_sector_the_statement_and_the_adult_confirmation(self):
        r = parse_investor_signup({k: v for k, v in BASE.items() if k not in ("sectors", "confirmedStatement")}, False)
        assert r.errors["sectors"] == "Choose at least one sector."
        assert r.errors["confirmedStatement"] == "Confirm that this describes you."
        assert r.errors["confirmedAdult"] == "You must be 18 or older to join."

    def test_refuses_a_sector_that_is_not_on_the_list(self):
        assert not parse_investor_edit({**BASE, "sectors": ["Fintech", "Health", "Crypto"]}).ok

    def test_refuses_a_sector_chosen_twice(self):
        assert parse_investor_edit({**BASE, "sectors": ["Fintech", "Fintech"]}).errors == {"sectors": "Choose each sector once."}

    def test_an_edit_changes_the_name_and_country_only(self):
        r = parse_investor_edit({**BASE, "basedIn": "KE"})
        assert r.data["profile"] == {"full_name": "Ife Investor", "country": "KE"}


class TestDiscoveryFilters:
    def test_keeps_known_values_and_drops_the_rest(self):
        f = parse_filters(Params({"sector": ["Fintech", "Crypto"], "stage": "revenue,idea", "country": "NG",
                                  "evidence": "registry_record", "activity": "30", "page": "2"}))
        assert f["sector"] == ["Fintech"]
        assert f["stage"] == ["revenue", "idea"]
        assert f["country"] == ["NG"]
        assert f["evidence"] == ["registry_record"]
        assert f["activity"] == "30"
        assert f["page"] == 2
        assert filter_count(f) == 6

    def test_ignores_a_bad_activity_or_page(self):
        f = parse_filters(Params({"activity": "7", "page": "-3"}))
        assert f["activity"] == ""
        assert f["page"] == 1

    def test_turns_empty_groups_into_no_filter_for_the_database(self):
        assert rpc_args(parse_filters(Params({"sector": "Health", "page": "3"}))) == {
            "p_sectors": ["Health"], "p_stages": None, "p_countries": None, "p_evidence": None, "p_active_days": None,
            "p_limit": PAGE_SIZE, "p_offset": 2 * PAGE_SIZE,
        }

    def test_writes_the_same_filters_back_as_a_query_string(self):
        f = parse_filters(Params({"sector": ["Fintech", "Health"], "activity": "90"}))
        assert query_string(f) == "?sector=Fintech&sector=Health&activity=90"
        assert query_string(f, 2) == "?sector=Fintech&sector=Health&activity=90&page=2"
        assert query_string(parse_filters(Params({}))) == ""

    def test_offers_the_groups_the_for_investors_page_describes(self):
        assert [g["label"] for g in FILTER_GROUPS] == ["Sector", "Stage", "Geography", "Evidence"]

    def test_words_the_count(self):
        assert match_text(1, True) == "1 founder matches these filters. Sorted by company name."
        assert match_text(3, False) == "3 founders are on IkonetU. Sorted by company name."


def test_the_report_link_names_the_conversation_with_spaces_written_as_percent_20():
    link = report_link("6f1c1a3e-1111-4222-8333-944455556666")
    assert link.startswith("mailto:info@ikonetu.com?") and "+" not in link
    query = parse_qs(urlsplit(link).query)
    assert query["subject"] == ["Report about conversation 6f1c1a3e-1111-4222-8333-944455556666"]
    assert query["body"] == ["Conversation reference: 6f1c1a3e-1111-4222-8333-944455556666\n\nWhat happened:\n"]
