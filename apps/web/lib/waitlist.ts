import { z } from "zod";
import { COUNTRIES, ROLES } from "./constants";

export { COUNTRIES, ROLES };

/** Version of the privacy notice a person accepts when they join. */
export const PRIVACY_VERSION = "2026-10-draft";

const EMAIL = z.string().email();

export type Contact = { value: string; type: "email" | "phone" };

/**
 * Turns what a person typed into a stored contact. Emails are lower-cased.
 * Phone numbers become international digits with a leading plus; a local
 * number that starts with 0 takes the dialling code of the chosen country.
 */
export function normaliseContact(raw: string, country: (typeof COUNTRIES)[number]["code"]): Contact | null {
  const input = raw.trim();
  if (input.includes("@")) {
    const email = input.toLowerCase();
    return EMAIL.safeParse(email).success && email.length <= 160 ? { value: email, type: "email" } : null;
  }
  if (!/^[+\d\s().-]+$/.test(input)) return null;
  let digits = input.replace(/\D/g, "");
  if (input.startsWith("+")) {
    // already international
  } else if (digits.startsWith("00")) {
    digits = digits.slice(2);
  } else if (digits.startsWith("0")) {
    const dial = COUNTRIES.find((c) => c.code === country)!.dial;
    digits = dial + digits.slice(1);
  }
  if (digits.length < 10 || digits.length > 15) return null;
  return { value: `+${digits}`, type: "phone" };
}

export const waitlistSchema = z
  .object({
    fullName: z.string().trim().min(2, "Enter your full name.").max(120, "Your name is too long."),
    contact: z.string().trim().min(5, "Enter a phone number or email.").max(160),
    country: z.enum(["NG", "GH", "KE"], { message: "Choose your country." }),
    role: z.enum(ROLES, { message: "Choose how you are joining." }),
    confirmedAdult: z.boolean().refine((v) => v, { message: "You must be 18 or older to join." }),
    acceptedPrivacy: z.boolean().refine((v) => v, { message: "Please confirm you have read the privacy notice." }),
    // Honeypot: people never see this field, so it must stay empty.
    website: z.string().max(0).optional().default(""),
  })
  .strict();

export type WaitlistInput = z.input<typeof waitlistSchema>;

export type WaitlistRow = {
  full_name: string;
  contact: string;
  contact_type: Contact["type"];
  country: "NG" | "GH" | "KE";
  role: (typeof ROLES)[number];
  confirmed_adult: true;
  privacy_version: string;
  source: string;
};

export type ParseResult =
  | { ok: true; row: WaitlistRow }
  | { ok: false; bot: true }
  | { ok: false; bot: false; errors: Record<string, string> };

export function parseWaitlist(body: unknown): ParseResult {
  if (body && typeof body === "object" && "website" in body && (body as { website?: unknown }).website) {
    return { ok: false, bot: true };
  }
  const parsed = waitlistSchema.safeParse(body);
  if (!parsed.success) {
    const errors: Record<string, string> = {};
    for (const issue of parsed.error.issues) {
      const key = String(issue.path[0] ?? "form");
      errors[key] ??= issue.message;
    }
    return { ok: false, bot: false, errors };
  }
  const d = parsed.data;
  const contact = normaliseContact(d.contact, d.country);
  if (!contact) return { ok: false, bot: false, errors: { contact: "Enter a valid phone number or email." } };
  return {
    ok: true,
    row: {
      full_name: d.fullName,
      contact: contact.value,
      contact_type: contact.type,
      country: d.country,
      role: d.role,
      confirmed_adult: true,
      privacy_version: PRIVACY_VERSION,
      source: "landing",
    },
  };
}
