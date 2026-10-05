import {
  LANE_WEIGHT,
  LEAGUE_THRESHOLDS,
  REGISTRATION_SIGNAL,
  UNREGISTERED_CAP,
} from "./rubric";
import type {
  Category,
  CategoryResult,
  EvidenceItem,
  League,
  Rubric,
  ScoreResult,
  SignalDef,
  SignalResult,
} from "./types";

const EPSILON = 1e-9;

const round2 = (n: number): number => Math.round(n * 100) / 100;

/** Maps a total to a league: Early 0–300, Rising 301–600, Investable 601–850, Elite 851–1000. */
export function leagueFor(total: number): League {
  if (total >= LEAGUE_THRESHOLDS.ELITE) return "ELITE";
  if (total >= LEAGUE_THRESHOLDS.INVESTABLE) return "INVESTABLE";
  if (total >= LEAGUE_THRESHOLDS.RISING) return "RISING";
  return "EARLY";
}

/** True when the evidence counts towards the Score at `now` (approved, verified, unexpired). */
export function isCountable(item: EvidenceItem, now: Date): boolean {
  if (item.status !== "approved") return false;
  if (LANE_WEIGHT[item.lane] <= 0) return false;
  if (item.expiresAt) {
    const expires = new Date(item.expiresAt);
    if (Number.isNaN(expires.getTime())) return false;
    if (expires.getTime() <= now.getTime()) return false;
  }
  return true;
}

/** Points one evidence item earns for its signal before the signal cap, already lane-weighted. */
function weightedPoints(def: SignalDef, item: EvidenceItem): number {
  const w = LANE_WEIGHT[item.lane];
  switch (def.mode) {
    case "fixed":
      return def.points * w;
    case "per_item":
      return Math.max(0, Math.floor(item.itemCount ?? 1)) * def.points * w;
    case "months":
      return Math.max(0, Math.floor(item.months ?? 0)) * def.points * w;
    case "revenue": {
      const perPoint = def.usdPerPoint ?? 100;
      const usd = Math.max(0, item.revenueUsd ?? 0);
      return Math.floor(usd / perPoint) * def.points * w;
    }
    case "stage":
      return (item.stage ? def.stagePoints?.[item.stage] ?? 0 : 0) * w;
  }
}

/** per_item evidence adds up; every other mode counts the single best item. */
function combine(def: SignalDef, values: number[]): number {
  if (values.length === 0) return 0;
  if (def.mode === "per_item") return values.reduce((a, b) => a + b, 0);
  return Math.max(...values);
}

export interface CalculateInput {
  evidence: EvidenceItem[];
  rubric: Rubric;
  now?: Date;
}

/**
 * Calculates the IkonetU Score from approved evidence only (PRD S-1).
 * Rules follow the TRD: lane weight, then signal cap, then category cap,
 * then the unregistered cap of 600, then the total is rounded down.
 */
export function calculateScore({ evidence, rubric, now = new Date() }: CalculateInput): ScoreResult {
  const countable = evidence.filter((e) => isCountable(e, now));
  const defs = new Map(rubric.signals.map((s) => [s.code, s]));

  const signals: SignalResult[] = rubric.signals.map((def) => {
    const items = countable.filter((e) => e.signalCode === def.code);
    const weighted = combine(def, items.map((i) => weightedPoints(def, i)));
    return {
      code: def.code,
      category: def.category,
      weighted: round2(weighted),
      capped: round2(Math.min(weighted, def.maxPoints)),
      maxPoints: def.maxPoints,
      evidenceIds: items.map((i) => i.id),
    };
  });

  const categoryOrder = Object.keys(rubric.categoryCaps) as Category[];
  const categories: CategoryResult[] = categoryOrder.map((category) => {
    const uncapped = signals
      .filter((s) => s.category === category)
      .reduce((sum, s) => sum + s.capped, 0);
    const cap = rubric.categoryCaps[category];
    return { category, uncapped: round2(uncapped), cap, earned: round2(Math.min(uncapped, cap)) };
  });

  const isRegistered = countable.some(
    (e) => e.signalCode === REGISTRATION_SIGNAL && defs.has(REGISTRATION_SIGNAL),
  );

  let total = Math.floor(categories.reduce((sum, c) => sum + c.earned, 0) + EPSILON);
  let unregisteredCapApplied = false;
  if (!isRegistered && total > UNREGISTERED_CAP) {
    total = UNREGISTERED_CAP;
    unregisteredCapApplied = true;
  }

  return {
    rubricVersion: rubric.version,
    total,
    league: leagueFor(total),
    isRegistered,
    unregisteredCapApplied,
    categories,
    signals,
  };
}

/**
 * Converts revenue in a local currency to US dollars using one stated rate
 * (TRD rule 4). `usdPerUnit` is the value of one unit of the local currency in USD
 * on the evidence date; the caller stores the rate with the result.
 */
export function convertToUsd(amount: number, usdPerUnit: number): number {
  if (!Number.isFinite(amount) || !Number.isFinite(usdPerUnit) || usdPerUnit <= 0) {
    throw new Error("convertToUsd needs a finite amount and a positive rate");
  }
  return round2(amount * usdPerUnit);
}

export interface NextAction {
  code: string;
  label: string;
  category: Category;
  estimatedGain: number;
}

/**
 * Suggests the evidence that would add the most points next (PRD P-3, O-4),
 * using each signal's expected lane and the room left under signal and category caps.
 */
export function nextBestActions(result: ScoreResult, rubric: Rubric, limit = 5): NextAction[] {
  const roomByCategory = new Map(result.categories.map((c) => [c.category, c.cap - c.earned]));
  const bySignal = new Map(result.signals.map((s) => [s.code, s]));

  const actions: NextAction[] = [];
  for (const def of rubric.signals) {
    const current = bySignal.get(def.code)?.capped ?? 0;
    const w = LANE_WEIGHT[def.expectedLane];
    let step: number;
    switch (def.mode) {
      case "fixed":
        step = def.points * w - current;
        break;
      case "per_item":
        step = def.points * w;
        break;
      case "months":
        step = def.points * 3 * w;
        break;
      case "revenue":
        step = 10 * def.points * w;
        break;
      case "stage": {
        const values = Object.values(def.stagePoints ?? {}).sort((a, b) => a - b);
        const next = values.find((v) => v * w > current + EPSILON);
        step = next === undefined ? 0 : next * w - current;
        break;
      }
    }
    const room = Math.min(def.maxPoints - current, roomByCategory.get(def.category) ?? 0);
    const gain = Math.floor(Math.min(step, room) + EPSILON);
    if (gain > 0) actions.push({ code: def.code, label: def.label, category: def.category, estimatedGain: gain });
  }

  return actions.sort((a, b) => b.estimatedGain - a.estimatedGain || a.code.localeCompare(b.code)).slice(0, limit);
}
