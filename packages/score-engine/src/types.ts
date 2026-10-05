export type Category =
  | "identity"
  | "legal"
  | "financial"
  | "product"
  | "market"
  | "team"
  | "media"
  | "operations";

export type League = "EARLY" | "RISING" | "INVESTABLE" | "ELITE";

/**
 * How a piece of evidence was verified (TRD, Score engine rule 2).
 * self = a claim with no approved evidence; it earns nothing (PRD E-6).
 */
export type Lane = "government" | "source" | "ai" | "human" | "human_confirmed" | "self";

export type EvidenceStatus =
  | "submitted"
  | "checking"
  | "needs_review"
  | "needs_more"
  | "approved"
  | "rejected"
  | "expired";

export type ProductStage = "idea" | "mvp" | "revenue" | "scaling";

/**
 * How a signal turns evidence into points.
 * fixed: one item earns `points` (best item counts).
 * per_item: each verified item earns `points`, summed up to `maxPoints`.
 * months: `points` per verified month, best item counts, up to `maxPoints`.
 * revenue: 1 point per `usdPerPoint` US dollars, best item counts, up to `maxPoints`.
 * stage: points looked up from `stagePoints`, best item counts.
 */
export type SignalMode = "fixed" | "per_item" | "months" | "revenue" | "stage";

export interface SignalDef {
  code: string;
  category: Category;
  label: string;
  mode: SignalMode;
  points: number;
  maxPoints: number;
  usdPerPoint?: number;
  stagePoints?: Partial<Record<ProductStage, number>>;
  /** Lane a founder is most likely to get, used to estimate next best actions. */
  expectedLane: Lane;
}

export interface Rubric {
  version: string;
  categoryCaps: Record<Category, number>;
  signals: SignalDef[];
}

export interface EvidenceItem {
  id: string;
  signalCode: string;
  status: EvidenceStatus;
  lane: Lane;
  /** ISO date; evidence past this date no longer counts. */
  expiresAt?: string | null;
  /** per_item: number of verified items in this submission. */
  itemCount?: number;
  /** months: number of verified months. */
  months?: number;
  /** revenue: verified revenue over the last 12 months, already converted to USD. */
  revenueUsd?: number;
  /** stage: verified product stage. */
  stage?: ProductStage;
}

export interface SignalResult {
  code: string;
  category: Category;
  weighted: number;
  capped: number;
  maxPoints: number;
  evidenceIds: string[];
}

export interface CategoryResult {
  category: Category;
  earned: number;
  cap: number;
  uncapped: number;
}

export interface ScoreResult {
  rubricVersion: string;
  total: number;
  league: League;
  isRegistered: boolean;
  unregisteredCapApplied: boolean;
  categories: CategoryResult[];
  signals: SignalResult[];
}
