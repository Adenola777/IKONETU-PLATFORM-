"""The waitlist form behind POST /api/v1/waitlist, ported from apps/web/lib/waitlist.ts."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Literal

from .validate import JS_SPACE, Errors, is_email, js_len, js_trim

COUNTRIES = (
    {"code": "NG", "name": "Nigeria", "dial": "234"},
    {"code": "GH", "name": "Ghana", "dial": "233"},
    {"code": "KE", "name": "Kenya", "dial": "254"},
)
COUNTRY_CODES = tuple(c["code"] for c in COUNTRIES)
ROLES = ("founder", "investor", "mentor")

# The version of the privacy policy a person accepts: the one dated 21 October 2026, which replaced that of 15 October 2026.
PRIVACY_VERSION = "2026-10-21"

FIELDS = ("fullName", "contact", "country", "role", "confirmedAdult", "acceptedPrivacy", "website")


@dataclass
class Contact:
    value: str
    type: Literal["email", "phone"]


def normalise_contact(raw: str, country: str) -> Contact | None:
    """Turns what a person typed into a stored contact.

    Emails are lower-cased. Phone numbers become international digits with a
    leading plus, and a local number that starts with 0 takes the dialling
    code of the chosen country.
    """
    text = js_trim(raw)
    if "@" in text:
        email = text.lower()
        return Contact(email, "email") if is_email(email) and js_len(email) <= 160 else None
    if not re.fullmatch("[+0-9" + re.escape(JS_SPACE) + "().-]+", text):
        return None
    digits = re.sub(r"[^0-9]", "", text)
    if text.startswith("+"):
        pass
    elif digits.startswith("00"):
        digits = digits[2:]
    elif digits.startswith("0"):
        dial = next(c["dial"] for c in COUNTRIES if c["code"] == country)
        digits = dial + digits[1:]
    if len(digits) < 10 or len(digits) > 15:
        return None
    return Contact(f"+{digits}", "phone")


def parse_waitlist(body: object) -> dict:
    """Answers {"ok": True, "row": ...}, {"ok": False, "bot": True} or {"ok": False, "bot": False, "errors": ...}."""
    if isinstance(body, dict) and body.get("website"):
        return {"ok": False, "bot": True}
    errors = Errors()
    if not isinstance(body, dict):
        errors.add("form", "Expected object, received " + type(body).__name__)
        return {"ok": False, "bot": False, "errors": dict(errors)}

    def text(key: str, min_len: int, min_msg: str, max_len: int, max_msg: str) -> str | None:
        v = body.get(key)
        if not isinstance(v, str):
            errors.add(key, "Required" if v is None else f"Expected string, received {type(v).__name__}")
            return None
        t = js_trim(v)
        if js_len(t) < min_len:
            errors.add(key, min_msg)
        if js_len(t) > max_len:
            errors.add(key, max_msg)
        return t

    full_name = text("fullName", 2, "Enter your full name.", 120, "Your name is too long.")
    contact = text("contact", 5, "Enter a phone number or email.", 160, "String must contain at most 160 character(s)")
    country = body.get("country")
    if country not in ("NG", "GH", "KE"):
        errors.add("country", "Choose your country.")
    role = body.get("role")
    if role not in ROLES:
        errors.add("role", "Choose how you are joining.")
    for key, message in (("confirmedAdult", "You must be 18 or older to join."),
                         ("acceptedPrivacy", "Please confirm you have read the privacy policy.")):
        v = body.get(key)
        if not isinstance(v, bool):
            errors.add(key, "Required" if v is None else f"Expected boolean, received {type(v).__name__}")
        elif not v:
            errors.add(key, message)
    website = body.get("website", "")
    if website is not None and not isinstance(website, str):
        errors.add("website", f"Expected string, received {type(website).__name__}")
    # The schema is strict, so a caller cannot set staff-only columns such as source.
    unknown = [k for k in body if k not in FIELDS]
    if unknown:
        errors.add("form", "Unrecognized key(s) in object: " + ", ".join(f"'{k}'" for k in unknown))
    if errors:
        return {"ok": False, "bot": False, "errors": dict(errors)}

    normal = normalise_contact(contact or "", country)  # type: ignore[arg-type]
    if normal is None:
        return {"ok": False, "bot": False, "errors": {"contact": "Enter a valid phone number or email."}}
    return {
        "ok": True,
        "row": {
            "full_name": full_name,
            "contact": normal.value,
            "contact_type": normal.type,
            "country": country,
            "role": role,
            "confirmed_adult": True,
            "privacy_version": PRIVACY_VERSION,
            "source": "landing",
        },
    }
