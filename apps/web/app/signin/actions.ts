"use server";

import { firstErrors, signInSchema } from "@/lib/account";
import { SITE_URL } from "@/lib/site";
import { createClient } from "@/lib/supabase/server";
import { type FormState, typedValues } from "../form-state";

/**
 * Emails a sign-in link. Supabase creates the account the first time an email
 * is used, so sign-up and sign-in are the same step. The reply is the same
 * whether or not the email already has an account.
 */
export async function sendSignInLink(_prev: FormState, form: FormData): Promise<FormState> {
  const parsed = signInSchema.safeParse({ email: String(form.get("email") ?? "") });
  if (!parsed.success) {
    return { status: "error", message: "Please check the form.", errors: firstErrors(parsed.error), values: typedValues(form, ["email"]) };
  }
  const supabase = await createClient();
  if (!supabase) {
    return { status: "error", message: "Sign-up is not open yet. Please try again soon.", errors: {} };
  }
  const { error } = await supabase.auth.signInWithOtp({
    email: parsed.data.email,
    options: { emailRedirectTo: `${SITE_URL}/auth/callback` },
  });
  if (error) {
    console.error("signInWithOtp failed", error.status, error.code);
    const message =
      error.status === 429
        ? "Too many sign-in emails were sent. Please wait a few minutes and try again."
        : "We could not send the email. Please try again.";
    return { status: "error", message, errors: {}, values: typedValues(form, ["email"]) };
  }
  return { status: "sent", message: `We sent a sign-in link to ${parsed.data.email}. Open it on this device to continue.` };
}
