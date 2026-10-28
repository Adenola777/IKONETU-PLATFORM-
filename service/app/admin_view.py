"""What the admin pages show, worked out as the admin design's boards worked it out.

Each board of the design the owner approved on 26 October 2026 holds its rules in a script: how a
date is written, how a list is filtered and sorted, what a CSV export holds. This module repeats
those rules in Python, so a page shows what its board showed for the same records.
"""

from __future__ import annotations

import csv
import io
import re
import unicodedata
from datetime import date, datetime, timezone
from math import ceil
from urllib.parse import urlencode

from fastapi.responses import Response

SHORT = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MONTHS = ("January", "February", "March", "April", "May", "June", "July", "August", "September", "October",
          "November", "December")
DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

# The status chips: their words, and the class that gives their colours.
VIDEO_CHIPS = {"pending": "Pending review", "approved": "Approved", "rejected": "Rejected", "none": "Not uploaded"}
INTRO_CHIPS = {"pending": "Pending", "accepted": "Accepted", "declined": "Declined", "withdrawn": "Withdrawn"}

# The six reasons a pitch video can be rejected for, as the Videos board lists them.
REJECT_REASONS = (
    "The pitch does not name the problem.", "The pitch does not name the solution.",
    "The pitch does not name the market.", "The pitch does not name the ask.",
    "The sound or the picture is not clear enough.", "The video breaks the platform rules.",
)
VIDEO_CHECKS = (("problem", "The problem"), ("solution", "The solution"), ("market", "The market"), ("ask", "The ask"))


# ---------------------------------------------------------------- dates
def moment(value: str | datetime) -> datetime:
    """A timestamp from PostgREST, such as 2026-01-13T21:16:55+00:00, in UTC."""
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc)
    d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return (d if d.tzinfo else d.replace(tzinfo=timezone.utc)).astimezone(timezone.utc)


def day_text(value: str | datetime | date) -> str:
    """13 Jan 2026, as the boards' dayText wrote a date."""
    d = value if isinstance(value, date) and not isinstance(value, datetime) else (
        date.fromisoformat(value) if isinstance(value, str) and len(value) == 10 else moment(value).date())
    return f"{d.day} {SHORT[d.month - 1]} {d.year}"


def long_text(value: str | datetime) -> str:
    """13 Jan 2026, 21:16, as the boards' longText wrote a time."""
    d = moment(value)
    return f"{day_text(d)}, {d.hour:02d}:{d.minute:02d}"


def full_date(value: str | date) -> str:
    """28 September 2026."""
    d = date.fromisoformat(value) if isinstance(value, str) else value
    return f"{d.day} {MONTHS[d.month - 1]} {d.year}"


def month_name(key: str) -> str:
    """July 2026, from 2026-07."""
    y, m = key.split("-")[:2]
    return f"{MONTHS[int(m) - 1]} {y}"


def today_text(now: datetime | None = None) -> str:
    """Saturday 24 October 2026, the dashboard's date, in UTC as the pages show times."""
    d = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    return f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month - 1]} {d.year}"


# ---------------------------------------------------------------- text
def initials(name: str) -> str:
    """Up to two initials, as the founder board drew the avatar."""
    parts = [p for p in re.split(r"\s+", name or "") if p]
    return "".join(p[0].upper() for p in parts[:2]) or "?"


def plural(n: int, one: str, many: str | None = None) -> str:
    return f"{n} {one if n == 1 else (many or one + 's')}"


def name_key(text: str) -> str:
    """A sort key close to the browser's localeCompare: accents and case do not decide the order."""
    plain = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in plain if not unicodedata.combining(c)).casefold()


def tel(phone: str) -> str:
    """The digits and the plus of a phone number, for a tel: link."""
    return "tel:" + re.sub(r"[^+0-9]", "", phone or "")


# ---------------------------------------------------------------- lists and pages
def query(path: str, pairs: dict[str, str | None]) -> str:
    """A page's address with the filters that differ from their defaults."""
    kept = [(k, v) for k, v in pairs.items() if v not in (None, "", "any", "all")]
    return path + ("?" + urlencode(kept) if kept else "")


def page_of(items: list, page: int, size: int) -> dict:
    """One page of a list, with the words under it, as the boards paged their tables."""
    pages = max(1, ceil(len(items) / size))
    page = min(max(page, 0), pages - 1)
    part = items[page * size: page * size + size]
    text = f"Showing {page * size + 1} to {page * size + len(part)} of {len(items)}" if items else "Showing 0"
    return {"rows": part, "page": page, "pages": pages, "text": text,
            "prev": page - 1 if page > 0 else None, "next": page + 1 if page < pages - 1 else None}


def page_number(raw: str | None) -> int:
    """The page asked for in the address, counted from 1 there and from 0 here."""
    return max(1, int(raw)) - 1 if raw and raw.isdigit() else 0


