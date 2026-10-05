import { describe, expect, it } from "vitest";
import {
  CATEGORY_CAPS,
  RUBRIC_V2,
  UNREGISTERED_CAP,
  calculateScore,
  convertToUsd,
  isCountable,
  leagueFor,
  nextBestActions,
  type EvidenceItem,
} from "./index";

const NOW = new Date("2026-10-05T12:00:00Z");
let seq = 0;
const ev = (partial: Partial<EvidenceItem> & Pick<EvidenceItem, "signalCode">): EvidenceItem => ({
  id: `e${++seq}`,
  status: "approved",
  lane: "ai",
  ...partial,
});
const score = (evidence: EvidenceItem[]) => calculateScore({ evidence, rubric: RUBRIC_V2, now: NOW });
const signal = (r: ReturnType<typeof score>, code: string) => r.signals.find((s) => s.code === code)!;
const category = (r: ReturnType<typeof score>, c: string) => r.categories.find((x) => x.category === c)!;

describe("rubric v2", () => {
  it("category caps add up to 1000", () => {
    expect(Object.values(CATEGORY_CAPS).reduce((a, b) => a + b, 0)).toBe(1000);
  });

  it("every category can be filled by its signals", () => {
    for (const [cat, cap] of Object.entries(CATEGORY_CAPS)) {
      const max = RUBRIC_V2.signals.filter((s) => s.category === cat).reduce((a, s) => a + s.maxPoints, 0);
      expect(max, cat).toBeGreaterThanOrEqual(cap);
    }
  });

  it("signal codes are unique", () => {
    const codes = RUBRIC_V2.signals.map((s) => s.code);
    expect(new Set(codes).size).toBe(codes.length);
  });
});

describe("leagueFor boundaries", () => {
  it.each([
    [0, "EARLY"],
    [300, "EARLY"],
    [301, "RISING"],
    [600, "RISING"],
    [601, "INVESTABLE"],
    [850, "INVESTABLE"],
    [851, "ELITE"],
    [1000, "ELITE"],
  ] as const)("%i is %s", (total, league) => {
    expect(leagueFor(total)).toBe(league);
  });
});

describe("what counts", () => {
  it("an empty profile scores 0 in Early", () => {
    const r = score([]);
    expect(r.total).toBe(0);
    expect(r.league).toBe("EARLY");
  });

  it("self-declared claims earn nothing", () => {
    expect(score([ev({ signalCode: "tax_registration", lane: "self" })]).total).toBe(0);
  });

  it.each(["submitted", "checking", "needs_review", "needs_more", "rejected", "expired"] as const)(
    "%s evidence earns nothing",
    (status) => {
      expect(score([ev({ signalCode: "tax_registration", status })]).total).toBe(0);
    },
  );

  it("expired evidence stops counting on its expiry date", () => {
    expect(isCountable(ev({ signalCode: "government_id", expiresAt: "2026-10-05T12:00:00Z" }), NOW)).toBe(false);
    expect(isCountable(ev({ signalCode: "government_id", expiresAt: "2026-10-06T00:00:00Z" }), NOW)).toBe(true);
  });

  it("an unparseable expiry date does not count", () => {
    expect(isCountable(ev({ signalCode: "government_id", expiresAt: "not a date" }), NOW)).toBe(false);
  });

  it("unknown signal codes are ignored", () => {
    expect(score([ev({ signalCode: "google_maps_listing", lane: "source" })]).total).toBe(0);
  });
});

describe("lane weights", () => {
  it.each([
    ["government", 50],
    ["source", 47],
    ["human_confirmed", 47],
    ["ai", 42],
    ["human", 42],
  ] as const)("tax registration through %s earns %i", (lane, points) => {
    expect(score([ev({ signalCode: "tax_registration", lane })]).total).toBe(points);
  });
});

