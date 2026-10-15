import { describe, expect, it } from "vitest";
import { parseDecision, parseEvidence, parseIntroductionNote, parsePitch, parseVenture } from "./forms";
import { parseInvestorEdit, parseInvestorSignUp } from "./investor-profile";

function form(entries: [string, string][]) {
  const f = new FormData();
  for (const [k, v] of entries) f.append(k, v);
  return f;
}

describe("investor sign-up", () => {
  const base: [string, string][] = [
    ["fullName", "Ife Investor"],
    ["basedIn", "other"],
    ["investorType", "angel"],
    ["sectors", "Fintech"],
    ["sectors", "Health"],
    ["stages", "revenue"],
    ["countries", "NG"],
    ["chequeSize", "Prefer not to say"],
    ["confirmedStatement", "on"],
    ["acceptedPrivacy", "on"],
  ];
  it("makes a pending investor profile, with the consents recorded", () => {
    const r = parseInvestorSignUp(form(base), true);
    expect(r.ok).toBe(true);
    if (!r.ok) return;
    expect(r.profile).toEqual({ full_name: "Ife Investor", country: null, role: "investor", status: "pending", confirmed_adult: true });
    expect(r.investor.sectors).toEqual(["Fintech", "Health"]);
    expect(r.investor.based_in).toBe("other");
    expect(r.consents.map((c) => [c.consent_type, c.granted])).toEqual([["profile", true], ["notifications", false]]);
  });
  it("asks a fund investor for the fund's name", () => {
    const r = parseInvestorSignUp(form(base.map(([k, v]) => (k === "investorType" ? [k, "fund"] : [k, v]))), true);
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors.firm).toBe("Enter the name of your fund or firm.");
  });
  it("needs a sector, the statement and the 18 or older confirmation", () => {
    const r = parseInvestorSignUp(form(base.filter(([k]) => k !== "sectors" && k !== "confirmedStatement")), false);
    expect(r.ok).toBe(false);
    if (!r.ok) {
      expect(r.errors.sectors).toBe("Choose at least one sector.");
      expect(r.errors.confirmedStatement).toBe("Confirm that this describes you.");
      expect(r.errors.confirmedAdult).toBe("You must be 18 or older to join.");
    }
  });
  it("refuses a sector that is not on the list", () => {
    const r = parseInvestorEdit(form([...base, ["sectors", "Crypto"]]));
    expect(r.ok).toBe(false);
  });
});

describe("evidence", () => {
  const pdf = { name: "statements.pdf", type: "application/pdf", size: 2_000_000 };
  it("needs a file or a link", () => {
    const r = parseEvidence({ signal: "revenue", summary: "Twelve months of bank statements", link: "", files: [] });
    expect(r.ok).toBe(false);
    if (!r.ok) expect(r.errors.files).toBe("Add a file or a link, so a reviewer can check it.");
  });
  it("accepts a link alone and adds https", () => {
    const r = parseEvidence({ signal: "press_coverage", summary: "An article about Kola Pay", link: "news.example.com/kola", files: [] });
    expect(r.ok && r.data.link).toBe("https://news.example.com/kola");
  });
  it("refuses large files, other types and unknown signals", () => {
    expect(parseEvidence({ signal: "revenue", summary: "Twelve months of statements", link: "", files: [{ ...pdf, size: 11 * 1024 * 1024 }] }).ok).toBe(false);
    expect(parseEvidence({ signal: "revenue", summary: "Twelve months of statements", link: "", files: [{ ...pdf, type: "text/html" }] }).ok).toBe(false);
    expect(parseEvidence({ signal: "made_up", summary: "Twelve months of statements", link: "", files: [pdf] }).ok).toBe(false);
    expect(parseEvidence({ signal: "revenue", summary: "Twelve months of statements", link: "", files: [pdf] }).ok).toBe(true);
  });
});

describe("pitch", () => {
  const ok = {
    path: "77777777-7777-7777-7777-777777777777/0b6c2f4e-1111-4222-8333-944455556666.mp4",
    mimeType: "video/mp4",
    size: 12_000_000,
    duration: 58.2,
    transcript: "Kola Pay lets market traders take card payments on their phones.",
  };
  it("accepts a one-minute pitch with a transcript", () => {
    expect(parsePitch(ok).ok).toBe(true);
  });
  it("refuses a long video, a large file, a short transcript and a path outside the pattern", () => {
    expect(parsePitch({ ...ok, duration: 120 }).ok).toBe(false);
    expect(parsePitch({ ...ok, size: 60 * 1024 * 1024 }).ok).toBe(false);
    expect(parsePitch({ ...ok, transcript: "Too short" }).ok).toBe(false);
    expect(parsePitch({ ...ok, path: "../../etc/passwd" }).ok).toBe(false);
  });
});

describe("notes, venture details and decisions", () => {
  it("asks for a note of at least 20 characters", () => {
    expect(parseIntroductionNote({ note: "Hi" }).ok).toBe(false);
    expect(parseIntroductionNote({ note: "We back payments companies in Lagos." }).ok).toBe(true);
  });
  it("keeps the sector to the list", () => {
    expect(parseVenture({ name: "Kola Pay", sector: "Payments", stage: "revenue", description: "", website: "" }).ok).toBe(false);
    expect(parseVenture({ name: "Kola Pay", sector: "Fintech", stage: "revenue", description: "", website: "kolapay.ng" }).ok).toBe(true);
  });
  it("needs a lane and a note to approve, and a reason to reject", () => {
    expect(parseDecision(form([["decision", "approve"], ["lane", "human"], ["publicNote", ""]])).ok).toBe(false);
    const ok = parseDecision(form([["decision", "approve"], ["lane", "human"], ["publicNote", "Compared with bank statements"], ["revenueUsd", "18,000"]]));
    expect(ok.ok && ok.data.decision === "approve" && ok.data.revenueUsd).toBe(18000);
    expect(parseDecision(form([["decision", "approve"], ["lane", "human"], ["publicNote", "Compared with statements"], ["months", "twelve"]])).ok).toBe(false);
    expect(parseDecision(form([["decision", "reject"], ["reason", ""]])).ok).toBe(false);
    expect(parseDecision(form([["decision", "needs_more"], ["reason", "Add the last three months."]])).ok).toBe(true);
    expect(parseDecision(form([["decision", "delete"]])).ok).toBe(false);
  });
});
