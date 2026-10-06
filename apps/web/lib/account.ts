import { z } from "zod";
import { COUNTRIES } from "./constants";
import { normaliseContact, PRIVACY_VERSION } from "./waitlist";

export const STAGES = [
  { code: "idea", label: "Idea" },
  { code: "mvp", label: "First version" },
  { code: "revenue", label: "Earning revenue" },
  { code: "scaling", label: "Scaling" },
] as const;

/**
 * The consents a founder gives before any data is processed (PRD A-4, SRD SEC-D4).
 * The profile is needed to run the account, so it is required. The others are
 * optional toggles, and each answer is recorded, including a no.
 */
export const OPTIONAL_CONSENTS = [
  { code: "evidence_processing", label: "Check the evidence I submit, by AI and by a reviewer" },
  { code: "registry_check", label: "Look up my company in the official registry" },
  { code: "bank_check", label: "Read my business bank statements when I connect an account" },
  { code: "notifications", label: "Send me notifications about my evidence, rounds and introductions" },
] as const;

type ConsentCode = "profile" | (typeof OPTIONAL_CONSENTS)[number]["code"];

const COUNTRY_CODES = COUNTRIES.map((c) => c.code) as unknown as readonly ["NG", "GH", "KE"];
const STAGE_CODES = STAGES.map((s) => s.code) as unknown as readonly ["idea", "mvp", "revenue", "scaling"];

const adult = z.boolean().refine((v) => v, { message: "You must be 18 or older to join." });

/** The sign-in step: an email, and the 18 or older confirmation (SRD SEC-A9). */
export const emailSignInSchema = z.object({
  email: z.string().trim().toLowerCase().email("Enter a valid email address.").max(160, "That email is too long."),
  confirmedAdult: adult,
});

/** The phone sign-in step. A local number takes the dialling code of the chosen country. */
export const phoneSignInSchema = z
  .object({
    country: z.enum(COUNTRY_CODES, { message: "Choose your country." }),
    phone: z.string().trim().min(5, "Enter your phone number.").max(30, "That number is too long."),
    confirmedAdult: adult,
  })
  .transform((d, ctx) => {
    const contact = normaliseContact(d.phone, d.country);
    if (!contact || contact.type !== "phone") {
      ctx.addIssue({ code: z.ZodIssueCode.custom, path: ["phone"], message: "Enter a valid phone number." });
      return z.NEVER;
    }
    return { phone: contact.value, confirmedAdult: d.confirmedAdult };
  });

/** The six-digit code from the email or message (SRD SEC-A1). Spaces are ignored. */
export const codeSchema = z.object({
  code: z
    .string()
    .transform((v) => v.replace(/\s/g, ""))
    .refine((v) => /^\d{6}$/.test(v), { message: "Enter the 6-digit code." }),
});

const optionalText = (max: number, message: string) =>
  z
    .string()
    .trim()
    .max(max, message)
    .transform((v) => (v === "" ? null : v));

