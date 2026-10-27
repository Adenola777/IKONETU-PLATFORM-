"""The Database board: what each table holds, in the board's groups, and the figures admin_database() reads.

The board described the 22 tables of 24 October 2026. The tables added since are described here in the same
way. A table the list does not know yet is shown under Other tables, so the page never hides one.
"""

from __future__ import annotations

from datetime import date

from . import admin_view as av

GROUPS: list[tuple[str, list[tuple[str, str]]]] = [
    ("People", [
        ("profiles", "Every account: role, status and name"),
        ("investor_profiles", "Investor details and approval"),
        ("investor_register", "The investor register"),
        ("founder_register", "The founder register, one record for each founder"),
        ("founder_register_responses", "Each response to the founder form"),
        ("register_imports", "Each load of the founder register"),
        ("consents", "Consents each person has given"),
        ("waitlist", "Waitlist sign-ups from the website"),
        ("investor_interest", "Investors who asked to hear when IkonetU opens"),
    ]),
    ("Ventures and Evidence", [
        ("ventures", "Each founder’s venture"),
        ("pitches", "Pitch video records and transcripts"),
        ("pitch_video_files", "Pitch video files in Google Drive and their review"),
        ("venture_updates", "Progress updates founders posted before the activity feed replaced them"),
        ("evidence", "Evidence founders send for review"),
        ("evidence_files", "Files attached to evidence"),
        ("reviews", "Reviewer decisions on evidence"),
        ("verification_checks", "Automatic checks run on evidence"),
    ]),
    ("Introductions", [
        ("introductions", "Introduction requests and their answers"),
        ("introduction_messages", "Messages between founder and investor"),
        ("register_introductions", "Introductions made from the registers"),
        ("reports", "Reports about conversations"),
    ]),
    ("IkonetU Score", [
        ("scores", "Each venture’s current score"),
        ("score_events", "Every change to a score"),
        ("score_snapshots", "The monthly record of scores"),
        ("rubric_versions", "Versions of the scoring rubric"),
        ("rubric_categories", "Rubric categories"),
        ("rubric_signals", "Rubric signals and their points"),
    ]),
    ("System", [
        ("audit_log", "Every admin and staff action"),
        ("activity_events", "The activity feed, written by the system"),
        ("platform_settings", "Pitch rules, introduction rules and the platform mode"),
    ]),
]
DESCRIBED = {name: what for _, tables in GROUPS for name, what in tables}
# Columns whose values are private. The page shows their names in red and says that their text is never shown.
PRIVATE = {"introduction_messages": {"body"}}
BUCKETS = {"pitches": "Pitch videos", "evidence": "Evidence documents"}


def migration_day(version: str) -> str:
    """24 October 2026, from a migration version such as 20261024000001."""
    return av.full_date(date(int(version[:4]), int(version[4:6]), int(version[6:8])))


def build(d: dict, q: str, with_rows: bool, today: date) -> dict:
    """Everything the Database page shows, with the search and the rows filter applied as the board applied them."""
    tables = {t["name"]: t for t in d.get("tables") or []}
    q = q.strip().lower()
    groups = [(label, [name for name, _ in names if name in tables]) for label, names in GROUPS]
    other = sorted(name for name in tables if name not in DESCRIBED)
    if other:
        groups.append(("Other tables", other))
    shown_groups = []
    for label, names in groups:
        shown = []
        for name in names:
            t = tables[name]
            what = DESCRIBED.get(name, "Not described yet")
            columns = t.get("columns") or []
            if with_rows and not t["rows"]:
                continue
            if q and q not in name and q not in what.lower() and not any(q in c for c in columns):
                continue
            private = PRIVATE.get(name, set())
            shown.append({
                "name": name, "what": what, "rows_text": av.plural(t["rows"], "row"), "rls": t["rls"],
                "open": bool(q) and any(q in c for c in columns), "private": bool(private),
                "columns": [{"name": c, "kind": "private" if c in private else "hit" if q and q in c else ""} for c in columns],
            })
        if shown:
            shown_groups.append({"label": label, "tables": shown})

    count = len(tables)
    secured = sum(1 for t in tables.values() if t["rls"])
    rows = sum(t["rows"] for t in tables.values())
    known = list(BUCKETS)
    buckets = sorted(d.get("buckets") or [], key=lambda b: (known.index(b["id"]) if b["id"] in known else len(known), b["id"]))
    files = sum(b["files"] for b in buckets)
    m = d.get("migrations")
    version = (d.get("version") or "").split(" ")[0]
    return {
        "subtitle": f"Supabase, PostgreSQL {version} · live counts read on {av.full_date(today)}",
        "summary": [
            ("Tables", str(count), f"Row security on all {count}" if secured == count else f"Row security on {secured} of {count}"),
            ("Rows in all tables", str(rows), f"Across {av.plural(count, 'table')}"),
            ("Stored files", str(files), " · ".join(f"{b['id']} {b['files']}" for b in buckets) or "No bucket"),
            ("Migrations", str(m["count"]), f"Latest {migration_day(m['latest'])}") if m and m.get("latest")
            else ("Migrations", "Not recorded", "This database keeps no record of them"),
        ],
        "groups": shown_groups,
        "buckets": [{"id": b["id"], "holds": BUCKETS.get(b["id"], "Other files"), "files": b["files"]} for b in buckets],
        "migrations": m if m and m.get("latest") else None,
        "latest": f"{m['latest']}_{m['name']}" if m and m.get("latest") and m.get("name") else (m or {}).get("latest"),
        "tables_text": f"{count}, all with row security on" if secured == count else f"{count}, {secured} of them with row security on",
    }
