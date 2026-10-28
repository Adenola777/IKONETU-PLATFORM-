"""The Analytics board's figures, worked out from admin_analytics_source() for one of its three ranges.

The board counted only the registers: the sample founders and the sample introductions are left out by
the database function, and the founders with introductions come from admin_register_introductions()
without its sample rows. Dates are read in UTC, as every admin page shows them.
"""

from __future__ import annotations

from datetime import date, timedelta

from . import admin_view as av

RANGES = ("year", "d90", "d30")
DAYS_BACK = {"d90": 90, "d30": 30}
WEEKLY_TITLE = "Founders and investors by week, each week ending on the Saturday shown"
CSV_HEAD = ["Period", "Founders joined", "Investors added to the register"]
CHART_HEIGHT = 170
UNIVERSITIES_SHOWN = 8


def window(key: str, today: date) -> tuple[date, date]:
    """The first and last day of a range. The last 90 days end today and count today as one of them."""
    if key == "year":
        return date(today.year, 1, 1), today
    return today - timedelta(days=DAYS_BACK[key] - 1), today


def button_label(key: str, today: date) -> str:
    return f"{today.year} so far" if key == "year" else f"Last {DAYS_BACK[key]} days"


def slug(key: str, today: date) -> str:
    return f"{today.year}-so-far" if key == "year" else f"last-{DAYS_BACK[key]}-days"


def range_text(key: str, start: date, end: date) -> str:
    """1 January to 24 October 2026, or 27 July 2026 to 24 October 2026."""
    if key == "year":
        return f"{start.day} {av.MONTHS[start.month - 1]} to {av.full_date(end)}"
    return f"{av.full_date(start)} to {av.full_date(end)}"


def periods(key: str, start: date, end: date) -> list[dict]:
    """The chart's bars: a month each for the year, and a week ending on Saturday for the shorter ranges.
    The first and last weeks are cut at the range's ends, and each keeps its Saturday as its label."""
    out = []
    if key == "year":
        for m in range(1, end.month + 1):
            first = date(end.year, m, 1)
            last = min(end, (date(end.year, m + 1, 1) if m < 12 else date(end.year + 1, 1, 1)) - timedelta(days=1))
            out.append({"label": av.SHORT[m - 1], "period": f"{av.MONTHS[m - 1]} {end.year}", "start": first, "end": last})
        return out
    day = start
    while day <= end:
        saturday = day + timedelta(days=(5 - day.weekday()) % 7)
        last = min(saturday, end)
        out.append({"label": f"{saturday.day} {av.SHORT[saturday.month - 1]}",
                    "period": f"{av.full_date(day)} to {av.full_date(last)}", "start": day, "end": last})
        day = last + timedelta(days=1)
    return out


def _within(d: date, start: date, end: date) -> bool:
    return start <= d <= end


def _ranked(counts: dict[str, int]) -> list[tuple[str, int]]:
    return sorted(counts.items(), key=lambda c: (-c[1], av.name_key(c[0])))


def _list(rows: list[tuple[str, int]]) -> list[dict]:
    top = max([1, *(n for _, n in rows)])
    return [{"label": label, "n": n, "style": f"width:{round(n / top * 100)}%"} for label, n in rows]


def universities(founders: list[dict]) -> list[tuple[str, int]]:
    """Founders by university, with the spellings of one university counted together under the
    spelling most of its founders used, or the first one sent when two are used as often."""
    groups: dict[str, dict[str, int]] = {}
    for f in founders:
        name = " ".join((f.get("university") or "").split())
        if name:
            spellings = groups.setdefault(name.casefold(), {})
            spellings[name] = spellings.get(name, 0) + 1
    totals = {}
    for spellings in groups.values():
        label = max(spellings.items(), key=lambda s: s[1])[0]
        totals[label] = sum(spellings.values())
    return _ranked(totals)[:UNIVERSITIES_SHOWN]


def build(source: dict, introductions: list[dict], key: str, today: date) -> dict:
    """Everything the Analytics page shows for one range."""
    start, end = window(key, today)
    joined = [f for f in source.get("founders") or [] if _within(av.moment(f["joined_at"]).date(), start, end)]
    registered = [date.fromisoformat(d) for d in source.get("investors") or []]
    videos = [date.fromisoformat(d) for d in source.get("videos") or []]
    intros = source.get("introductions") or []
    made = [n for n in intros if _within(date.fromisoformat(n["made_on"]), start, end)]

    bars = []
    for p in periods(key, start, end):
        f = sum(1 for x in joined if _within(av.moment(x["joined_at"]).date(), p["start"], p["end"]))
        i = sum(1 for d in registered if _within(d, p["start"], p["end"]))
        bars.append({**p, "f": f, "i": i})
    top = max([1, *(b["f"] + b["i"] for b in bars)])
    for b in bars:
        b["total"] = b["f"] + b["i"]
        b["f_style"] = f"height:{round(b['f'] / top * CHART_HEIGHT)}px"
        b["i_style"] = f"height:{round(b['i'] / top * CHART_HEIGHT)}px"
        b["f_top"], b["i_top"] = b["f"] > 0, b["i"] > 0 and b["f"] == 0
    chart_title = "Founders and investors by month" if key == "year" else WEEKLY_TITLE

    ids = {f["record_id"] for f in joined}
    introduced = {n["record_id"] for n in intros if n["record_id"] in ids}
    accepted = {n["record_id"] for n in intros if n["record_id"] in ids and n["status"] == "accepted"}
    funnel = [("Joined the register", len(joined)), ("Introduced to an investor", len(introduced)),
              ("Introduction accepted", len(accepted))]
    base = len(joined)

    countries: dict[str, int] = {}
    support: dict[str, int] = {}
    for f in joined:
        countries[f["country"]] = countries.get(f["country"], 0) + 1
        for s in f.get("support") or []:
            support[s] = support.get(s, 0) + 1

    table = sorted((n for n in introductions if not n["sample"] and _within(date.fromisoformat(n["made_on"]), start, end)),
                   key=lambda n: (n["investor_no"], n["intro_id"]))

    return {
        "key": key, "text": range_text(key, start, end), "chart_title": chart_title,
        "buttons": [(k, button_label(k, today)) for k in RANGES],
        "csv_name": f"ikonetu-analytics-{slug(key, today)}.csv",
        "kpis": [
            ("Founders joined", len(joined)),
            ("Investors added to the register", sum(1 for d in registered if _within(d, start, end))),
            ("Pitch videos", sum(1 for d in videos if _within(d, start, end))),
            ("Introductions made", len(made)),
            ("Introductions accepted", sum(1 for n in made if n["status"] == "accepted")),
        ],
        "bars": bars,
        "chart_label": chart_title + ": " + "; ".join(f"{b['period']}, {b['f']} founders, {b['i']} investors" for b in bars),
        "funnel": [{"label": label, "n": n, "style": f"width:{round(n / base * 100) if base else 0}%"} for label, n in funnel],
        "countries": _list(_ranked(countries)),
        "support": _list([s for s in _ranked(support) if s[1] > 1]),
        "universities": _list(universities(joined)),
        "no_founders": not joined,
        "table": [{"founder": n["founder_name"] or "(no name given)", "startup": n["startup"] or "Not given",
                   "investor": f"{n['investor_no']} · {n['investor_name']}", "made": av.day_text(n["made_on"]),
                   "status": n["status"], "chip": av.INTRO_CHIPS[n["status"]]} for n in table],
        "csv_rows": [[b["period"], b["f"], b["i"]] for b in bars],
    }
