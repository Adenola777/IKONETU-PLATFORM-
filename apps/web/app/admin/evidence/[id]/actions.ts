"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { formValues, type AppState } from "@/lib/app-state";
import { parseDecision } from "@/lib/forms";
import { logError, logInfo } from "@/lib/log";
import { recordVentureScore } from "@/lib/scoring";
import { requireStaff } from "@/lib/session";

/**
 * Records a reviewer's decision through decide_evidence, which checks the
 * reviewer's role, refuses their own evidence and writes the audit log. The
 * score engine then recomputes the venture's score from its approved evidence,
 * with up to three attempts (lib/scoring.ts).
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
    const own = /own evidence/.test(error.message);
    const taken = /already been decided/.test(error.message);
    if (own || taken) logInfo("evidence.decide_refused", { evidence: id, reason: own ? "own_evidence" : "already_decided" });
    else logError("evidence.decide_failed", { evidence: id, code: error.code });
    const message = own
      ? "You cannot decide evidence on your own venture."
      : taken
        ? "Someone has already decided this evidence."
        : "The decision was not saved. Please try again.";
    return { status: "error", message, errors: {}, values };
  }

  const ev = await supabase.from("evidence").select("venture_id").eq("id", id).single();
  const scored = ev.data ? await recordVentureScore(supabase, ev.data.venture_id, id) : false;
  revalidatePath("/admin/evidence");
  redirect(scored ? "/admin/evidence" : "/admin/evidence?score=failed");
}

/**
 * Recomputes the score of a venture whose score missed an update after a
 * decision. The staff queue lists such ventures.
 */
export async function recomputeScore(form: FormData) {
  const { supabase } = await requireStaff();
  const venture = String(form.get("venture") ?? "");
  if (!/^[0-9a-f-]{36}$/.test(venture)) return;
  const scored = await recordVentureScore(supabase, venture, null);
  revalidatePath("/admin/evidence");
  redirect(scored ? "/admin/evidence" : "/admin/evidence?score=failed");
}
