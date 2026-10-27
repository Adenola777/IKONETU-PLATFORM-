"""The investor register: reading a list of entries an admin pastes in, and the wording of the register pages.

The database function admin_register_add() of migration 20261024000001 checks every rule again, so these
rules only let the form report a problem line by line before the database refuses the whole list.
"""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone

from .validate import js_len, js_trim

MAX_ENTRIES = 1000
MAX_TEXT = 200_000

NUMBER = re.compile(r"[0-9]{3,6}")
ISO_DATE = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")
# A line is an entry when it ends with something written like a date. Headings, month names and counts do not.
DATE_AT_END = re.compile(r"[0-9]{1,4}[-/.][0-9]{1,2}[-/.][0-9]{1,4}\s*$")
# A line with no tab or comma: an optional row number, the register number, the name and the date, split by spaces.
SPACED = re.compile(r"(?:([0-9]{1,4})\s+)?([0-9]+)\s+(.+?)\s+(\S+)")


@dataclass
class ParsedList:
    entries: list[dict] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    skipped: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors and bool(self.entries)


def _fields(line: str) -> list[str] | None:
    """The line's columns, as a spreadsheet or a table copied from a document gives them: tabs, or commas."""
    if "\t" in line:
        return [f.strip() for f in line.split("\t") if f.strip()]
    if "," in line:
        return [f.strip() for f in next(csv.reader([line])) if f.strip()]
    m = SPACED.fullmatch(line.strip())
    return [g for g in m.groups() if g is not None] if m else None


def _date(text: str, today: date) -> tuple[str | None, str | None]:
    if not ISO_DATE.fullmatch(text):
        return None, "write the date as 2026-07-01"
    try:
        day = date.fromisoformat(text)
    except ValueError:
        return None, f"{text} is not a real date"
    if day > today:
        return None, "the registration date is after today"
    return text, None


def parse_register(text: str, today: date | None = None) -> ParsedList:
    """Reads the pasted list. Each entry gives the register number, the name and the registration date, in that
    order, with the row number in front if the list has one. Lines that do not end with a date, such as headings and
    the monthly totals under the list, are left out and counted."""
    today = today or datetime.now(timezone.utc).date()
    out = ParsedList()
    if len(text) > MAX_TEXT:
        out.errors.append("The list is too long to add at once. Add it in parts of up to 1,000 entries.")
        return out
    seen: dict[str, int] = {}
    for n, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or not DATE_AT_END.search(line):
            if line:
                out.skipped += 1
            continue
        fields = _fields(line)
        if fields is None or len(fields) not in (3, 4) or (len(fields) == 4 and not fields[0].isdigit()):
            out.errors.append(f"Line {n}: give the register number, the name and the date, in that order.")
            continue
        number, name, when = fields[-3], " ".join(fields[-2].split()), fields[-1]
        problems = []
        if not NUMBER.fullmatch(number):
            problems.append("the register number must be 3 to 6 digits, such as 001")
        if not 2 <= js_len(name) <= 120:
            problems.append("the name must be 2 to 120 characters")
        day, problem = _date(when, today)
        if problem:
            problems.append(problem)
        if number in seen:
            problems.append(f"register number {number} is also on line {seen[number]}")
        seen.setdefault(number, n)
        if problems:
            out.errors.append(f"Line {n}: {'; '.join(problems)}.")
            continue
        out.entries.append({"register_no": number, "full_name": js_trim(name), "registered_on": day})
    if not out.entries and not out.errors:
        out.errors.append("No entries were found. Each line needs the register number, the name and the date, such as "
                          "001, Ada Okafor, 2026-07-01.")
    if len(out.entries) > MAX_ENTRIES:
        out.errors.append("Add at most 1,000 entries at a time.")
    return out


def number_ranges(numbers: list[str]) -> str:
    """Register numbers as runs, such as 001 to 010 and 012. A run keeps numbers of the same width in sequence."""
    runs: list[list[str]] = []
    for no in numbers:
        last = runs[-1][-1] if runs else None
        if last is not None and len(last) == len(no) and int(no) == int(last) + 1:
            runs[-1].append(no)
        else:
            runs.append([no])
    parts = [r[0] if len(r) == 1 else f"{r[0]} to {r[-1]}" for r in runs]
    if len(parts) < 2:
        return "".join(parts)
    return ", ".join(parts[:-1]) + " and " + parts[-1]


def register_lines(after: dict | None) -> list[str]:
    """What an addition to the register changed, for its audit log entry."""
    a = after or {}
    lines = []
    if isinstance(a.get("added"), int):
        lines.append(f"Entries added: {a['added']}")
    if isinstance(a.get("unchanged"), int) and a["unchanged"]:
        lines.append(f"Already in the register and left as they were: {a['unchanged']}")
    numbers = a.get("numbers")
    if isinstance(numbers, list) and numbers and all(isinstance(x, str) for x in numbers):
        lines.append(f"Register numbers: {number_ranges(numbers)}")
    return lines


IMPORT_FIELDS = (
    ("founders", "Founders"), ("responses_received", "Form responses received"), ("responses_kept", "Form responses kept"),
    ("introductions", "Introductions"), ("investors_added", "Investor register entries added"), ("pitch_videos", "Pitch videos"),
    ("list", "List"), ("investor", "Investor register number"), ("messages_added", "Messages added"),
)


def import_lines(after: dict | None) -> list[str]:
    """What a load of the founder register brought in, for its audit log entry."""
    a = after or {}
    return [f"{name}: {a[key]}" for key, name in IMPORT_FIELDS
            if isinstance(a.get(key), (int, str)) and not isinstance(a.get(key), bool)]


def added_text(added: int, unchanged: int, skipped: int) -> str:
    """The confirmation shown after a list is added."""
    def count(n: int, one: str, many: str) -> str:
        return one if n == 1 else f"{n:,} {many}"
    parts = [f"{count(added, 'One entry', 'entries')} added to the register."]
    if unchanged:
        parts.append(f"{count(unchanged, 'One entry was', 'entries were')} already there with the same name and date, "
                     f"and {'it stayed as it was' if unchanged == 1 else 'they stayed as they were'}.")
    if skipped:
        parts.append(f"{count(skipped, 'One line', 'lines')} without a date, such as headings or totals, "
                     f"{'was' if skipped == 1 else 'were'} left out.")
    return " ".join(parts)


def refusal_text(message: str) -> str:
    """The message an admin sees when the database refuses the list, matched on the database's own words."""
    text = message or ""
    clash = re.search(r"different name or date: ([0-9, ]+)", text)
    if clash:
        numbers = [x.strip() for x in clash.group(1).split(",") if x.strip()]
        return (f"Nothing was added. These register numbers are already in the register with a different name or "
                f"date: {number_ranges(numbers)}. Correct those lines, or take them out, and add the list again.")
    if "only admins" in text:
        return "Only an admin can add to the investor register."
    entry = re.match(r"entry ([0-9]+): (.+)", text)
    if entry:
        return f"Nothing was added. Entry {entry.group(1)} was refused: {entry.group(2)}."
    return "Nothing was added. Please try again."
