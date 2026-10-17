import { z } from "zod";
import { firstErrors, STAGES, type FieldErrors } from "./account";
import { COUNTRIES } from "./constants";
import { CHEQUE_SIZES, INTEREST_COUNTRIES, INVESTOR_TYPES } from "./investor-options";
import { SECTORS } from "./product";
import { PRIVACY_VERSION } from "./waitlist";

const STAGE_CODES = STAGES.map((s) => s.code) as unknown as readonly ["idea", "mvp", "revenue", "scaling"];
const COUNTRY_CODES = COUNTRIES.map((c) => c.code) as unknown as readonly ["NG", "GH", "KE"];

export const BASED_IN = [
  { code: "NG", name: "Nigeria" },
  { code: "GH", name: "Ghana" },
  { code: "KE", name: "Kenya" },
  { code: "other", name: "Somewhere else" },
] as const;

export const INVESTOR_TYPE_OPTIONS = [
  { code: "individual", name: "Individual investor", hint: "You invest your own money, without a fund or an angel network." },
  { code: "angel", name: "Angel investor", hint: "You invest your own money in early-stage companies, alone or with an angel network." },
  { code: "fund", name: "Fund investor", hint: "You invest for a fund, a firm or another organisation." },
] as const;

const optional = (max: number, message: string) =>
  z
    .string()
    .trim()
    .max(max, message)
    .transform((v) => (v === "" ? null : v));

const optionalUrl = z
  .string()
  .trim()
  .max(200, "That address is too long.")
  .transform((v) => (v === "" ? null : /^https?:\/\//i.test(v) ? v : `https://${v}`))
  .refine((v) => {
    if (v === null) return true;
    try {
      const u = new URL(v);
      return (u.protocol === "https:" || u.protocol === "http:") && u.hostname.includes(".");
    } catch {
      return false;
    }
  }, "Enter a full web address, for example savannahseed.com.");

const unique = <T>(list: T[]) => new Set(list).size === list.length;

/** The investor's details. The same rules apply at sign-up and when they edit. */
const detailsSchema = z.object({
  fullName: z.string().trim().min(2, "Enter your full name.").max(120, "Your name is too long."),
  basedIn: z.enum(INTEREST_COUNTRIES, { message: "Choose where you are based." }),
  investorType: z.enum(INVESTOR_TYPES, { message: "Choose the one that describes you best." }),
  firm: optional(120, "The firm name is too long."),
  website: optionalUrl,
  sectors: z
    .array(z.enum(SECTORS, { message: "Choose sectors from the list." }))
    .min(1, "Choose at least one sector.")
    .refine(unique, "Choose each sector once."),
  stages: z.array(z.enum(STAGE_CODES, { message: "Choose stages from the list." })).refine(unique, "Choose each stage once."),
  countries: z.array(z.enum(COUNTRY_CODES, { message: "Choose countries from the list." })).refine(unique, "Choose each country once."),
  chequeSize: z.enum(CHEQUE_SIZES, { message: "Choose a cheque size, or prefer not to say." }),
  thesis: optional(600, "Keep this to 600 characters."),
  confirmedStatement: z.boolean().refine((v) => v, "Confirm that this describes you."),
});

const signUpSchema = detailsSchema
  .extend({
    confirmedAdult: z.boolean().refine((v) => v, "You must be 18 or older to join."),
    acceptedPrivacy: z.boolean().refine((v) => v, "Please confirm you have read the privacy policy."),
    notifications: z.boolean(),
  })
  .refine((d) => d.investorType !== "fund" || d.firm !== null, { path: ["firm"], message: "Enter the name of your fund or firm." });

const editSchema = detailsSchema.refine((d) => d.investorType !== "fund" || d.firm !== null, {
  path: ["firm"],
  message: "Enter the name of your fund or firm.",
});

export type InvestorRow = {
  investor_type: (typeof INVESTOR_TYPES)[number];
  firm: string | null;
  website: string | null;
  based_in: (typeof INTEREST_COUNTRIES)[number];
  sectors: string[];
  stages: string[];
  countries: string[];
  cheque_size: (typeof CHEQUE_SIZES)[number];
  thesis: string | null;
  confirmed_statement: true;
};

export const INVESTOR_TEXT_FIELDS = ["fullName", "basedIn", "investorType", "firm", "website", "chequeSize", "thesis"] as const;

function read(form: FormData) {
  const text = (k: string) => String(form.get(k) ?? "");
  const all = (k: string) => form.getAll(k).map(String);
  return {
    fullName: text("fullName"),
    basedIn: text("basedIn"),
    investorType: text("investorType"),
    firm: text("firm"),
    website: text("website"),
    sectors: all("sectors"),
    stages: all("stages"),
    countries: all("countries"),
    chequeSize: text("chequeSize"),
    thesis: text("thesis"),
    confirmedStatement: form.get("confirmedStatement") === "on",
  };
}

function rows(d: z.infer<typeof detailsSchema>) {
  return {
    fullName: d.fullName,
    country: d.basedIn === "other" ? null : (d.basedIn as "NG" | "GH" | "KE"),
    investor: {
      investor_type: d.investorType,
      firm: d.firm,
      website: d.website,
      based_in: d.basedIn,
      sectors: d.sectors,
      stages: d.stages,
      countries: d.countries,
      cheque_size: d.chequeSize,
      thesis: d.thesis,
      confirmed_statement: true,
    } satisfies InvestorRow,
  };
}

/** Reads the investor sign-up form. `adultConfirmed` is true when sign-in already asked. */
export function parseInvestorSignUp(form: FormData, adultConfirmed = false) {
  const parsed = signUpSchema.safeParse({
    ...read(form),
    confirmedAdult: adultConfirmed || form.get("confirmedAdult") === "on",
    acceptedPrivacy: form.get("acceptedPrivacy") === "on",
    notifications: form.get("notifications") === "on",
  });
  if (!parsed.success) return { ok: false as const, errors: firstErrors(parsed.error) as FieldErrors };
  const r = rows(parsed.data);
  return {
    ok: true as const,
    profile: { full_name: r.fullName, country: r.country, role: "investor" as const, status: "pending" as const, confirmed_adult: true as const },
    investor: r.investor,
    consents: [
      { consent_type: "profile" as const, granted: true, policy_version: PRIVACY_VERSION },
      { consent_type: "notifications" as const, granted: parsed.data.notifications, policy_version: PRIVACY_VERSION },
    ],
  };
}

/** Reads the form an investor uses to change their details. */
export function parseInvestorEdit(form: FormData) {
  const parsed = editSchema.safeParse(read(form));
  if (!parsed.success) return { ok: false as const, errors: firstErrors(parsed.error) as FieldErrors };
  const r = rows(parsed.data);
  return { ok: true as const, profile: { full_name: r.fullName, country: r.country }, investor: r.investor };
}
