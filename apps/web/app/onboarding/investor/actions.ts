"use server";

import { redirect } from "next/navigation";
import { formValues, type AppState } from "@/lib/app-state";
import { parseInvestorSignUp } from "@/lib/investor-profile";
import { requireViewer } from "@/lib/session";

const FAILED = "We could not save your details. Please try again.";

/**
 * Creates the investor's profile as pending, records their consents and saves
 * their investor details, all as the signed-in person so row level security
 * applies. Each step is skipped when it already exists, so a retry is safe.
 */
export async function createInvestor(_prev: AppState, form: FormData): Promise<AppState> {
  const values = formValues(form);
  const { supabase, user, profile } = await requireViewer();
  if (profile && profile.role !== "investor") redirect("/dashboard");

  const parsed = parseInvestorSignUp(form, user.user_metadata?.confirmed_adult === true);
  if (!parsed.ok) return { status: "error", message: "Please check the form.", errors: parsed.errors, values };

  if (!profile) {
    const made = await supabase.from("profiles").insert({ user_id: user.id, ...parsed.profile });
    if (made.error) return logged("insert profile", made.error, values);
    const agreed = await supabase.from("consents").insert(parsed.consents.map((c) => ({ user_id: user.id, ...c })));
    if (agreed.error) return logged("insert consents", agreed.error, values);
  }
  const existing = await supabase.from("investor_profiles").select("user_id").eq("user_id", user.id).maybeSingle();
  if (existing.error) return logged("read investor profile", existing.error, values);
  if (!existing.data) {
    const saved = await supabase.from("investor_profiles").insert({ user_id: user.id, ...parsed.investor });
    if (saved.error) return logged("insert investor profile", saved.error, values);
  }
  redirect("/investor/pending");
}

function logged(step: string, error: { code?: string }, values: Record<string, string | string[]>): AppState {
  console.error(`investor sign-up: ${step} failed`, error.code);
  return { status: "error", message: FAILED, errors: {}, values };
}
