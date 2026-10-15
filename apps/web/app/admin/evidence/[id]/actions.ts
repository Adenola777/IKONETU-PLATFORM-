"use server";

import { calculateScore, RUBRIC_V2, type EvidenceItem } from "@ikonetu/score-engine";
import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { formValues, type AppState } from "@/lib/app-state";
import { parseDecision } from "@/lib/forms";
import { requireStaff } from "@/lib/session";

/**
 * Records a reviewer's decision through decide_evidence, which checks the
 * reviewer's role, refuses their own evidence and writes the audit log. The
 * score engine then recomputes the venture's score from its approved evidence.
 */
export async function decide(_prev: AppState, form: FormData): Promise<AppState> {
  const values = formValues(form);
  const { supabase } = await requireStaff();
  const id = String(values.id ?? "");
  if (!/^[0-9a-f-]{36}$/.test(id)) return { status: "error", message: "This evidence could not be found.", errors: {} };
  const parsed = parseDecision(form);
  if (!parsed.ok) return { status: "error", message: "Please check the decision.", errors: parsed.errors, values };
  const d = parsed.data;
  const args =
    d.decision === "approve"
      ? { p_evidence: id, p_decision: "approve", p_lane: d.lane, p_public_note: d.publicNote, p_item_count: d.itemCount, p_months: d.months, p_revenue_usd: d.revenueUsd, p_stage: d.stage }
      : { p_evidence: id, p_decision: d.decision, p_reason: d.reason };
  const { error } = await supabase.rpc("decide_evidence", args);
  if (error) {
    console.error("decide_evidence failed", error.code, error.message);
    const message = /own evidence/.test(error.message)
      ? "You cannot decide evidence on your own venture."
      : /already been decided/.test(error.message)
        ? "Someone has already decided this evidence."
        : "The decision was not saved. Please try again.";
    return { status: "error", message, errors: {}, values };
  }

  const ev = await supabase.from("evidence").select("venture_id").eq("id", id).single();
  if (ev.data) {
    const all = await supabase
      .from("evidence")
      .select("id, signal_code, status, lane, expires_at, item_count, months, revenue_usd, stage")
      .eq("venture_id", ev.data.venture_id);
    const items: EvidenceItem[] = (all.data ?? [])
      .filter((e) => e.lane)
      .map((e) => ({
        id: e.id, signalCode: e.signal_code, status: e.status, lane: e.lane, expiresAt: e.expires_at,
        itemCount: e.item_count ?? undefined, months: e.months ?? undefined, revenueUsd: e.revenue_usd === null ? undefined : Number(e.revenue_usd), stage: e.stage ?? undefined,
      }));
    const score = calculateScore({ evidence: items, rubric: RUBRIC_V2 });
    const recorded = await supabase.rpc("record_score", {
      p_venture: ev.data.venture_id, p_total: score.total, p_league: score.league,
      p_categories: score.categories, p_rubric: score.rubricVersion, p_cause: id,
    });
    if (recorded.error) console.error("record_score failed", recorded.error.code);
  }
  revalidatePath("/admin/evidence");
  redirect("/admin/evidence");
}
