import { describe, expect, it } from "vitest";
import { normaliseContact, parseWaitlist } from "./waitlist";

const valid = {
  fullName: "Amara Okafor",
  contact: "0803 123 4567",
  country: "NG",
  role: "founder",
  confirmedAdult: true,
  acceptedPrivacy: true,
  website: "",
};

describe("normaliseContact", () => {
  it("adds the country code to a local Nigerian number", () => {
    expect(normaliseContact("0803 123 4567", "NG")).toEqual({ value: "+2348031234567", type: "phone" });
  });
  it("adds the Kenyan code to a local Kenyan number", () => {
    expect(normaliseContact("0712-345-678", "KE")).toEqual({ value: "+254712345678", type: "phone" });
  });
  it("keeps an international number as typed", () => {
    expect(normaliseContact("+233 24 123 4567", "NG")).toEqual({ value: "+233241234567", type: "phone" });
  });
  it("treats a 00 prefix as international", () => {
    expect(normaliseContact("00233241234567", "NG")).toEqual({ value: "+233241234567", type: "phone" });
  });
  it("lower-cases an email", () => {
    expect(normaliseContact(" Amara@Example.COM ", "GH")).toEqual({ value: "amara@example.com", type: "email" });
  });
  it("rejects text that is neither", () => {
    expect(normaliseContact("call me maybe", "NG")).toBeNull();
    expect(normaliseContact("12345", "NG")).toBeNull();
    expect(normaliseContact("amara@", "NG")).toBeNull();
  });
});

describe("parseWaitlist", () => {
  it("builds a database row from a valid form", () => {
    const r = parseWaitlist(valid);
    expect(r).toEqual({
      ok: true,
      row: {
        full_name: "Amara Okafor",
        contact: "+2348031234567",
        contact_type: "phone",
        country: "NG",
        role: "founder",
        confirmed_adult: true,
        privacy_version: expect.any(String),
        source: "landing",
      },
    });
  });
  it("flags a filled honeypot as a bot", () => {
    expect(parseWaitlist({ ...valid, website: "http://spam" })).toEqual({ ok: false, bot: true });
  });
  it("requires the age and privacy boxes", () => {
    const r = parseWaitlist({ ...valid, confirmedAdult: false, acceptedPrivacy: false });
    expect(r.ok).toBe(false);
    if (!r.ok && !r.bot) {
      expect(r.errors).toEqual({
        acceptedPrivacy: "Please confirm you have read the privacy notice.",
        confirmedAdult: "You must be 18 or older to join.",
      });
    }
  });
  it("rejects countries outside Season 1", () => {
    const r = parseWaitlist({ ...valid, country: "ZA" });
    expect(r.ok === false && !r.bot && r.errors.country).toBeTruthy();
  });
  it("rejects unknown fields, so callers cannot set staff-only columns", () => {
    const r = parseWaitlist({ ...valid, source: "admin" });
    expect(r.ok).toBe(false);
  });
  it("reports a bad contact", () => {
    const r = parseWaitlist({ ...valid, contact: "not a contact" });
    expect(r.ok === false && !r.bot && r.errors.contact).toBe("Enter a valid phone number or email.");
  });
});
