import { z } from "zod";

/**
 * Between the two sign-in steps the server remembers where the code went, in
 * an HTTP-only cookie, so the address never appears in a URL or a log.
 */
export const PENDING_COOKIE = "ik_pending_sign_in";
export const CODE_LIFETIME_SECONDS = 300; // SRD SEC-A1: a code lasts 5 minutes

const pendingSchema = z.discriminatedUnion("kind", [
  z.object({ kind: z.literal("email"), email: z.string().email(), sentAt: z.number() }),
  z.object({ kind: z.literal("phone"), phone: z.string().regex(/^\+\d{10,15}$/), channel: z.enum(["sms", "whatsapp"]), sentAt: z.number() }),
]);

export type PendingSignIn = z.infer<typeof pendingSchema>;

export function readPending(raw: string | undefined): PendingSignIn | null {
  if (!raw) return null;
  try {
    const parsed = pendingSchema.safeParse(JSON.parse(raw));
    return parsed.success ? parsed.data : null;
  } catch {
    return null;
  }
}

/** Whether phone sign-in is switched on. It stays off until an SMS and WhatsApp provider is set up in Supabase. */
export function phoneSignInEnabled(): boolean {
  return process.env.NEXT_PUBLIC_PHONE_SIGN_IN === "on";
}