/** A web address. A bare domain gets https:// added. */
const optionalUrl = (message: string) =>
  z
    .string()
    .trim()
    .max(200, message)
    .transform((v) => (v === "" ? null : /^https?:\/\//i.test(v) ? v : `https://${v}`))
    .refine((v) => v === null || isWebAddress(v), { message });

function isWebAddress(v: string): boolean {
  try {
    const u = new URL(v);
    return (u.protocol === "https:" || u.protocol === "http:") && u.hostname.includes(".");
  } catch {
    return false;
  }
}

export const onboardingSchema = z
  .object({
    fullName: z.string().trim().min(2, "Enter your full name.").max(120, "Your name is too long."),
    country: z.enum(COUNTRY_CODES, { message: "Choose your country." }),
    city: optionalText(80, "The city name is too long."),
    institution: optionalText(120, "The institution name is too long."),
    graduateStatus: optionalText(80, "Keep this to 80 characters."),
    bio: optionalText(600, "Keep your bio to 600 characters."),
    ventureName: z.string().trim().min(1, "Enter your venture's name.").max(120, "The venture name is too long."),
    sector: z.string().trim().min(2, "Enter your sector, for example Fintech.").max(60, "The sector is too long."),
    stage: z.enum(STAGE_CODES, { message: "Choose your stage." }),
    description: optionalText(280, "Keep the description to 280 characters."),
    website: optionalUrl("Enter a full web address, for example learnloop.ng."),
    linkedin: optionalUrl("Enter a full LinkedIn address."),
    x: optionalUrl("Enter a full X address."),
    instagram: optionalUrl("Enter a full Instagram address."),
    confirmedAdult: adult,
    acceptedPrivacy: z.boolean().refine((v) => v, { message: "Please confirm you have read the privacy notice." }),
    consents: z.record(z.boolean()),
  })
  .strict();

export type FieldErrors = Record<string, string>;

export type OnboardingRows = {
  profile: {
    full_name: string;
    country: "NG" | "GH" | "KE";
    city: string | null;
    institution: string | null;
    graduate_status: string | null;
    bio: string | null;
    confirmed_adult: true;
  };
  consents: { consent_type: ConsentCode; granted: boolean; policy_version: string }[];
  venture: {
    name: string;
    sector: string;
    stage: (typeof STAGE_CODES)[number];
    country: "NG" | "GH" | "KE";
    description: string | null;
    website: string | null;
    social_links: Record<string, string>;
  };
};

/**
 * Reads the onboarding form. The ids of the person are added by the caller,
 * from the session. `adultConfirmed` is true when the person already confirmed
 * at sign-in, so the form does not ask twice.
 */
export function parseOnboarding(
  form: FormData,
  adultConfirmed = false,
): { ok: true; rows: OnboardingRows } | { ok: false; errors: FieldErrors } {
  const text = (k: string) => String(form.get(k) ?? "");
  const parsed = onboardingSchema.safeParse({
    fullName: text("fullName"),
    country: text("country"),
    city: text("city"),
    institution: text("institution"),
    graduateStatus: text("graduateStatus"),
    bio: text("bio"),
    ventureName: text("ventureName"),
    sector: text("sector"),
    stage: text("stage"),
    description: text("description"),
    website: text("website"),
    linkedin: text("linkedin"),
    x: text("x"),
    instagram: text("instagram"),
    confirmedAdult: adultConfirmed || form.get("confirmedAdult") === "on",
    acceptedPrivacy: form.get("acceptedPrivacy") === "on",
    consents: Object.fromEntries(OPTIONAL_CONSENTS.map((c) => [c.code, form.get(`consent_${c.code}`) === "on"])),
  });
  if (!parsed.success) return { ok: false, errors: firstErrors(parsed.error) };
  const d = parsed.data;
  const social: Record<string, string> = {};
  if (d.linkedin) social.linkedin = d.linkedin;
  if (d.x) social.x = d.x;
  if (d.instagram) social.instagram = d.instagram;
  return {
    ok: true,
    rows: {
      profile: {
        full_name: d.fullName,
        country: d.country,
        city: d.city,
        institution: d.institution,
        graduate_status: d.graduateStatus,
        bio: d.bio,
        confirmed_adult: true,
      },
      consents: [
        { consent_type: "profile", granted: true, policy_version: PRIVACY_VERSION },
        ...OPTIONAL_CONSENTS.map((c) => ({
          consent_type: c.code,
          granted: d.consents[c.code] === true,
          policy_version: PRIVACY_VERSION,
        })),
      ],
      venture: {
        name: d.ventureName,
        sector: d.sector,
        stage: d.stage,
        country: d.country,
        description: d.description,
        website: d.website,
        social_links: social,
      },
    },
  };
}

export function firstErrors(error: z.ZodError): FieldErrors {
  const errors: FieldErrors = {};
  for (const issue of error.issues) {
    const key = String(issue.path[0] ?? "form");
    errors[key] ??= issue.message;
  }
  return errors;
}