describe("signal modes and caps", () => {
  it("fixed signals count the best single item only", () => {
    const r = score([
      ev({ signalCode: "government_id", lane: "ai" }),
      ev({ signalCode: "government_id", lane: "source" }),
    ]);
    expect(signal(r, "government_id").capped).toBe(28.5);
  });

  it("per-item signals add up across submissions and stop at the cap", () => {
    const r = score([
      ev({ signalCode: "customer_evidence", itemCount: 3 }),
      ev({ signalCode: "customer_evidence", itemCount: 2 }),
    ]);
    expect(signal(r, "customer_evidence").capped).toBe(42.5);

    const capped = score([ev({ signalCode: "customer_evidence", itemCount: 20 })]);
    expect(signal(capped, "customer_evidence").weighted).toBe(170);
    expect(signal(capped, "customer_evidence").capped).toBe(70);
  });

  it("per-item evidence without a count counts as one item", () => {
    expect(signal(score([ev({ signalCode: "press_coverage" })]), "press_coverage").capped).toBe(8.5);
  });

  it("revenue earns 1 point per USD 100 up to 80", () => {
    expect(signal(score([ev({ signalCode: "revenue", lane: "human", revenueUsd: 4_250 })]), "revenue").capped).toBe(35.7);
    expect(signal(score([ev({ signalCode: "revenue", lane: "human", revenueUsd: 50_000 })]), "revenue").capped).toBe(80);
  });

  it("revenue counts the best item, not the sum", () => {
    const r = score([
      ev({ signalCode: "revenue", lane: "human", revenueUsd: 2_000 }),
      ev({ signalCode: "revenue", lane: "human", revenueUsd: 3_000 }),
    ]);
    expect(signal(r, "revenue").capped).toBe(25.5);
  });

  it("months signals use the best item", () => {
    const r = score([
      ev({ signalCode: "financial_records", months: 6 }),
      ev({ signalCode: "financial_records", months: 9 }),
    ]);
    expect(signal(r, "financial_records").capped).toBe(30.6);
  });

  it("product stage uses the stage points table", () => {
    expect(signal(score([ev({ signalCode: "product_stage", stage: "idea" })]), "product_stage").capped).toBe(0);
    expect(signal(score([ev({ signalCode: "product_stage", stage: "mvp" })]), "product_stage").capped).toBe(42.5);
    expect(signal(score([ev({ signalCode: "product_stage", stage: "scaling", lane: "government" })]), "product_stage").capped).toBe(130);
  });

  it("categories stop at their cap", () => {
    const r = score([
      ev({ signalCode: "customer_interviews", itemCount: 20, lane: "government" }),
      ev({ signalCode: "pilot_letters", itemCount: 10, lane: "government" }),
      ev({ signalCode: "market_research", lane: "government" }),
    ]);
    expect(category(r, "market").uncapped).toBe(100);
    expect(category(r, "market").earned).toBe(100);
  });
});

describe("registration and the unregistered cap", () => {
  const strongUnregistered: EvidenceItem[] = [
    ev({ signalCode: "government_id", lane: "government" }),
    ev({ signalCode: "operating_tenure", months: 30, lane: "government" }),
    ev({ signalCode: "tax_registration", lane: "government" }),
    ev({ signalCode: "legal_documents", itemCount: 5, lane: "government" }),
    ev({ signalCode: "revenue", revenueUsd: 100_000, lane: "government" }),
    ev({ signalCode: "financial_records", months: 12, lane: "government" }),
    ev({ signalCode: "business_account", lane: "government" }),
    ev({ signalCode: "product_stage", stage: "scaling", lane: "government" }),
    ev({ signalCode: "customer_evidence", itemCount: 7, lane: "government" }),
    ev({ signalCode: "team_members", itemCount: 8, lane: "government" }),
    ev({ signalCode: "team_credentials", itemCount: 4, lane: "government" }),
    ev({ signalCode: "website_live", lane: "government" }),
    ev({ signalCode: "pitch_deck", lane: "government" }),
  ];

  it("caps an unregistered venture at 600, the top of Rising", () => {
    const r = score(strongUnregistered);
    expect(r.isRegistered).toBe(false);
    expect(r.unregisteredCapApplied).toBe(true);
    expect(r.total).toBe(UNREGISTERED_CAP);
    expect(r.league).toBe("RISING");
  });

  it("lifts the cap once registration is approved", () => {
    const r = score([...strongUnregistered, ev({ signalCode: "company_registration", lane: "source" })]);
    expect(r.isRegistered).toBe(true);
    expect(r.unregisteredCapApplied).toBe(false);
    expect(r.total).toBeGreaterThan(UNREGISTERED_CAP);
    expect(r.league).toBe("INVESTABLE");
  });

  it("does not treat registration under review as registered", () => {
    const r = score([ev({ signalCode: "company_registration", status: "needs_review" })]);
    expect(r.isRegistered).toBe(false);
  });
});

