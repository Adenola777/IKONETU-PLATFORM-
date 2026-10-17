import type { Category } from "@ikonetu/score-engine";
import { INTEREST_SECTORS } from "./investor-options";

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

/**
 * The readiness check, the same on the website and in the app. An area is
 * strong when it holds platform-reviewed or third-party evidence, building
 * when it holds founder-submitted evidence only, and a gap when it holds none.
 * The owner set this on 15 October 2026.
 */
export type Level = "strong" | "building" | "gap";

export const LEVEL: Record<Level, { name: string; chip: string; means: string }> = {
  strong: { name: "Strong", chip: "chip-i", means: "Platform-reviewed or third-party evidence" },
  building: { name: "Building", chip: "chip-n", means: "Founder-submitted evidence only" },
  gap: { name: "Gap", chip: "chip-none", means: "No evidence yet" },
};

export function levelOf(status: ShownStatus | null | undefined): Level {
  if (status === "third_party" || status === "reviewed") return "strong";
  if (status === "submitted") return "building";
  return "gap";
}

/** One entry per area, in rubric order, with its level and how many pieces of evidence it holds. */
export function areaCells(areas: AreaSummary[]): { code: Category; label: string; level: Level; count: number }[] {
  return AREAS.map((a) => {
    const found = areas.find((x) => x.category === a.code);
    return { code: a.code, label: a.label, level: levelOf(found?.status), count: found ? found.count : 0 };
  });
}

/** The readiness check in words, so the meter's colours are never the only signal. */
export function readinessText(areas: AreaSummary[]): string {
  const cells = areaCells(areas);
  const n = (l: Level) => cells.filter((c) => c.level === l).length;
  if (n("gap") === 8) return "No evidence yet, so all eight areas are gaps.";
  return `Strong in ${n("strong")} of 8 areas, building in ${n("building")}, with a gap in ${n("gap")}.`;
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

/**
 * Why each area matters to an investor. The founder's next steps and the
 * public readiness self-check use the same sentences.
 */
export const AREA_WHY: Record<Category, string> = {
  identity: "Investors want to know the company exists and who stands behind it.",
  legal: "A company that can trade legally carries less risk.",
  financial: "Recorded numbers can be reviewed. Remembered numbers cannot.",
  product: "A product investors can try is easier to believe than a description.",
  market: "Investors want to know the problem exists before they look at the solution.",
  team: "Investors back people, so they want to see who is building the company.",
  media: "A public presence lets investors check what the founder says.",
  operations: "Operational evidence shows the business can deliver.",
};

/**
 * The evidence a founder added in the last 90 days, counted, with the number
 * of areas it falls in, for example "7 pieces in 90 days, in 7 of 8 areas".
 */
export function evidenceAddedText(items: { category: string; createdAt: string }[], now: Date): string {
  const recent = items.filter((e) => daysBetween(new Date(e.createdAt), now) <= 90);
  if (recent.length === 0) return "None in 90 days";
  const areas = new Set(recent.map((e) => e.category)).size;
  return `${recent.length} ${recent.length === 1 ? "piece" : "pieces"} in 90 days, in ${areas} of 8 areas`;
}

/**
 * Momentum, as the website describes it: recency, consistency and evidence
 * added. Consistency counts progress updates in the last 90 days, and the
 * strip marks each of the last 13 weeks that had an update. There are no
 * streaks, points or ranks.
 */
export function momentum(updateDates: string[], now: Date) {
  const day = (d: string) => daysBetween(new Date(d), now);
  const in90 = updateDates.filter((d) => day(d) <= 90).length;
  const weeks = Array.from({ length: 13 }, (_, i) => {
    const ago = 12 - i;
    return { ago, active: updateDates.some((d) => Math.floor(day(d) / 7) === ago) };
  });
  return {
    in90,
    consistencyText: in90 === 0 ? "No updates in 90 days" : `${in90} ${in90 === 1 ? "update" : "updates"} in 90 days`,
    weeks,
    activeWeeks: weeks.filter((w) => w.active).length,
  };
}
