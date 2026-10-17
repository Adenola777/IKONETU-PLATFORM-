"use server";

import { revalidatePath } from "next/cache";
import { formValues, type AppState } from "@/lib/app-state";
import { parseInvestorEdit } from "@/lib/investor-profile";
import { requireInvestor } from "@/lib/session";
import { logError } from "@/lib/log";

/** An approved investor changes their details. A request already sent keeps the name it was sent with. */
export async function updateInvestor(_prev: AppState, form: FormData): Promise<AppState> {
  const values = formValues(form);
  const { supabase, user } = await requireInvestor();
  const parsed = parseInvestorEdit(form);
  if (!parsed.ok) return { status: "error", message: "Please check the form.", errors: parsed.errors, values };
  const a = await supabase.from("profiles").update(parsed.profile).eq("user_id", user.id);
  const b = await supabase.from("investor_profiles").update(parsed.investor).eq("user_id", user.id);
  if (a.error || b.error) {
    logError("investor.update_failed", { profile: a.error?.code, investor: b.error?.code });
    return { status: "error", message: "We could not save your changes. Please try again.", errors: {}, values };
  }
  revalidatePath("/investor", "layout");
  return { status: "sent", message: "Your details are saved." };
}
