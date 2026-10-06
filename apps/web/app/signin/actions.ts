"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { emailSignInSchema, firstErrors, phoneSignInSchema } from "@/lib/account";
import { CODE_LIFETIME_SECONDS, PENDING_COOKIE, phoneSignInEnabled, type PendingSignIn } from "@/lib/pending-sign-in";
import { SITE_URL } from "@/lib/site";
import { createClient } from "@/lib/supabase/server";
import { type FormState, typedValues } from "../form-state";

/**
 * Sends a six-digit sign-in code (PRD A-1, A-2). Supabase creates the account
 * the first time an address is used, so sign-up and sign-in are one step. The
 * reply is the same whether or not the address already has an account.
 */
export async function sendCode(_prev: FormState, form: FormData): Promise<FormState> {
  const usePhone = form.get("method") === "phone" && phoneSignInEnabled();
  const values = typedValues(form, usePhone ? ["country", "phone"] : ["email"]);
  const confirmedAdult = form.get("confirmedAdult") === "on";

  const parsed = usePhone
    ? phoneSignInSchema.safeParse({ country: form.get("country") ?? "", phone: form.get("phone") ?? "", confirmedAdult })
    : emailSignInSchema.safeParse({ email: form.get("email") ?? "", confirmedAdult });
  if (!parsed.success) {
    return { status: "error", message: "Please check the form.", errors: firstErrors(parsed.error), values };
  }

  const supabase = await createClient();
  if (!supabase) return { status: "error", message: "Sign-up is not open yet. Please try again soon.", errors: {}, values };

  // The confirmation is kept on the new account, so onboarding does not ask again.
  const data = { confirmed_adult: true };
  let pending: PendingSignIn;
  let error;
  if (usePhone && "phone" in parsed.data) {
    pending = { kind: "phone", phone: parsed.data.phone, channel: "whatsapp", sentAt: Date.now() };
    ({ error } = await supabase.auth.signInWithOtp({ phone: pending.phone, options: { channel: "whatsapp", data } }));
  } else if ("email" in parsed.data) {
    pending = { kind: "email", email: parsed.data.email, sentAt: Date.now() };
    ({ error } = await supabase.auth.signInWithOtp({
      email: pending.email,
      // Supabase's default email carries a link, not the code, until the template
      // can be edited. The link returns to /auth/callback, which signs the person in.
      options: { data, emailRedirectTo: `${SITE_URL}/auth/callback` },
    }));
  } else {
    return { status: "error", message: "Please check the form.", errors: {}, values };
  }

  if (error) {
    console.error("signInWithOtp failed", error.status, error.code);
    const message =
      error.status === 429
        ? "Too many codes were requested. Please wait a few minutes and try again."
        : "We could not send your code. Please try again.";
    return { status: "error", message, errors: {}, values };
  }

  (await cookies()).set(PENDING_COOKIE, JSON.stringify(pending), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/signin",
    maxAge: CODE_LIFETIME_SECONDS * 2,
  });
  redirect("/signin/code");
}
