import type { Category } from "@ikonetu/score-engine";
import { INTEREST_SECTORS } from "./investor-interest";

/** The sectors a venture and an investor choose from. Discovery filters on them. */
export const SECTORS = INTEREST_SECTORS;
export type Sector = (typeof SECTORS)[number];

/** The eight areas of evidence, in the order of the score engine's rubric. */
export const AREAS: { code: Category; label: string }[] = [
  { code: "identity", label: "Identity" },
  { code: "legal", label: "Legal" },
  { code: "financial", label: "Financial" },
  { code: "product", label: "Product" },
  { code: "market", label: "Market" },
  { code: "team", label: "Team" },
  { code: "media", label: "Media and presence" },
  { code: "operations", label: "Operations" },
];

export function areaLabel(code: string): string {
  return AREAS.find((a) => a.code === code)?.label ?? code;
}

/**
 * The three statuses an investor sees. The database decides which one applies
 * (venture_evidence and discover_ventures): third_party for evidence approved
 * from a registry or other outside source, reviewed for evidence an IkonetU
 * reviewer approved, and submitted for evidence nobody has decided yet.
 */
export type ShownStatus = "third_party" | "reviewed" | "submitted";

export const STATUS: Record<ShownStatus, { name: string; chip: string; icon: "link" | "shield-check" | "upload"; means: string }> = {
  third_party: {
    name: "Third-party evidence available",
    chip: "chip-io",
    icon: "link",
    means: "An outside source backs it. The outside source has not assessed the company.",
  },
  reviewed: {
    name: "Platform reviewed",
    chip: "chip-i",
    icon: "shield-check",
    means: "An IkonetU reviewer compared it with its source. A review is not an audit, a valuation or an endorsement.",
  },
  submitted: {
    name: "Founder submitted",
    chip: "chip-n",
    icon: "upload",
    means: "IkonetU has not checked it. Treat it as the founder's own statement.",
  },
};

export function isShownStatus(v: unknown): v is ShownStatus {
  return v === "third_party" || v === "reviewed" || v === "submitted";
}

export type AreaSummary = { category: string; status: ShownStatus; count: number };

/** One cell per area for the card's meter, with the best status in that area or none. */
export function areaCells(areas: AreaSummary[]): { code: Category; label: string; status: ShownStatus | null; count: number }[] {
  return AREAS.map((a) => {
    const found = areas.find((x) => x.category === a.code);
    return { code: a.code, label: a.label, status: found ? found.status : null, count: found ? found.count : 0 };
  });
}

/** A one-line summary of the meter, so the cells are never the only way to read it. */
export function areaSummaryText(areas: AreaSummary[]): string {
  const withEvidence = areas.length;
  if (withEvidence === 0) return "No evidence added yet.";
  const reviewed = areas.filter((a) => a.status === "reviewed").length;
  const third = areas.filter((a) => a.status === "third_party").length;
  const parts = [`Evidence in ${withEvidence} of 8 areas.`];
  const checked: string[] = [];
  if (third) checked.push(`${third} with third-party evidence`);
  if (reviewed) checked.push(`${reviewed} platform reviewed`);
  if (checked.length) parts.push(`${sentenceCase(checked.join(", "))}.`);
  else parts.push("None reviewed yet.");
  return parts.join(" ");
}

function sentenceCase(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

const DAY = 24 * 60 * 60 * 1000;

/** Whole days between two moments, counted in UTC calendar days. */
export function daysBetween(then: Date, now: Date): number {
  const a = Date.UTC(then.getUTCFullYear(), then.getUTCMonth(), then.getUTCDate());
  const b = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate());
  return Math.max(0, Math.round((b - a) / DAY));
}

/** "Updated today", "Updated yesterday" or "Updated 9 days ago". */
export function activityText(last: string | null | undefined, now: Date): string {
  if (!last) return "No activity yet";
  const d = daysBetween(new Date(last), now);
  if (d === 0) return "Updated today";
  if (d === 1) return "Updated yesterday";
  return `Updated ${d} days ago`;
}

export function isRecent(last: string | null | undefined, now: Date, days = 30): boolean {
  return Boolean(last) && daysBetween(new Date(last as string), now) <= days;
}

/** A pitch length as m:ss, for example 0:58. */
export function clockText(seconds: number | null | undefined): string {
  const s = Math.max(0, Math.round(Number(seconds) || 0));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

/** A date as 15 October 2026, in UK English. */
export function dateText(iso: string | null | undefined): string {
  if (!iso) return "";
  return new Date(iso).toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric", timeZone: "UTC" });
}

export const INVESTOR_TYPE_NAME: Record<string, string> = {
  individual: "Individual investor",
  angel: "Angel investor",
  fund: "Fund investor",
};
