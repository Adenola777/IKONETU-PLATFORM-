"""Helpers that check form input the way the Next.js app's zod schemas did.

Each form keeps the first error per field, in the order the fields were
checked, as `firstErrors` did. Text is trimmed of the characters JavaScript's
trim() removes, and lengths count UTF-16 units as JavaScript's `length` does,
so a limit of 160 means what it meant before.
"""

from __future__ import annotations

import re

from ada_url import URL

# JavaScript's WhiteSpace and LineTerminator characters, which trim() and \s cover.
JS_SPACE = "\t\n\x0b\x0c\r \xa0                　﻿"
JS_SPACE_CLASS = "[" + re.escape(JS_SPACE) + "]"

# zod 3.25.76's email rule (v3/types.js, line 384).
EMAIL = re.compile(r"(?!\.)(?!.*\.\.)([A-Z0-9_'+\-\.]*)[A-Z0-9_+-]@([A-Z0-9][A-Z0-9\-]*\.)+[A-Z]{2,}", re.IGNORECASE)


def js_trim(value: str) -> str:
    return value.strip(JS_SPACE)


def js_len(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def is_email(value: str) -> bool:
    return EMAIL.fullmatch(value) is not None


def remove_js_space(value: str) -> str:
    return re.sub(JS_SPACE_CLASS, "", value)


def is_web_address(value: str) -> bool:
    """An http or https address whose host contains a dot, as the app's isWebAddress() required.

    The address is read by ada, the URL parser inside Node.js, so an address is accepted or
    refused exactly as `new URL()` accepted or refused it in the Next.js app. ada also parses
    the host the way a browser does: it percent-decodes it, converts an international name to
    its ASCII form and reads numbers such as 0x7f.1 as an IPv4 address.
    """
    try:
        address = URL(value)
    except (ValueError, UnicodeError):
        return False
    return address.protocol in ("http:", "https:") and "." in address.hostname


class Errors(dict):
    """Field errors, keeping only the first message for each field."""

    def add(self, field: str, message: str) -> None:
        self.setdefault(field, message)
