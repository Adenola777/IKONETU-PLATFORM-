"use server";

import { revalidatePath } from "next/cache";
import { requireStaff } from "@/lib/session";
import { logError } from "@/lib/log";

/** An admin approves or declines an investor. The database checks the role again and writes the audit log. */
export async function decideInvestor(form: FormData) {
  const { supabase } = await requireStaff(true);
  const user = String(form.get("user") ?? "");
  const approve = form.get("approve") === "yes";
  if (!/^[0-9a-f-]{36}$/.test(user)) return;
  const { error } = await supabase.rpc("decide_investor", { p_user: user, p_approve: approve });
  if (error) logError("investor.decide_failed", { code: error.code });
  revalidatePath("/admin/investors");
}
