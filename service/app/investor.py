"""The investor's details, read from the sign-up form and the profile form.

Ported from apps/web/lib/investor-profile.ts. The same rules apply at sign-up and when an
investor edits their details, and each matches a check on investor_profiles. Each field keeps
the first message its zod schema would have given.
"""

from __future__ import annotations

from .forms import Parsed, _optional, _text, _web
from .product import CHEQUE_SIZES, COUNTRIES, INVESTOR_TYPES, SECTORS, STAGES
from .validate import Errors, js_len, js_trim
from .waitlist import PRIVACY_VERSION

# An investor can be based in any country. Rows written before 21 October 2026 may hold "other".
BASED_IN = COUNTRIES

INVESTOR_TYPE_OPTIONS = (
    {"code": "individual", "name": "Individual investor", "hint": "You invest your own money, without a fund or an angel network."},
    {"code": "angel", "name": "Angel investor", "hint": "You invest your own money in early-stage companies, alone or with an angel network."},
    {"code": "fund", "name": "Fund investor", "hint": "You invest for a fund, a firm or another organisation."},
)

STAGE_CODES = tuple(s["code"] for s in STAGES)
COUNTRY_CODES = tuple(c["code"] for c in COUNTRIES)
WEBSITE = "Enter a full web address, for example savannahseed.com."


def _first(form: dict, key: str) -> str:
    v = form.get(key, "")
    if isinstance(v, list):
        return v[0] if v else ""
    return v if isinstance(v, str) else ""


def _all(form: dict, key: str) -> list[str]:
    v = form.get(key)
    if isinstance(v, list):
        return [str(x) for x in v]
    return [] if v is None else [str(v)]


def _choices(e: Errors, key: str, chosen: list[str], allowed, wrong: str, twice: str, at_least: str | None = None) -> bool:
    """A list of ticked boxes. Returns False when a value is not on the list, which stops the checks across fields.

    zod checks the list's length first, then each value, and checks for repeats only when every value is allowed.
    """
    if at_least and not chosen:
        e.add(key, at_least)
    if any(c not in allowed for c in chosen):
        e.add(key, wrong)
        return False
    if len(set(chosen)) != len(chosen):
        e.add(key, twice)
    return True


def _details(form: dict, e: Errors) -> tuple[dict, bool]:
    """Reads the fields both forms share. The flag is False when a field failed outright, as zod's aborted fields."""
    whole = True
    full_name = _text(e, "fullName", _first(form, "fullName"), 2, "Enter your full name.", 120, "Your name is too long.")
    based_in = _first(form, "basedIn")
    if based_in not in COUNTRY_CODES:
        e.add("basedIn", "Choose where you are based.")
        whole = False
    investor_type = _first(form, "investorType")
    if investor_type not in INVESTOR_TYPES:
        e.add("investorType", "Choose the one that describes you best.")
        whole = False
    firm = _optional(e, "firm", _first(form, "firm"), 120, "The firm name is too long.")
    website = _web(e, "website", _first(form, "website"), 200, "That address is too long.", WEBSITE)
    # Countries come from three menus, and a menu left on "No country" sends an empty value.
    sectors, stages = _all(form, "sectors"), _all(form, "stages")
    countries = [c for c in _all(form, "countries") if c]
    whole &= _choices(e, "sectors", sectors, SECTORS, "Choose sectors from the list.", "Choose each sector once.",
                      "Choose at least one sector.")
    whole &= _choices(e, "stages", stages, STAGE_CODES, "Choose stages from the list.", "Choose each stage once.")
    whole &= _choices(e, "countries", countries, COUNTRY_CODES, "Choose countries from the list.", "Choose each country once.")
    if len(countries) > 3 and "countries" not in e:
        e.add("countries", "Choose up to three countries.")
        whole = False
    cheque = _first(form, "chequeSize")
    if cheque not in CHEQUE_SIZES:
        e.add("chequeSize", "Choose a cheque size, or prefer not to say.")
        whole = False
    thesis = _optional(e, "thesis", _first(form, "thesis"), 600, "Keep this to 600 characters.")
    # A field that zod changes after its checks (an empty text becomes null, a bare domain gets https://) counts
    # as failed outright when it is too long, because zod does not run the change on a field that failed.
    for key, limit in (("firm", 120), ("website", 200), ("thesis", 600)):
        if js_len(js_trim(_first(form, key))) > limit:
            whole = False
    if form.get("confirmedStatement") != "on":
        e.add("confirmedStatement", "Confirm that this describes you.")
    return {
        "fullName": full_name, "basedIn": based_in, "investorType": investor_type, "firm": firm, "website": website,
        "sectors": sectors, "stages": stages, "countries": countries, "chequeSize": cheque, "thesis": thesis,
    }, whole


def _needs_firm(e: Errors, d: dict, whole: bool) -> None:
    # The rule across fields runs only when no field failed outright, as zod's refine on the object did.
    if whole and d["investorType"] == "fund" and d["firm"] is None:
        e.add("firm", "Enter the name of your fund or firm.")


def _rows(d: dict) -> dict:
    return {
        "full_name": d["fullName"],
        "country": None if d["basedIn"] == "other" else d["basedIn"],
        "investor": {
            "investor_type": d["investorType"], "firm": d["firm"], "website": d["website"], "based_in": d["basedIn"],
            "sectors": d["sectors"], "stages": d["stages"], "countries": d["countries"], "cheque_size": d["chequeSize"],
            "thesis": d["thesis"], "confirmed_statement": True,
        },
    }


def parse_investor_signup(form: dict, adult_confirmed: bool = False) -> Parsed:
    """Reads the investor sign-up form. `adult_confirmed` is true when sign-in already asked."""
    e = Errors()
    d, whole = _details(form, e)
    if not (adult_confirmed or form.get("confirmedAdult") == "on"):
        e.add("confirmedAdult", "You must be 18 or older to join.")
    if form.get("acceptedPrivacy") != "on":
        e.add("acceptedPrivacy", "Please confirm you have read the privacy policy.")
    _needs_firm(e, d, whole)
    if e:
        return Parsed(ok=False, errors=dict(e))
    r = _rows(d)
    return Parsed(ok=True, data={
        "profile": {"full_name": r["full_name"], "country": r["country"], "role": "investor", "status": "pending",
                    "confirmed_adult": True},
        "investor": r["investor"],
        "consents": [
            {"consent_type": "profile", "granted": True, "policy_version": PRIVACY_VERSION},
            {"consent_type": "notifications", "granted": form.get("notifications") == "on", "policy_version": PRIVACY_VERSION},
        ],
    })


def parse_investor_edit(form: dict) -> Parsed:
    """Reads the form an investor uses to change their details."""
    e = Errors()
    d, whole = _details(form, e)
    _needs_firm(e, d, whole)
    if e:
        return Parsed(ok=False, errors=dict(e))
    r = _rows(d)
    return Parsed(ok=True, data={"profile": {"full_name": r["full_name"], "country": r["country"]}, "investor": r["investor"]})
