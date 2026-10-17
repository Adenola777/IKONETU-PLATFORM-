"use server";

import { revalidatePath } from "next/cache";
import { redirect } from "next/navigation";
import { parseRoleChange, parseStatusChange, refusalText } from "@/lib/admin";
import { formValues, type AppState } from "@/lib/app-state";
import { logError, logInfo } from "@/lib/log";
import { requireStaff } from "@/lib/session";

/**
 * An admin changes a person's role through admin_set_role(), which refuses a
 * change to the admin's own account, checks that a founder has a venture and
 * an investor has an investor profile, and writes the audit log.
 */
export async function setRole(_prev: AppState, form: FormData): Promise<AppState> {
  const values = formValues(form);
  const { supabase } = await requireStaff(true);
  const parsed = parseRoleChange(form);
  if (!parsed.ok) return { status: "error", message: "Please check the form.", errors: parsed.errors, values };
  const { error } = await supabase.rpc("admin_set_role", { p_user: parsed.data.id, p_role: parsed.data.role, p_reason: parsed.data.reason });
  if (error) {
    (["P0001", "42501"].includes(error.code ?? "") ? logInfo : logError)("admin.role_failed", { user: parsed.data.id, code: error.code });
    return { status: "error", message: refusalText(error.message), errors: {}, values };
  }
  revalidatePath(`/admin/people/${parsed.data.id}`);
  redirect(`/admin/people/${parsed.data.id}?done=role`);
}

/** An admin suspends an account with a reason, or makes it active again, through admin_set_status(). */
export async function setStatus(_prev: AppState, form: FormData): Promise<AppState> {
  const values = formValues(form);
  const { supabase } = await requireStaff(true);
  const parsed = parseStatusChange(form);
  if (!parsed.ok) return { status: "error", message: "Please check the form.", errors: parsed.errors, values };
  const { error } = await supabase.rpc("admin_set_status", { p_user: parsed.data.id, p_status: parsed.data.status, p_reason: parsed.data.reason });
  if (error) {
    (["P0001", "42501"].includes(error.code ?? "") ? logInfo : logError)("admin.status_failed", { user: parsed.data.id, code: error.code });
    return { status: "error", message: refusalText(error.message), errors: {}, values };
  }
  revalidatePath(`/admin/people/${parsed.data.id}`);
  redirect(`/admin/people/${parsed.data.id}?done=${parsed.data.status}`);
}
