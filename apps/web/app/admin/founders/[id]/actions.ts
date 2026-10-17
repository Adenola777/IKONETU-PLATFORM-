"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { parseHold, parseLift, refusalText } from "@/lib/admin";
import { formValues, type AppState } from "@/lib/app-state";
import { logError, logInfo } from "@/lib/log";
import { requireStaff } from "@/lib/session";

/**
 * An admin hides a founder's profile from investors with a reason the founder
 * reads. admin_hide_venture() checks the role again, unpublishes the profile,
 * keeps the founder from publishing it, and writes the audit log.
 */
export async function hideVenture(_prev: AppState, form: FormData): Promise<AppState> {
  const values = formValues(form);
  const { supabase } = await requireStaff(true);
  const parsed = parseHold(form);
  if (!parsed.ok) return { status: "error", message: "Please check the reason.", errors: parsed.errors, values };
  const { error } = await supabase.rpc("admin_hide_venture", { p_venture: parsed.data.id, p_reason: parsed.data.reason });
  if (error) {
    (error.code === "P0001" ? logInfo : logError)("admin.hide_failed", { venture: parsed.data.id, code: error.code });
    return { status: "error", message: refusalText(error.message), errors: {}, values };
  }
  revalidatePath(`/admin/founders/${parsed.data.id}`);
  redirect(`/admin/founders/${parsed.data.id}?done=hidden`);
}

/** An admin lifts the hold. The founder can then publish the profile again; it is not published for them. */
export async function liftHold(_prev: AppState, form: FormData): Promise<AppState> {
  const values = formValues(form);
  const { supabase } = await requireStaff(true);
  const parsed = parseLift(form);
  if (!parsed.ok) return { status: "error", message: "Please check the note.", errors: parsed.errors, values };
  const { error } = await supabase.rpc("admin_lift_hold", { p_venture: parsed.data.id, p_note: parsed.data.note });
  if (error) {
    (error.code === "P0001" ? logInfo : logError)("admin.lift_failed", { venture: parsed.data.id, code: error.code });
    return { status: "error", message: refusalText(error.message), errors: {}, values };
  }
  revalidatePath(`/admin/founders/${parsed.data.id}`);
  redirect(`/admin/founders/${parsed.data.id}?done=lifted`);
}
