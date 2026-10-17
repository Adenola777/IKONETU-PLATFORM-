"""Numbers, dates and query strings written as the Next.js app's JavaScript wrote them.

Each function names the JavaScript it repeats. The formats were read from Node 22.22.0, with ICU
77.1, on 17 October 2026: for example September's short name in en-GB is "Sept", and an audit
time reads "17 October 2026 at 00:05".
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from decimal import ROUND_HALF_UP, Decimal
from urllib.parse import quote_plus

from .score_engine.engine import parse_instant
from .validate import JS_SPACE

MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
# Intl.DateTimeFormat("en-GB", { month: "short" }).
MONTHS_SHORT = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sept", "Oct", "Nov", "Dec")


def to_fixed(x: float, digits: int) -> str:
    """Number.prototype.toFixed: the exact value of the number, with a half rounded up."""
    return str(Decimal(x).quantize(Decimal(1).scaleb(-digits), rounding=ROUND_HALF_UP))


def number_text(x: float) -> str:
    """String(x) for the numbers a chart draws: a whole number has no decimal point."""
    return str(int(x)) if float(x).is_integer() else repr(float(x))


def parse_int(text: str) -> int | None:
    """Number.parseInt(text, 10): the whole number the text starts with, or None where JavaScript gives NaN."""
    m = re.match(r"[+-]?[0-9]+", text.lstrip(JS_SPACE))
    return int(m.group(0)) if m else None


def search_params(pairs: list[tuple[str, str]]) -> str:
    """new URLSearchParams(pairs).toString(): spaces as +, and only * - . _ and letters and digits left as they are."""
    def enc(s: str) -> str:
        return quote_plus(s, safe="*").replace("~", "%7E")
    return "&".join(f"{enc(k)}={enc(v)}" for k, v in pairs)


def _utc(value) -> datetime:
    d = value if isinstance(value, datetime) else parse_instant(value)
    return d.astimezone(timezone.utc)


def month_short(value) -> str:
    return MONTHS_SHORT[_utc(value).month - 1]


def month_long(value) -> str:
    """Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric" }), for example October 2026."""
    d = _utc(value)
    return f"{MONTHS[d.month - 1]} {d.year}"


def when_text(value) -> str:
    """The audit log's time, in UTC: 17 October 2026 at 00:05."""
    d = _utc(value)
    return f"{d.day} {MONTHS[d.month - 1]} {d.year} at {d.hour:02d}:{d.minute:02d}"
