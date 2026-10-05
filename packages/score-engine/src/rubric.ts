import type { Category, Lane, Rubric } from "./types";

/** Lane weights from the TRD. Self-declared claims earn nothing. */
export const LANE_WEIGHT: Record<Lane, number> = {
  government: 1.0,
  source: 0.95,
  ai: 0.85,
  human: 0.85,
  human_confirmed: 0.95,
  self: 0,
};

export const LEAGUE_THRESHOLDS = {
  RISING: 301,
  INVESTABLE: 601,
  ELITE: 851,
} as const;

/** A venture without approved company registration cannot score above this (PRD S-6). */
export const UNREGISTERED_CAP = 600;

/** The signal whose approval marks a venture as registered. */
export const REGISTRATION_SIGNAL = "company_registration";

export const CATEGORY_CAPS: Record<Category, number> = {
  identity: 100,
  legal: 100,
  financial: 200,
  product: 200,
  market: 100,
  team: 150,
  media: 100,
  operations: 50,
};

/**
 * Rubric v2, proposed defaults from the TRD (5 October 2026).
 * The values are mirrored into the rubric_signals table so admins can tune them;
 * any change here needs the matching migration and the tests updated.
 */
export const RUBRIC_V2: Rubric = {
  version: "v2",
  categoryCaps: CATEGORY_CAPS,
  signals: [
    // Identity (100)
    { code: "company_registration", category: "identity", label: "Company registration matched to the founder", mode: "fixed", points: 50, maxPoints: 50, expectedLane: "source" },
    { code: "government_id", category: "identity", label: "Government ID verified", mode: "fixed", points: 30, maxPoints: 30, expectedLane: "source" },
    { code: "operating_tenure", category: "identity", label: "Months operating", mode: "months", points: 1, maxPoints: 20, expectedLane: "ai" },

    // Legal (100)
    { code: "tax_registration", category: "legal", label: "Tax registration", mode: "fixed", points: 50, maxPoints: 50, expectedLane: "ai" },
    { code: "legal_documents", category: "legal", label: "Legal documents such as IP filings, contracts or licences", mode: "per_item", points: 10, maxPoints: 50, expectedLane: "ai" },

    // Financial (200)
    { code: "revenue", category: "financial", label: "Verified revenue, last 12 months", mode: "revenue", points: 1, usdPerPoint: 100, maxPoints: 80, expectedLane: "human" },
    { code: "financial_records", category: "financial", label: "Months of verified financial records", mode: "months", points: 4, maxPoints: 40, expectedLane: "ai" },
    { code: "business_account", category: "financial", label: "Verified business bank or mobile money account", mode: "fixed", points: 50, maxPoints: 50, expectedLane: "source" },
    { code: "financial_statements", category: "financial", label: "Verified financial statements", mode: "per_item", points: 10, maxPoints: 30, expectedLane: "ai" },

    // Product (200)
    { code: "product_stage", category: "product", label: "Product stage with evidence", mode: "stage", points: 0, maxPoints: 130, stagePoints: { idea: 0, mvp: 50, revenue: 90, scaling: 130 }, expectedLane: "ai" },
    { code: "customer_evidence", category: "product", label: "Customer evidence such as signed orders or usage data", mode: "per_item", points: 10, maxPoints: 70, expectedLane: "ai" },

    // Market (100)
    { code: "customer_interviews", category: "market", label: "Documented customer interviews", mode: "per_item", points: 5, maxPoints: 40, expectedLane: "ai" },
    { code: "pilot_letters", category: "market", label: "Signed pilot or intent letters", mode: "per_item", points: 10, maxPoints: 40, expectedLane: "ai" },
    { code: "market_research", category: "market", label: "Market research document", mode: "fixed", points: 20, maxPoints: 20, expectedLane: "ai" },

    // Team (150)
    { code: "team_members", category: "team", label: "Verified team members", mode: "per_item", points: 5, maxPoints: 40, expectedLane: "ai" },
    { code: "team_credentials", category: "team", label: "Verified team credentials", mode: "per_item", points: 15, maxPoints: 60, expectedLane: "ai" },
    { code: "student_status", category: "team", label: "Student or graduate status verified", mode: "fixed", points: 20, maxPoints: 20, expectedLane: "ai" },
    { code: "programme_completed", category: "team", label: "Recognised programme completed", mode: "per_item", points: 15, maxPoints: 30, expectedLane: "ai" },

    // Media (100)
    { code: "website_live", category: "media", label: "Live website, checked automatically", mode: "fixed", points: 20, maxPoints: 20, expectedLane: "source" },
    { code: "social_profile", category: "media", label: "Verified social profile", mode: "fixed", points: 20, maxPoints: 20, expectedLane: "ai" },
    { code: "pitch_deck", category: "media", label: "One-pager or pitch deck", mode: "fixed", points: 20, maxPoints: 20, expectedLane: "ai" },
    { code: "press_coverage", category: "media", label: "Verified press coverage", mode: "per_item", points: 10, maxPoints: 40, expectedLane: "ai" },

    // Operations (50)
    { code: "operational_evidence", category: "operations", label: "Operational evidence such as supplier contracts, premises or tools", mode: "per_item", points: 10, maxPoints: 50, expectedLane: "ai" },
  ],
};
