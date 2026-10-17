"""The sign-in forms' rules and the cookie that carries a sign-in between its two steps."""

from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import asdict, dataclass
from typing import Literal

from .validate import Errors, is_email, js_len, js_trim, remove_js_space
from .waitlist import COUNTRY_CODES, normalise_contact

# Between the two sign-in steps the server remembers where the code went, in an
# HTTP-only cookie, so the address never appears in a URL or a log.
PENDING_COOKIE = "ik_pending_sign_in"
# The PKCE verifier for the link in the sign-in email, which only this browser holds.
VERIFIER_COOKIE = "ik_pkce"
CODE_LIFETIME_SECONDS = 300  # SRD SEC-A1: a code lasts 5 minutes

ADULT = "You must be 18 or older to join."


@dataclass
class Pending:
    kind: Literal["email", "phone"]
    sent_at: int  # milliseconds, as Date.now() gave
    email: str | None = None
    phone: str | None = None
    channel: Literal["sms", "whatsapp"] | None = None

    def encode(self) -> str:
        data = {k: v for k, v in asdict(self).items() if v is not None}
        return base64.urlsafe_b64encode(json.dumps(data).encode()).decode().rstrip("=")

    def describe(self) -> str:
        """Where the code went, with most of a phone number hidden."""
        if self.kind == "email":
            return f"to {self.email}"
        how = "by SMS" if self.channel == "sms" else "by WhatsApp"
        return f"{how} to a number ending {(self.phone or '')[-4:]}"

    @property
    def expires_at(self) -> int:
        return self.sent_at + CODE_LIFETIME_SECONDS * 1000


def now_ms() -> int:
    return int(time.time() * 1000)


def read_pending(raw: str | None) -> Pending | None:
    if not raw:
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
    except ValueError:
        return None
    if not isinstance(data, dict) or not isinstance(data.get("sent_at"), int):
        return None
    sent = data["sent_at"]
    if data.get("kind") == "email" and isinstance(data.get("email"), str) and is_email(data["email"]):
        return Pending(kind="email", email=data["email"], sent_at=sent)
    if (data.get("kind") == "phone" and isinstance(data.get("phone"), str)
            and re.fullmatch(r"\+[0-9]{10,15}", data["phone"]) and data.get("channel") in ("sms", "whatsapp")):
        return Pending(kind="phone", phone=data["phone"], channel=data["channel"], sent_at=sent)
    return None


def parse_email_sign_in(email: str, confirmed_adult: bool) -> tuple[str | None, Errors]:
    """The sign-in step: an email, and the 18 or older confirmation (SRD SEC-A9)."""
    errors = Errors()
    value = js_trim(email).lower()
    if not is_email(value):
        errors.add("email", "Enter a valid email address.")
    if js_len(value) > 160:
        errors.add("email", "That email is too long.")
    if not confirmed_adult:
        errors.add("confirmedAdult", ADULT)
    return (value if not errors else None), errors


def parse_phone_sign_in(country: str, phone: str, confirmed_adult: bool) -> tuple[str | None, Errors]:
    """The phone sign-in step. A local number takes the dialling code of the chosen country."""
    errors = Errors()
    if country not in COUNTRY_CODES:
        errors.add("country", "Choose your country.")
    value = js_trim(phone)
    if js_len(value) < 5:
        errors.add("phone", "Enter your phone number.")
    if js_len(value) > 30:
        errors.add("phone", "That number is too long.")
    if not confirmed_adult:
        errors.add("confirmedAdult", ADULT)
    if errors:
        return None, errors
    contact = normalise_contact(value, country)
    if contact is None or contact.type != "phone":
        errors.add("phone", "Enter a valid phone number.")
        return None, errors
    return contact.value, errors


def parse_code(code: str) -> tuple[str | None, Errors]:
    """The six-digit code from the email or message (SRD SEC-A1). Spaces are ignored."""
    errors = Errors()
    value = remove_js_space(code)
    if not re.fullmatch(r"[0-9]{6}", value):
        errors.add("code", "Enter the 6-digit code.")
        return None, errors
    return value, errors
