"""The investor's form and the discovery filters.

Ported from the investor part of apps/web/lib/forms.test.ts and the discovery part of
apps/web/lib/product.test.ts, with the report a person sends about a conversation.
"""

from app.discovery import FILTER_GROUPS, PAGE_SIZE, filter_count, match_text, parse_filters, query_string, rpc_args
from app.forms import parse_report
from app.investor import parse_investor_edit, parse_investor_signup


class Params(dict):
    """A query string as a multi-dict, as Starlette's QueryParams gives it."""

    def getlist(self, key):
        v = self.get(key, [])
        return v if isinstance(v, list) else [v]


BASE = {
    "fullName": "Ife Investor", "basedIn": "GB", "investorType": "angel", "sectors": ["Fintech", "Health"],
    "stages": "revenue", "countries": "NG", "chequeSize": "Prefer not to say", "confirmedStatement": "on",
    "acceptedPrivacy": "on",
}


class TestInvestorSignUp:
    def test_makes_a_pending_investor_profile_with_the_consents_recorded(self):
        r = parse_investor_signup(BASE, True)
        assert r.ok
        assert r.data["profile"] == {"full_name": "Ife Investor", "country": "GB", "role": "investor", "status": "pending",
                                     "confirmed_adult": True}
        assert r.data["investor"]["sectors"] == ["Fintech", "Health"]
        assert r.data["investor"]["based_in"] == "GB"
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


def test_a_report_says_what_happened_in_10_to_2000_characters():
    assert parse_report("  Too short ").errors == {"reason": "Say what happened, in at least 10 characters."}
    assert parse_report("x" * 2001).errors == {"reason": "Keep the report to 2,000 characters."}
    assert parse_report("  He asked for my bank details.  ").data == {"reason": "He asked for my bank details."}


class TestInvestorCountries:
    """Investors can be based in, and invest in, any country since 21 October 2026."""

    def test_takes_an_investor_based_in_any_country(self):
        for code in ("GB", "US", "NG", "AE"):
            assert parse_investor_signup({**BASE, "basedIn": code}, True).ok, code

    def test_refuses_a_base_outside_iso_3166(self):
        assert "basedIn" in parse_investor_signup({**BASE, "basedIn": "other"}, True).errors

    def test_ignores_a_country_menu_left_on_no_country(self):
        r = parse_investor_signup({**BASE, "countries": ["GB", "", "KE"]}, True)
        assert r.ok and r.data["investor"]["countries"] == ["GB", "KE"]

    def test_refuses_more_than_three_countries(self):
        r = parse_investor_signup({**BASE, "countries": ["GB", "KE", "NG", "US"]}, True)
        assert r.errors["countries"] == "Choose up to three countries."

    def test_discovery_filters_by_any_country(self):
        f = parse_filters(Params({"country": "GB"}))
        assert f["country"] == ["GB"] and rpc_args(f)["p_countries"] == ["GB"]
        assert parse_filters(Params({"country": "XX"}))["country"] == []
