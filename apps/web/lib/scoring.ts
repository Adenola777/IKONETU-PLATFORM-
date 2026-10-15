import { calculateScore, RUBRIC_V2, type EvidenceItem } from "@ikonetu/score-engine";
import type { SupabaseClient } from "@supabase/supabase-js";
import { logError, logWarn } from "./log";
import { withRetry } from "./retry";

/**
 * Recomputes a venture's score from its evidence with the score engine and
 * records it through record_score(), as a member of staff. record_score() is
 * safe to repeat: the same total only refreshes the current row and writes no
 * second history row. So a failed attempt is tried again, three times in all,
 * and a score that still fails stays on the staff list of scores to update
 * (ventures_with_stale_scores) until someone recomputes it.
 */
export async function recordVentureScore(
  supabase: SupabaseClient,
  ventureId: string,
  cause: string | null,
  options?: Parameters<typeof withRetry>[1],
): Promise<boolean> {
  const result = await withRetry(async () => {
    const all = await supabase
      .from("evidence")
      .select("id, signal_code, status, lane, expires_at, item_count, months, revenue_usd, stage")
      .eq("venture_id", ventureId);
    if (all.error) return { ok: false as const, error: all.error.code || all.error.message };
    const items: EvidenceItem[] = (all.data ?? [])
      .filter((e) => e.lane)
      .map((e) => ({
        id: e.id, signalCode: e.signal_code, status: e.status, lane: e.lane, expiresAt: e.expires_at,
        itemCount: e.item_count ?? undefined, months: e.months ?? undefined,
        revenueUsd: e.revenue_usd === null ? undefined : Number(e.revenue_usd), stage: e.stage ?? undefined,
      }));
    const score = calculateScore({ evidence: items, rubric: RUBRIC_V2 });
    const recorded = await supabase.rpc("record_score", {
      p_venture: ventureId, p_total: score.total, p_league: score.league,
      p_categories: score.categories, p_rubric: score.rubricVersion, p_cause: cause,
    });
    if (recorded.error) return { ok: false as const, error: recorded.error.code || recorded.error.message };
    return { ok: true as const, value: score.total };
  }, options);
  if (!result.ok) {
    logError("score.record_failed", { venture: ventureId, attempts: result.attempts, code: result.error });
    return false;
  }
  if (result.attempts > 1) logWarn("score.recorded_after_retry", { venture: ventureId, attempts: result.attempts });
  return true;
}
