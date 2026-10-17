import { describe, expect, it } from "vitest";
import { nextSteps } from "./next-steps";

const row = (signal_code: string, status: string, lane: string | null = null) => ({
  id: signal_code, signal_code, status, lane, expires_at: null, item_count: null, months: null, revenue_usd: null, stage: null,
});

describe("next steps", () => {
  it("gives three steps to a founder with no evidence", () => {
    const steps = nextSteps([]);
    expect(steps).toHaveLength(3);
    expect(new Set(steps.map((s) => s.code)).size).toBe(3);
  });
  it("leaves out evidence already waiting for a reviewer", () => {
    const first = nextSteps([])[0]!;
    const after = nextSteps([row(first.code, "submitted")]);
    expect(after.map((s) => s.code)).not.toContain(first.code);
  });
  it("leaves out a fixed signal that is already approved", () => {
    const steps = nextSteps([row("company_registration", "approved", "government")], 30);
    expect(steps.map((s) => s.code)).not.toContain("company_registration");
  });
});
