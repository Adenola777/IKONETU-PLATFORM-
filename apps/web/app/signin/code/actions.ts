"use server";

import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { codeSchema, firstErrors } from "@/lib/account";
import { CODE_LIFETIME_SECONDS, PENDING_COOKIE, readPending } from "@/lib/pending-sign-in";
import { SITE_URL } from "@/lib/site";
import { createClient } from "@/lib/supabase/server";
import type { FormState } from "../../form-state";

const START_AGAIN: FormState = { status: "error", message: "Your code has expired. Please ask for a new one.", errors: {} };

/** Checks the six-digit code. A right code signs the person in and opens the session cookie. */
export async function verifyCode(_prev: FormState, form: FormData): Promise<FormState> {
  const jar = await cookies();
  const pending = readPending(jar.get(PENDING_COOKIE)?.value);
  if (!pending) return START_AGAIN;

  const parsed = codeSchema.safeParse({ code: String(form.get("code") ?? "") });
  if (!parsed.success) return { status: "error", message: "Please check the code.", errors: firstErrors(parsed.error) };

  const supabase = await createClient();
  if (!supabase) return { status: "error", message: "Sign-up is not open yet. Please try again soon.", errors: {} };

  const { error } =
    pending.kind === "email"
      ? await supabase.auth.verifyOtp({ email: pending.email, token: parsed.data.code, type: "email" })
      : await supabase.auth.verifyOtp({ phone: pending.phone, token: parsed.data.code, type: "sms" });
  if (error) {
    console.error("verifyOtp failed", error.status, error.code);
    if (error.status === 429) {
      return { status: "error", message: "Too many attempts. Please wait a few minutes and try again.", errors: {} };
    }
    return { status: "error", message: "That code is wrong or has expired.", errors: { code: "Check the code and try again, or ask for a new one." } };
  }

  jar.delete({ name: PENDING_COOKIE, path: "/signin" });
  redirect("/dashboard");
}

/** Sends a new code. For a phone, the person can switch from WhatsApp to SMS here. */
export async function resendCode(_prev: FormState, form: FormData): Promise<FormState> {
  const jar = await cookies();
  const pending = readPending(jar.get(PENDING_COOKIE)?.value);
  if (!pending) return START_AGAIN;
  const supabase = await createClient();
  if (!supabase) return { status: "error", message: "Sign-up is not open yet. Please try again soon.", errors: {} };

  let error;
  if (pending.kind === "phone") {
    const channel = form.get("channel") === "sms" ? "sms" : "whatsapp";
    ({ error } = await supabase.auth.signInWithOtp({ phone: pending.phone, options: { channel } }));
    pending.channel = channel;
  } else {
    ({ error } = await supabase.auth.signInWithOtp({ email: pending.email, options: { emailRedirectTo: `${SITE_URL}/auth/callback` } }));
  }
  if (error) {
    console.error("resend failed", error.status, error.code);
    const message =
      error.status === 429
        ? "Too many codes were requested. Please wait a few minutes and try again."
        : "We could not send a new code. Please try again.";
    return { status: "error", message, errors: {} };
  }
  pending.sentAt = Date.now();
  jar.set(PENDING_COOKIE, JSON.stringify(pending), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/signin",
    maxAge: CODE_LIFETIME_SECONDS * 2,
  });
  return { status: "sent", message: "We sent a new code." };
}
