import type { Rubric } from "./types";

const q = (s: string): string => `'${s.replace(/'/g, "''")}'`;

/**
 * Builds the SQL that seeds rubric_signals from a rubric, so the database copy
 * is generated from the same source the score engine uses.
 */
export function rubricToSql(rubric: Rubric): string {
  const rows = rubric.signals.map((s) => {
    const stage = s.stagePoints ? `${q(JSON.stringify(s.stagePoints))}::jsonb` : "null";
    const usd = s.usdPerPoint ?? "null";
    return `  (${q(rubric.version)}, ${q(s.code)}, ${q(s.category)}, ${q(s.label)}, ${q(s.mode)}, ${s.points}, ${s.maxPoints}, ${usd}, ${stage})`;
  });
  return [
    `-- Generated from packages/score-engine/src/rubric.ts. Do not edit by hand.`,
    `-- Regenerate with: pnpm --filter @ikonetu/score-engine rubric:sql`,
    `insert into public.rubric_versions (version, is_active) values (${q(rubric.version)}, true)`,
    `on conflict (version) do update set is_active = excluded.is_active;`,
    ``,
    `insert into public.rubric_signals (rubric_version, code, category, label, mode, points, max_points, usd_per_point, stage_points) values`,
    rows.join(",\n"),
    `on conflict (rubric_version, code) do update set`,
    `  category = excluded.category, label = excluded.label, mode = excluded.mode, points = excluded.points,`,
    `  max_points = excluded.max_points, usd_per_point = excluded.usd_per_point, stage_points = excluded.stage_points;`,
    ``,
  ].join("\n");
}
