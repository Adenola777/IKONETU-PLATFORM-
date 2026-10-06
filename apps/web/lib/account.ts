import { z } from "zod";
import { COUNTRIES } from "./constants";
import { PRIVACY_VERSION } from "./waitlist";

export const STAGES = [
  { code: "idea", label: "Idea" },
  { code: "mvp", label: "First version" },
  { code: "revenue", label: "Earning revenue" },
  { code: "scaling", label: "Scaling" },
] as const;

const COUNTRY_CODES = COUNTRIES.map((c) => c.code) as unknown as readonly ["NG", "GH", "KE"];
const STAGE_CODES = STAGES.map((s) => s.code) as unknown as readonly ["idea", "mvp", "revenue", "scaling"];

export const signInSchema = z.object({
  email: z.string().trim().toLowerCase().email("Enter a valid email address.").max(160, "That email is too long."),
});

const optionalText = (max: number, message: string) =>
  z
    .string()
    .trim()
    .max(max, message)
    .transform((v) => (v === "" ? null : v));

export const onboardingSchema = z
  .object({
    fullName: z.string().trim().min(2, "Enter your full name.").max(120, "Your name is too long."),
    country: z.enum(COUNTRY_CODES, { message: "Choose your country." }),
    city: optionalText(80, "The city name is too long."),
    institution: optionalText(120, "The institution name is too long."),
    ventureName: z.string().trim().min(1, "Enter your venture's name.").max(120, "The venture name is too long."),
    sector: z.string().trim().min(2, "Enter your sector, for example Fintech.").max(60, "The sector is too long."),
    stage: z.enum(STAGE_CODES, { message: "Choose your stage." }),
    description: optionalText(280, "Keep the description to 280 characters."),
    confirmedAdult: z.boolean().refine((v) => v, { message: "You must be 18 or older to join." }),
    acceptedPrivacy: z.boolean().refine((v) => v, { message: "Please confirm you have read the privacy notice." }),
  })
  .strict();

export type FieldErrors = Record<string, string>;

export type OnboardingRows = {
  profile: { full_name: string; country: "NG" | "GH" | "KE"; city: string | null; institution: string | null; confirmed_adult: true };
  consent: { consent_type: "profile"; granted: true; policy_version: string };
  venture: { name: string; sector: string; stage: (typeof STAGE_CODES)[number]; country: "NG" | "GH" | "KE"; description: string | null };
};

/** The ids of the person and the user are added by the caller, from the session. */
export function parseOnboarding(form: FormData): { ok: true; rows: OnboardingRows } | { ok: false; errors: FieldErrors } {
  const text = (k: string) => String(form.get(k) ?? "");
  const parsed = onboardingSchema.safeParse({
    fullName: text("fullName"),
    country: text("country"),
    city: text("city"),
    institution: text("institution"),
    ventureName: text("ventureName"),
    sector: text("sector"),
    stage: text("stage"),
    description: text("description"),
    confirmedAdult: form.get("confirmedAdult") === "on",
    acceptedPrivacy: form.get("acceptedPrivacy") === "on",
  });
  if (!parsed.success) return { ok: false, errors: firstErrors(parsed.error) };
  const d = parsed.data;
  return {
    ok: true,
    rows: {
      profile: { full_name: d.fullName, country: d.country, city: d.city, institution: d.institution, confirmed_adult: true },
      consent: { consent_type: "profile", granted: true, policy_version: PRIVACY_VERSION },
      venture: { name: d.ventureName, sector: d.sector, stage: d.stage, country: d.country, description: d.description },
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
