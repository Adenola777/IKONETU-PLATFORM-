import { describe, expect, it } from "vitest";
import { parseOnboarding, signInSchema } from "./account";
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
  ventureName: "LearnLoop",
  sector: "Edtech",
  stage: "mvp",
  description: "",
  confirmedAdult: "on",
  acceptedPrivacy: "on",
};

describe("signInSchema", () => {
  it("lower-cases and trims the email", () => {
    expect(signInSchema.parse({ email: "  Amara@Example.COM " }).email).toBe("amara@example.com");
  });
  it("refuses an address without an @", () => {
    expect(signInSchema.safeParse({ email: "amara.example.com" }).success).toBe(false);
  });
});

describe("parseOnboarding", () => {
  it("builds the three rows from a valid form", () => {
    const result = parseOnboarding(form(VALID));
    expect(result).toEqual({
      ok: true,
      rows: {
        profile: { full_name: "Amara Okafor", country: "NG", city: "Lagos", institution: null, confirmed_adult: true },
        consent: { consent_type: "profile", granted: true, policy_version: PRIVACY_VERSION },
        venture: { name: "LearnLoop", sector: "Edtech", stage: "mvp", country: "NG", description: null },
      },
    });
  });

  it("requires the 18 or older box", () => {
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

  it("refuses a description longer than the database allows", () => {
    const result = parseOnboarding(form({ ...VALID, description: "x".repeat(281) }));
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.description).toBeDefined();
  });

  it("never takes a role or status from the form", () => {
    const result = parseOnboarding(form({ ...VALID, role: "admin", status: "active" }));
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.rows.profile).not.toHaveProperty("role");
  });
});
