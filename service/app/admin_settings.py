"""The Settings board's forms: what each one accepts, and the database's refusals in the board's words.

The admin functions of migration 20261027000002 check every value again and write the audit log, so these
checks only spare a round trip and keep what was typed on the page.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TYPES = (("mp4", "video/mp4", "MP4"), ("webm", "video/webm", "WebM"), ("mov", "video/quicktime", "MOV (QuickTime)"))
STAFF_ROLES = (("reviewer", "Reviewer"), ("admin", "Admin"))
EMAIL = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")
SAVED = "Saved."


@dataclass
class Form:
    data: dict = field(default_factory=dict)
    error: str | None = None


def _whole(text: str) -> int | None:
    text = (text or "").strip()
    return int(text) if re.fullmatch(r"\d{1,6}", text) else None


def parse_pitch_rules(types: list[str], max_mb: str, max_seconds: str) -> Form:
    chosen = [mime for key, mime, _ in TYPES if key in types]
    size, length = _whole(max_mb), _whole(max_seconds)
    if not chosen:
        return Form(error="Allow at least one file type.")
    if size is None or not 1 <= size <= 50:
        return Form(error="Give the largest file as a whole number from 1 to 50 MB.")
    if length is None or not 1 <= length <= 90:
        return Form(error="Give the longest pitch as a whole number from 1 to 90 seconds.")
    return Form({"p_types": chosen, "p_max_mb": size, "p_max_seconds": length})


def parse_introduction_rules(on: bool, per_day: str) -> Form:
    """With introductions switched off, the box is disabled and the limit kept as it was."""
    n = _whole(per_day)
    if on and (n is None or n < 1):
        return Form(error="Give the daily limit as a whole number of 1 or more.")
    return Form({"p_on": on, "p_per_day": n if on else None})


def parse_mode(mode: str, message: str) -> Form:
    message = message.strip()
    if mode not in ("live", "maintenance"):
        return Form(error="Choose live or maintenance.")
    if mode == "maintenance" and not message:
        return Form(error="Write the message people will see.")
    if len(message) > 280:
        return Form(error="Keep the message to 280 characters.")
    return Form({"p_mode": mode, "p_message": message or None})


def parse_password(first: str, second: str) -> Form:
    if not first:
        return Form(error="Type the new password.")
    if first != second:
        return Form(error="The two passwords do not match.")
    return Form({"password": first})


def password_refusal(code: str | None, status: int | None) -> str:
    """Supabase's refusal of a new password, from its list of Auth error codes."""
    if code == "weak_password":
        return "This password is too weak. Choose a longer one."
    if code == "same_password":
        return "This is the password you use now. Choose a new one."
    if code == "reauthentication_needed":
        return "Supabase asks you to sign in again first. Sign out, sign in, and then change the password."
    if status == 429 or code == "over_request_rate_limit":
        return "Too many changes were tried. Please wait a few minutes and try again."
    return "The password was not changed. Please try again."


def parse_staff_add(email: str, role: str) -> Form:
    email = email.strip().lower()
    if not EMAIL.fullmatch(email):
        return Form(error="Enter the email address of an existing account.")
    if role not in dict(STAFF_ROLES):
        return Form(error="Choose reviewer or admin.")
    return Form({"p_email": email, "p_role": role})


def staff_refusal(text: str, email: str) -> str:
    if "no account uses this email address" in text:
        return "No account uses this email address."
    if "on the staff list already" in text:
        return f"{email} is already on the staff list."
    if "not active" in text:
        return "This account is suspended, so it cannot be added to the staff list."
    return "The staff list was not changed. Please try again."


def removed_text(email: str, became: str) -> str:
    if became == "founder":
        return f"Removed {email} from staff. The account is a founder account again."
    return (f"Removed {email} from staff. The account is suspended, because it has no venture. "
            "You can change it on People and roles.")
