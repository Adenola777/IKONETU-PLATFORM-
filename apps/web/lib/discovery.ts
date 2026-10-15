import { STAGES } from "./account";
import { COUNTRIES } from "./constants";
import { SECTORS } from "./product";

/**
 * The discovery filters. Choices inside one group widen the list and choices
 * across groups narrow it, as the For investors page says. The database does
 * the filtering (discover_ventures); this module reads and writes the query
 * string, so a filtered list has its own address and works without script.
 */
export type FilterKey = "sector" | "stage" | "country" | "evidence";
export type Filters = Record<FilterKey, string[]> & { activity: "" | "30" | "90"; page: number };

export const FILTER_GROUPS: { key: FilterKey; label: string; options: { value: string; label: string }[] }[] = [
  { key: "sector", label: "Sector", options: SECTORS.map((s) => ({ value: s, label: s })) },
  { key: "stage", label: "Stage", options: STAGES.map((s) => ({ value: s.code, label: s.label })) },
  { key: "country", label: "Geography", options: COUNTRIES.map((c) => ({ value: c.code, label: c.name })) },
  {
    key: "evidence",
    label: "Evidence",
    options: [
      { value: "revenue_reviewed", label: "Revenue reviewed" },
      { value: "registry_record", label: "Registry record" },
      { value: "any_reviewed", label: "Any reviewed evidence" },
    ],
  },
];

export const ACTIVITY_OPTIONS = [
  { value: "", label: "Any time" },
  { value: "30", label: "In the last 30 days" },
  { value: "90", label: "In the last 90 days" },
] as const;

export const PAGE_SIZE = 24;

type Params = Record<string, string | string[] | undefined>;

function list(v: string | string[] | undefined): string[] {
  if (v === undefined) return [];
  return (Array.isArray(v) ? v : [v]).flatMap((x) => x.split(",")).map((x) => x.trim()).filter(Boolean);
}

/** Reads the filters from the query string. Unknown values are dropped. */
export function parseFilters(params: Params): Filters {
  const out = { sector: [], stage: [], country: [], evidence: [], activity: "", page: 1 } as Filters;
  for (const g of FILTER_GROUPS) {
    const allowed = new Set(g.options.map((o) => o.value));
    out[g.key] = [...new Set(list(params[g.key]).filter((v) => allowed.has(v)))];
  }
  const activity = list(params.activity)[0] ?? "";
  out.activity = activity === "30" || activity === "90" ? activity : "";
  const page = Number(list(params.page)[0]);
  out.page = Number.isInteger(page) && page > 1 && page < 1000 ? page : 1;
  return out;
}

/** The arguments discover_ventures takes. An empty group means no filter. */
export function rpcArgs(f: Filters) {
  const orNull = (v: string[]) => (v.length ? v : null);
  return {
    p_sectors: orNull(f.sector),
    p_stages: orNull(f.stage),
    p_countries: orNull(f.country),
    p_evidence: orNull(f.evidence),
    p_active_days: f.activity ? Number(f.activity) : null,
    p_limit: PAGE_SIZE,
    p_offset: (f.page - 1) * PAGE_SIZE,
  };
}

/** The query string for a set of filters, without the page unless asked. */
export function queryString(f: Filters, page = 1): string {
  const q = new URLSearchParams();
  for (const g of FILTER_GROUPS) for (const v of f[g.key]) q.append(g.key, v);
  if (f.activity) q.set("activity", f.activity);
  if (page > 1) q.set("page", String(page));
  const s = q.toString();
  return s ? `?${s}` : "";
}

export function filterCount(f: Filters): number {
  return FILTER_GROUPS.reduce((n, g) => n + f[g.key].length, 0) + (f.activity ? 1 : 0);
}

export function matchText(total: number, filtered: boolean): string {
  const noun = total === 1 ? "founder" : "founders";
  const verb = filtered ? (total === 1 ? "matches" : "match") : total === 1 ? "is" : "are";
  return filtered
    ? `${total} ${noun} ${verb} these filters. Sorted by company name.`
    : `${total} ${noun} ${verb} on IkonetU. Sorted by company name.`;
}
