import { z } from "zod";
import { PRIVACY_VERSION } from "./waitlist";

export const INTEREST_COUNTRIES = ["NG", "GH", "KE", "other"] as const;
export const INTEREST_SECTORS = ["Fintech", "Agritech", "Edtech", "Health", "Other"] as const;
export const CHEQUE_SIZES = ["Under $25,000", "$25,000 to $100,000", "$100,000 to $500,000", "Over $500,000", "Prefer not to say"] as const;
export const INVESTOR_TYPES = ["individual", "angel", "fund"] as const;

/** The answers to the investor interest form, as the page sends them. The rules match the table's checks. */
export const investorInterestSchema = z
  .object({
    fullName: z.string().trim().min(2, "Enter your full name.").max(120, "Your name is too long."),
    email: z.string().trim().toLowerCase().max(160, "Your email is too long.").email("Enter a valid email address."),
    country: z.enum(INTEREST_COUNTRIES, { message: "Choose where you are based." }),
    firm: z.string().trim().max(120, "The firm name is too long.").optional().default(""),
    sectors: z
      .array(z.enum(INTEREST_SECTORS, { message: "Choose sectors from the list." }))
      .min(1, "Choose at least one sector.")
      .max(INTEREST_SECTORS.length)
      .refine((list) => new Set(list).size === list.length, { message: "Choose each sector once." }),
    chequeSize: z.enum(CHEQUE_SIZES, { message: "Choose a cheque size, or prefer not to say." }),
    investorType: z.enum(INVESTOR_TYPES, { message: "Choose the one that describes you best." }),
    confirmedAdult: z.boolean().refine((v) => v, { message: "You must be 18 or older to register." }),
    acceptedPrivacy: z.boolean().refine((v) => v, { message: "Confirm that you have read the privacy policy." }),
    emailConsent: z.boolean().refine((v) => v, { message: "We need your agreement to email you about investor access." }),
    confirmedStatement: z.boolean().refine((v) => v, { message: "Confirm that this describes you." }),
    // Honeypot: people never see this field, so it must stay empty.
    website: z.string().max(0).optional().default(""),
  })
  .strict();

export type InvestorInterestRow = {
  full_name: string;
  email: string;
  country: (typeof INTEREST_COUNTRIES)[number];
  firm: string | null;
  sectors: (typeof INTEREST_SECTORS)[number][];
  cheque_size: (typeof CHEQUE_SIZES)[number];
  investor_type: (typeof INVESTOR_TYPES)[number];
  confirmed_adult: true;
  confirmed_statement: true;
  email_consent: true;
  privacy_version: string;
  source: string;
};

export type InterestParseResult =
  | { ok: true; row: InvestorInterestRow }
  | { ok: false; bot: true }
  | { ok: false; bot: false; errors: Record<string, string> };

export function parseInvestorInterest(body: unknown): InterestParseResult {
  if (body && typeof body === "object" && "website" in body && (body as { website?: unknown }).website) {
    return { ok: false, bot: true };
  }
  const parsed = investorInterestSchema.safeParse(body);
  if (!parsed.success) {
    const errors: Record<string, string> = {};
    for (const issue of parsed.error.issues) {
      const key = String(issue.path[0] ?? "form");
      errors[key] ??= issue.message;
    }
    return { ok: false, bot: false, errors };
  }
  const d = parsed.data;
  return {
    ok: true,
    row: {
      full_name: d.fullName,
      email: d.email,
      country: d.country,
      firm: d.firm ? d.firm : null,
      sectors: d.sectors,
      cheque_size: d.chequeSize,
      investor_type: d.investorType,
      confirmed_adult: true,
      confirmed_statement: true,
      email_consent: true,
      privacy_version: PRIVACY_VERSION,
      source: "website",
    },
  };
}
