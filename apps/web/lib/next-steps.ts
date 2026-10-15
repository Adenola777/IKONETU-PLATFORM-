import { calculateScore, nextBestActions, RUBRIC_V2, type EvidenceItem, type Lane, type EvidenceStatus, type ProductStage } from "@ikonetu/score-engine";

export type OwnEvidence = {
  id: string; signal_code: string; status: string; lane: string | null; expires_at: string | null;
  item_count: number | null; months: number | null; revenue_usd: number | string | null; stage: string | null;
};

const WAITING = new Set(["submitted", "checking", "needs_review"]);

/**
 * The founder's next three steps: the evidence the score engine says would
 * add most next, leaving out anything already waiting for a reviewer.
 */
export function nextSteps(evidence: OwnEvidence[], limit = 3) {
  const items: EvidenceItem[] = evidence
    .filter((e) => e.lane)
    .map((e) => ({
      id: e.id,
      signalCode: e.signal_code,
      status: e.status as EvidenceStatus,
      lane: e.lane as Lane,
      expiresAt: e.expires_at,
      itemCount: e.item_count ?? undefined,
      months: e.months ?? undefined,
      revenueUsd: e.revenue_usd === null ? undefined : Number(e.revenue_usd),
      stage: (e.stage ?? undefined) as ProductStage | undefined,
    }));
  const waiting = new Set(evidence.filter((e) => WAITING.has(e.status)).map((e) => e.signal_code));
  const result = calculateScore({ evidence: items, rubric: RUBRIC_V2 });
  return nextBestActions(result, RUBRIC_V2, RUBRIC_V2.signals.length)
    .filter((a) => !waiting.has(a.code))
    .slice(0, limit);
}
