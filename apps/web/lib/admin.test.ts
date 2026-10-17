import { describe, expect, it } from "vitest";
import {
  actionText,
  changeLines,
  entityHref,
  entryReason,
  parseHold,
  parseLift,
  parseRoleChange,
  parseStatusChange,
  refusalText,
  rolesFor,
} from "./admin";

const ID = "9b000000-0000-0000-0000-00000000000f";

function form(entries: Record<string, string>) {
  const f = new FormData();
  for (const [k, v] of Object.entries(entries)) f.append(k, v);
  return f;
}

describe("the roles an admin can give", () => {
  it("offers founder only to a person with a venture, and investor only with an investor profile", () => {
    expect(rolesFor("founder", { venture: true, investorProfile: false })).toEqual(["reviewer", "admin"]);
    expect(rolesFor("reviewer", { venture: true, investorProfile: false })).toEqual(["founder", "admin"]);
    expect(rolesFor("investor", { venture: false, investorProfile: true })).toEqual(["reviewer", "admin"]);
    expect(rolesFor("admin", { venture: false, investorProfile: false })).toEqual(["reviewer"]);
  });
});

describe("hiding a profile", () => {
  it("needs a reason of five to 280 characters, because the founder reads it", () => {
    expect(parseHold(form({ id: ID, reason: "no" })).ok).toBe(false);
    expect(parseHold(form({ id: ID, reason: "x".repeat(281) })).ok).toBe(false);
    const r = parseHold(form({ id: ID, reason: "  The revenue figure does not match.  " }));
    expect(r.ok && r.data.reason).toBe("The revenue figure does not match.");
  });
  it("refuses an id that is not a record id", () => {
    expect(parseHold(form({ id: "1 or 1=1", reason: "A real reason" })).ok).toBe(false);
  });
  it("lets the note on lifting a hold be empty", () => {
    const r = parseLift(form({ id: ID, note: "" }));
    expect(r.ok && r.data.note).toBe(null);
  });
});

describe("changing a role or status", () => {
  it("accepts the four roles an admin can give and nothing else", () => {
    expect(parseRoleChange(form({ id: ID, role: "reviewer", reason: "" })).ok).toBe(true);
    expect(parseRoleChange(form({ id: ID, role: "mentor", reason: "" })).ok).toBe(false);
  });
  it("needs a reason to suspend, and none to make an account active again", () => {
    expect(parseStatusChange(form({ id: ID, status: "suspended", reason: "" })).ok).toBe(false);
    expect(parseStatusChange(form({ id: ID, status: "suspended", reason: "Reported for spam." })).ok).toBe(true);
    expect(parseStatusChange(form({ id: ID, status: "active", reason: "" })).ok).toBe(true);
    expect(parseStatusChange(form({ id: ID, status: "pending", reason: "" })).ok).toBe(false);
  });
});

describe("the audit log", () => {
  it("names each action and links each record to its page", () => {
    expect(actionText("venture.hide")).toBe("hid a profile from investors");
    expect(actionText("something.new")).toBe("something.new");
    expect(entityHref("profiles", ID)).toBe(`/admin/people/${ID}`);
    expect(entityHref("ventures", ID)).toBe(`/admin/founders/${ID}`);
    expect(entityHref("evidence", ID)).toBe(`/admin/evidence/${ID}`);
    expect(entityHref("profiles", "not-an-id")).toBe(null);
  });
  it("describes what changed in words, and keeps the reason apart", () => {
    expect(changeLines({ status: "pending" }, { status: "active" })).toEqual(["Status: Waiting for approval to Active"]);
    expect(changeLines({ role: "founder", status: "active" }, { role: "reviewer", status: "active", reason: "Joins", profiles_hidden: 1 }))
      .toEqual(["Role: Founder to Reviewer"]);
    expect(changeLines({ published_at: "2026-10-17T10:00:00Z" }, { published_at: null, reason: "Misleading" }))
      .toEqual(["Published to investors: yes to no"]);
    expect(changeLines({ hidden_at: "2026-10-17T10:00:00Z", reason: "Misleading" }, { hidden_at: null, note: "Fixed" }))
      .toEqual(["Hold: on to off"]);
    expect(changeLines({ status: "submitted", lane: null }, { status: "needs_more", lane: null }))
      .toEqual(["Status: Waiting for review to More asked for"]);
    expect(changeLines({ status: "submitted", lane: null }, { status: "approved", lane: "human", public_note: "Compared" }))
      .toEqual(["Status: Waiting for review to Approved", "Checked by: none to an IkonetU reviewer", "Note for investors: none to Compared"]);
    expect(entryReason({ reason: "Misleading" })).toBe("Misleading");
    expect(entryReason({ note: "Corrected" })).toBe("Corrected");
    expect(entryReason({ status: "active" })).toBe(null);
  });
  it("turns the database's refusals into plain sentences", () => {
    expect(refusalText("nobody can change their own role")).toMatch(/your own role/);
    expect(refusalText("this person has no venture, so they cannot be a founder")).toMatch(/no venture/);
    expect(refusalText("connection reset")).toBe("The change was not saved. Please try again.");
  });
});
