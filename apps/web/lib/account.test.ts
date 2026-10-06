import { describe, expect, it } from "vitest";
import { codeSchema, emailSignInSchema, parseOnboarding, phoneSignInSchema } from "./account";
import { readPending } from "./pending-sign-in";
import { PRIVACY_VERSION } from "./waitlist";

function form(fields: Record<string, string>) {
  const f = new FormData();
  for (const [k, v] of Object.entries(fields)) f.set(k, v);
  return f;
}

const VALID = {
  fullName: "  Amara Okafor ",
  country: "NG",
  city: "Lagos",
  institution: "",
  graduateStatus: "Final-year student",
  bio: "",
  ventureName: "LearnLoop",
  sector: "Edtech",
  stage: "mvp",
  description: "",
  website: "learnloop.ng",
  linkedin: "",
  x: "",
  instagram: "https://instagram.com/learnloop",
  confirmedAdult: "on",
  acceptedPrivacy: "on",
  consent_registry_check: "on",
};

describe("emailSignInSchema", () => {
  it("lower-cases and trims the email", () => {
    expect(emailSignInSchema.parse({ email: "  Amara@Example.COM ", confirmedAdult: true }).email).toBe("amara@example.com");
  });
  it("refuses an address without an @", () => {
    expect(emailSignInSchema.safeParse({ email: "amara.example.com", confirmedAdult: true }).success).toBe(false);
  });
  it("requires the 18 or older box at sign-in (SEC-A9)", () => {
    const r = emailSignInSchema.safeParse({ email: "amara@example.com", confirmedAdult: false });
    expect(r.success).toBe(false);
    if (!r.success) expect(r.error.issues[0]?.message).toBe("You must be 18 or older to join.");
  });
});

describe("phoneSignInSchema", () => {
  it("turns a Nigerian local number into international form", () => {
    expect(phoneSignInSchema.parse({ country: "NG", phone: "0803 555 0142", confirmedAdult: true }).phone).toBe("+2348035550142");
  });
  it("uses the Kenyan dialling code for Kenya", () => {
    expect(phoneSignInSchema.parse({ country: "KE", phone: "0712 345 678", confirmedAdult: true }).phone).toBe("+254712345678");
  });
  it("refuses an email typed into the phone box", () => {
    const r = phoneSignInSchema.safeParse({ country: "NG", phone: "amara@example.com", confirmedAdult: true });
    expect(r.success).toBe(false);
    if (!r.success) expect(r.error.issues[0]?.path).toEqual(["phone"]);
  });
});

describe("codeSchema", () => {
  it("accepts six digits and ignores spaces", () => {
    expect(codeSchema.parse({ code: "481 203" }).code).toBe("481203");
  });
  it.each(["48120", "4812035", "48a203", ""])("refuses %j", (code) => {
    expect(codeSchema.safeParse({ code }).success).toBe(false);
  });
});

describe("readPending", () => {
  it("reads a valid email entry", () => {
    expect(readPending(JSON.stringify({ kind: "email", email: "a@b.co", sentAt: 1 }))).toEqual({ kind: "email", email: "a@b.co", sentAt: 1 });
  });
  it.each([undefined, "", "not json", JSON.stringify({ kind: "phone", phone: "0803", channel: "sms", sentAt: 1 })])(
    "returns null for %j",
    (raw) => {
      expect(readPending(raw)).toBeNull();
    },
  );
});

describe("parseOnboarding", () => {
  it("builds the profile, consent and venture rows from a valid form", () => {
    const result = parseOnboarding(form(VALID));
    expect(result).toEqual({
      ok: true,
      rows: {
        profile: {
          full_name: "Amara Okafor",
          country: "NG",
          city: "Lagos",
          institution: null,
          graduate_status: "Final-year student",
          bio: null,
          confirmed_adult: true,
        },
        consents: [
          { consent_type: "profile", granted: true, policy_version: PRIVACY_VERSION },
          { consent_type: "evidence_processing", granted: false, policy_version: PRIVACY_VERSION },
          { consent_type: "registry_check", granted: true, policy_version: PRIVACY_VERSION },
          { consent_type: "bank_check", granted: false, policy_version: PRIVACY_VERSION },
          { consent_type: "notifications", granted: false, policy_version: PRIVACY_VERSION },
        ],
        venture: {
          name: "LearnLoop",
          sector: "Edtech",
          stage: "mvp",
          country: "NG",
          description: null,
          website: "https://learnloop.ng",
          social_links: { instagram: "https://instagram.com/learnloop" },
        },
      },
    });
  });

  it("does not ask for the 18 or older box again when sign-in recorded it", () => {
    const { confirmedAdult: _, ...rest } = VALID;
    expect(parseOnboarding(form(rest), true).ok).toBe(true);
  });

  it("requires the 18 or older box when sign-in did not record it", () => {
    const { confirmedAdult: _, ...rest } = VALID;
    const result = parseOnboarding(form(rest));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.confirmedAdult).toBe("You must be 18 or older to join.");
  });

  it("requires the privacy notice box", () => {
    const { acceptedPrivacy: _, ...rest } = VALID;
    const result = parseOnboarding(form(rest));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.acceptedPrivacy).toBeDefined();
  });

  it("refuses a country outside Nigeria, Ghana and Kenya", () => {
    const result = parseOnboarding(form({ ...VALID, country: "ZA" }));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.country).toBe("Choose your country.");
  });

  it("refuses a stage the database does not hold", () => {
    const result = parseOnboarding(form({ ...VALID, stage: "unicorn" }));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.stage).toBe("Choose your stage.");
  });

  it("refuses a description or bio longer than the database allows", () => {
    const a = parseOnboarding(form({ ...VALID, description: "x".repeat(281) }));
    const b = parseOnboarding(form({ ...VALID, bio: "x".repeat(601) }));
    expect(a.ok || b.ok).toBe(false);
  });

  it.each(["javascript:alert(1)", "not a site", "ftp://files.example.com"])("refuses %j as a website", (website) => {
    const result = parseOnboarding(form({ ...VALID, website }));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.website).toBeDefined();
  });

  it("never takes a role or status from the form", () => {
    const result = parseOnboarding(form({ ...VALID, role: "admin", status: "active" }));
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.rows.profile).not.toHaveProperty("role");
  });
});
