"""Builds the SQL that seeds rubric_categories and rubric_signals from a rubric.

The database copy is generated from the same source the score engine uses. Regenerate the
migration with `python3 -m app.score_engine.rubric_sql` from the service folder. A test fails if
the migration and this rubric differ.

Rubric v2's seed, migration 20261005000002, was written by the TypeScript script removed on
17 October 2026. It is applied and is never edited, so this module no longer writes it.
"""

from __future__ import annotations

import pathlib

from .rubric import RUBRIC_V3, Rubric

MIGRATION = pathlib.Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "20261020000002_rubric_v3.sql"


def _q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def rubric_to_sql(rubric: Rubric) -> str:
    categories = [
        f"  ({_q(rubric.version)}, {_q(c.code)}, {_q(c.label)}, {c.max_points}, {c.weight}, "
        f"{_q(c.alternative_to) if c.alternative_to else 'null'}, {i})"
        for i, c in enumerate(rubric.categories, 1)
    ]
    signals = [
        f"  ({_q(rubric.version)}, {_q(s.code)}, {_q(s.category)}, {_q(s.label)}, 'fixed', {s.points}, {s.points}, "
        f"{_q(s.how)}, {_q(s.hint)})"
        for s in rubric.signals
    ]
    return "\n".join([
        "-- Generated from service/app/score_engine/rubric.py. Do not edit by hand.",
        "-- Regenerate with: python3 -m app.score_engine.rubric_sql (from the service folder)",
        "-- Only one rubric is active at a time, so the one before is switched off first.",
        f"update public.rubric_versions set is_active = false where is_active and version <> {_q(rubric.version)};",
        f"insert into public.rubric_versions (version, is_active, published_at) values ({_q(rubric.version)}, true, now())",
        "on conflict (version) do update set is_active = excluded.is_active;",
        "",
        "insert into public.rubric_categories (rubric_version, code, label, max_points, weight, alternative_to, position) values",
        ",\n".join(categories),
        "on conflict (rubric_version, code) do update set",
        "  label = excluded.label, max_points = excluded.max_points, weight = excluded.weight,",
        "  alternative_to = excluded.alternative_to, position = excluded.position;",
        "",
        "insert into public.rubric_signals (rubric_version, code, category, label, mode, points, max_points, how, hint) values",
        ",\n".join(signals),
        "on conflict (rubric_version, code) do update set",
        "  category = excluded.category, label = excluded.label, mode = excluded.mode, points = excluded.points,",
        "  max_points = excluded.max_points, how = excluded.how, hint = excluded.hint;",
        "",
    ])


if __name__ == "__main__":
    MIGRATION.write_text(rubric_to_sql(RUBRIC_V3))
    print(f"Wrote {MIGRATION}")