describe("maximum score", () => {
  it("reaches exactly 1000 only when everything is verified at government level", () => {
    const all = RUBRIC_V2.signals.map((s) =>
      ev({
        signalCode: s.code,
        lane: "government",
        itemCount: 100,
        months: 100,
        revenueUsd: 1_000_000,
        stage: "scaling",
      }),
    );
    const r = score(all);
    expect(r.total).toBe(1000);
    expect(r.league).toBe("ELITE");
  });

  it("stays below 1000 when the best evidence comes through source checks", () => {
    const all = RUBRIC_V2.signals.map((s) =>
      ev({ signalCode: s.code, lane: "source", itemCount: 100, months: 100, revenueUsd: 1_000_000, stage: "scaling" }),
    );
    expect(score(all).total).toBeLessThan(1000);
  });
});

describe("worked example from the screens", () => {
  it("adds up the founder home example's quick wins", () => {
    // Rubric v2 points as shown on the Founder home and Assessment screens.
    expect(score([ev({ signalCode: "company_registration", lane: "source" })]).total).toBe(47);
    expect(score([ev({ signalCode: "business_account", lane: "source" })]).total).toBe(47);
    expect(score([ev({ signalCode: "customer_evidence", itemCount: 2 })]).total).toBe(17);
    expect(score([ev({ signalCode: "website_live", lane: "source" })]).total).toBe(19);
    expect(score([ev({ signalCode: "student_status" })]).total).toBe(17);
  });
});

describe("convertToUsd", () => {
  it("converts with the stated rate and rounds to cents", () => {
    expect(convertToUsd(1_140_000, 0.0077)).toBe(8778);
  });

  it("rejects a missing or non-positive rate", () => {
    expect(() => convertToUsd(100, 0)).toThrow();
    expect(() => convertToUsd(Number.NaN, 0.01)).toThrow();
  });
});

describe("nextBestActions", () => {
  it("puts the largest quick wins first for an empty profile", () => {
    const actions = nextBestActions(score([]), RUBRIC_V2, 3);
    expect(actions.map((a) => a.code)).toEqual(["business_account", "company_registration", "product_stage"]);
    expect(actions[0]!.estimatedGain).toBe(47);
  });

  it("drops signals that are already full", () => {
    const r = score([ev({ signalCode: "company_registration", lane: "government" })]);
    expect(nextBestActions(r, RUBRIC_V2, 50).some((a) => a.code === "company_registration")).toBe(false);
  });

  it("respects the room left in a category", () => {
    const r = score([
      ev({ signalCode: "customer_interviews", itemCount: 8, lane: "government" }),
      ev({ signalCode: "pilot_letters", itemCount: 4, lane: "government" }),
      ev({ signalCode: "market_research", lane: "government" }),
    ]);
    expect(nextBestActions(r, RUBRIC_V2, 50).some((a) => a.category === "market")).toBe(false);
  });
});
