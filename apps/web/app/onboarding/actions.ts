"use server";

import { redirect } from "next/navigation";
import { parseOnboarding } from "@/lib/account";
import { createClient } from "@/lib/supabase/server";
import { type FormState, typedValues } from "../form-state";

const TEXT_FIELDS = [
  "fullName", "country", "city", "institution", "graduateStatus", "bio",
  "ventureName", "sector", "stage", "description", "website", "linkedin", "x", "instagram",
] as const;

const FAILED = { status: "error", message: "We could not save your details. Please try again.", errors: {} } as const;

/**
 * Creates the founder's profile, records their consents and creates their first
 * venture, all as the signed-in person so row level security applies. Each
 * step is skipped when it already exists, so a retry after a failure is safe.
 */
export async function completeOnboarding(_prev: FormState, form: FormData): Promise<FormState> {
  const values = typedValues(form, TEXT_FIELDS);
  const supabase = await createClient();
  if (!supabase) return { ...FAILED, values };
  const { data: auth } = await supabase.auth.getUser();
  if (!auth.user) redirect("/signin");
  const userId = auth.user.id;

  const parsed = parseOnboarding(form, auth.user.user_metadata?.confirmed_adult === true);
  if (!parsed.ok) return { status: "error", message: "Please check the form.", errors: parsed.errors, values };
  const { profile, consents, venture } = parsed.rows;

  const existing = await supabase.from("profiles").select("user_id").eq("user_id", userId).maybeSingle();
  if (existing.error) return logged("read profile", existing.error, values);
  if (!existing.data) {
    const created = await supabase.from("profiles").insert({ user_id: userId, ...profile });
    if (created.error) return logged("insert profile", created.error, values);
    const agreed = await supabase.from("consents").insert(consents.map((c) => ({ user_id: userId, ...c })));
    if (agreed.error) return logged("insert consent", agreed.error, values);
  }

  const ventures = await supabase.from("ventures").select("id").eq("founder_id", userId).limit(1);
  if (ventures.error) return logged("read ventures", ventures.error, values);
  if (ventures.data.length === 0) {
    const created = await supabase.from("ventures").insert({ founder_id: userId, ...venture });
    if (created.error) return logged("insert venture", created.error, values);
  }

  redirect("/dashboard");
}

function logged(step: string, error: { code?: string }, values: Record<string, string>): FormState {
  console.error(`onboarding: ${step} failed`, error.code);
  return { ...FAILED, values };
}
