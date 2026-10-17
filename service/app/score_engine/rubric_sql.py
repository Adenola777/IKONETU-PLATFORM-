"""Builds the SQL that seeds rubric_signals from a rubric.

The database copy is generated from the same source the score engine uses.
Regenerate the migration with `python3 -m app.score_engine.rubric_sql` from
the service folder. A test fails if the migration and this rubric differ.
"""

from __future__ import annotations

import json
import pathlib

from .rubric import RUBRIC_V2, Rubric

MIGRATION = pathlib.Path(__file__).resolve().parents[3] / "supabase" / "migrations" / "20261005000002_rubric_v2.sql"


def _q(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"


def rubric_to_sql(rubric: Rubric) -> str:
    rows = []
    for s in rubric.signals:
        stage = f"{_q(json.dumps(s.stage_points, separators=(',', ':')))}::jsonb" if s.stage_points else "null"
        usd = s.usd_per_point if s.usd_per_point is not None else "null"
        rows.append(
            f"  ({_q(rubric.version)}, {_q(s.code)}, {_q(s.category)}, {_q(s.label)}, {_q(s.mode)}, "
            f"{s.points}, {s.max_points}, {usd}, {stage})"
        )
    return "\n".join([
        # The first two lines name the TypeScript script that first wrote this migration, which
        # was removed on 17 October 2026. They stay, because a migration is never edited once it
        # may have been applied, so its text must come out the same as before.
        "-- Generated from packages/score-engine/src/rubric.ts. Do not edit by hand.",
        "-- Regenerate with: pnpm --filter @ikonetu/score-engine rubric:sql",
        f"insert into public.rubric_versions (version, is_active) values ({_q(rubric.version)}, true)",
        "on conflict (version) do update set is_active = excluded.is_active;",
        "",
        "insert into public.rubric_signals (rubric_version, code, category, label, mode, points, max_points, usd_per_point, stage_points) values",
        ",\n".join(rows),
        "on conflict (rubric_version, code) do update set",
        "  category = excluded.category, label = excluded.label, mode = excluded.mode, points = excluded.points,",
        "  max_points = excluded.max_points, usd_per_point = excluded.usd_per_point, stage_points = excluded.stage_points;",
        "",
    ])


if __name__ == "__main__":
    MIGRATION.write_text(rubric_to_sql(RUBRIC_V2))
    print(f"Wrote {MIGRATION}")