def shown_text(shown: int, total: int, noun: str) -> str:
    return f"{total} {noun}" if shown == total else f"{shown} of {total} {noun}"


# ---------------------------------------------------------------- CSV
def csv_response(filename: str, head: list[str], rows: list[list]) -> Response:
    """A CSV file as the boards built theirs: every cell quoted, lines ending CRLF, and a byte order mark
    so a spreadsheet reads the names in their own letters."""
    out = io.StringIO()
    writer = csv.writer(out, quoting=csv.QUOTE_ALL, lineterminator="\r\n")
    writer.writerow(head)
    for r in rows:
        writer.writerow(["" if v is None else v for v in r])
    body = "﻿" + out.getvalue().removesuffix("\r\n")
    return Response(body.encode("utf-8"), media_type="text/csv; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="{filename}"', "Cache-Control": "private, no-store"})


# ---------------------------------------------------------------- the frame
async def shell(v) -> dict:
    """What the sidebar shows: the counts beside People, the sample data badge and the account at its foot."""
    admin = v.profile.role == "admin"
    counts, sample = None, False
    if admin:
        r = await v.db.rpc("admin_shell")
        if r.ok and isinstance(r.data, dict):
            counts = {k: r.data.get(k) for k in ("founders", "investors", "introductions", "waitlist")}
            sample = bool(r.data.get("sample"))
    return {"admin": admin, "counts": counts, "sample": sample, "name": v.profile.full_name, "email": v.email}


# ---------------------------------------------------------------- the audit log's entries
# The kinds of entry, with the chip class each takes. The first three are the audit board's. Staff
# actions are the audit_log table's, which the board did not show and the app has kept since 17 October.
KINDS = {
    "waitlist": ("Joined the register", "a-chip-f"),
    "again": ("Sent the register form again", "a-chip-muted"),
    "investor": ("Added to the investor register", "a-chip-i"),
    "staff": ("Staff action", "a-chip-staff"),
}


def when_text(at: str, date_only: bool) -> str:
    """The audit board's whenText: 28 Sep 2026, with the time unless the entry has a date only."""
    d, _, t = at.partition("T")
    y, m, day = (int(x) for x in d.split("-"))
    return f"{day} {SHORT[m - 1]} {y}" + ("" if date_only else ", " + t[:5])


def register_entries(history: dict) -> list[dict]:
    """The audit board's entries for the form's responses and the investor register, newest first."""
    out = []
    for w in history.get("responses") or []:
        at = moment(w["responded_at"]).strftime("%Y-%m-%dT%H:%M:%S")
        first = bool(w.get("first"))
        what = ("Joined the register" if first else "Sent the register form again") + (f" with {w['startup']}" if w.get("startup") else "")
        details = [(k, v) for k, v in (
            ("Email", w.get("email")), ("Phone", w.get("phone")), ("Country", w.get("country")), ("University", w.get("university")),
            ("Startup", w.get("startup")), ("Sector", w.get("sector")),
            ("Register responses from this founder", str(w.get("response_count") or ""))) if v]
        out.append({"id": w["response_id"], "at": at, "date_only": False, "kind": "waitlist" if first else "again",
                    "who": w.get("full_name") or "(no name given)", "text": what, "details": details,
                    "href": f"/admin/founders/{w['record_id']}",
                    "search": " ".join([w.get("full_name") or "", w.get("email") or "", w.get("phone") or "", w.get("startup") or ""]).lower()})
    for r in history.get("investors") or []:
        out.append({"id": "i" + r["register_no"], "at": r["registered_on"] + "T00:00:00", "date_only": True, "kind": "investor",
                    "who": r["full_name"], "text": "Added to the investor register as number " + r["register_no"],
                    "details": [("Register number", r["register_no"]), ("Registered", full_date(r["registered_on"]))],
                    "href": None, "search": (r["full_name"] + " " + r["register_no"]).lower()})
    return out


def staff_entries(rows: list[dict], names: dict[str, str], describe) -> list[dict]:
    """The audit_log table's entries in the same shape. describe(row) gives the action's sentence and its details."""
    out = []
    for e in rows:
        text, details, href = describe(e)
        who = names.get(e.get("actor_id")) if e.get("actor_id") else None
        out.append({"id": f"a{e['id']}", "at": moment(e["created_at"]).strftime("%Y-%m-%dT%H:%M:%S"), "date_only": False,
                    "kind": "staff", "who": who or "The system", "text": text, "details": details, "href": href,
                    "search": " ".join([who or "the system", text, e.get("entity_id") or ""]).lower()})
    return out


def newest_first(entries: list[dict]) -> list[dict]:
    """Every entry, newest first. Entries at the same moment keep the order they came in."""
    return sorted(entries, key=lambda e: e["at"], reverse=True)
