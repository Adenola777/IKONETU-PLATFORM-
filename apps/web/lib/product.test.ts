import { describe, expect, it } from "vitest";
import { cuesFromTranscript, captionChunks } from "./captions";
import { FILTER_GROUPS, filterCount, matchText, parseFilters, queryString, rpcArgs, PAGE_SIZE } from "./discovery";
import { activityText, AREA_WHY, AREAS, areaCells, clockText, dateText, evidenceAddedText, isRecent, levelOf, momentum, readinessText } from "./product";

const NOW = new Date("2026-10-15T12:00:00Z");

describe("activity and dates", () => {
  it("counts whole days", () => {
    expect(activityText("2026-10-15T01:00:00Z", NOW)).toBe("Updated today");
    expect(activityText("2026-10-14T23:59:00Z", NOW)).toBe("Updated yesterday");
    expect(activityText("2026-10-06T12:00:00Z", NOW)).toBe("Updated 9 days ago");
    expect(activityText(null, NOW)).toBe("No activity yet");
  });
  it("calls 30 days recent and 31 days not", () => {
    expect(isRecent("2026-09-15T12:00:00Z", NOW)).toBe(true);
    expect(isRecent("2026-09-14T12:00:00Z", NOW)).toBe(false);
  });
  it("writes a pitch length and a UK date", () => {
    expect(clockText(58.4)).toBe("0:58");
    expect(clockText(90)).toBe("1:30");
    expect(dateText("2026-10-15T00:00:00Z")).toBe("15 October 2026");
  });
});

describe("evidence by area", () => {
  const areas = [
    { category: "financial", status: "reviewed" as const, count: 2 },
    { category: "identity", status: "third_party" as const, count: 1 },
    { category: "team", status: "submitted" as const, count: 1 },
  ];
  it("gives one cell per area in rubric order", () => {
    const cells = areaCells(areas);
    expect(cells.map((c) => c.code)).toEqual(["identity", "legal", "financial", "product", "market", "team", "media", "operations"]);
    expect(cells[0]?.level).toBe("strong");
    expect(cells[1]?.level).toBe("gap");
    expect(cells[2]?.count).toBe(2);
    expect(cells[5]?.level).toBe("building");
  });
  it("says the readiness check in words", () => {
    expect(readinessText(areas)).toBe("Strong in 2 of 8 areas, building in 1, with a gap in 5.");
    expect(readinessText([])).toBe("No evidence yet, so all eight areas are gaps.");
  });
  it("calls an area strong only with reviewed or third-party evidence", () => {
    expect(levelOf("third_party")).toBe("strong");
    expect(levelOf("reviewed")).toBe("strong");
    expect(levelOf("submitted")).toBe("building");
    expect(levelOf(null)).toBe("gap");
  });
});

describe("captions from a transcript", () => {
  it("splits sentences and long sentences at word breaks", () => {
    const long = "We help traders in Lagos markets take card payments on a phone they already own without buying a terminal or opening a new bank account.";
    const chunks = captionChunks(`Hello. ${long}`);
    expect(chunks[0]).toBe("Hello.");
    expect(chunks.slice(1).join(" ")).toBe(long);
    expect(chunks.every((c) => c.length <= 84)).toBe(true);
  });
  it("shares the length out and ends at the end", () => {
    const cues = cuesFromTranscript("One two three. Four five six seven eight nine.", 10);
    expect(cues).toHaveLength(2);
    expect(cues[0]?.start).toBe(0);
    expect(cues[0]?.end).toBe(cues[1]?.start);
    expect(cues[1]?.end).toBe(10);
    expect((cues[0]?.end ?? 0) < (cues[1]?.end ?? 0) - (cues[1]?.start ?? 0)).toBe(true);
  });
  it("makes nothing from an empty transcript or a zero length", () => {
    expect(cuesFromTranscript("   ", 10)).toEqual([]);
    expect(cuesFromTranscript("Hello there.", 0)).toEqual([]);
  });
});

describe("discovery filters", () => {
  it("keeps known values and drops the rest", () => {
    const f = parseFilters({ sector: ["Fintech", "Crypto"], stage: "revenue,idea", country: "NG", evidence: "registry_record", activity: "30", page: "2" });
    expect(f.sector).toEqual(["Fintech"]);
    expect(f.stage).toEqual(["revenue", "idea"]);
    expect(f.country).toEqual(["NG"]);
    expect(f.evidence).toEqual(["registry_record"]);
    expect(f.activity).toBe("30");
    expect(f.page).toBe(2);
    expect(filterCount(f)).toBe(6);
  });
  it("ignores a bad activity or page", () => {
    const f = parseFilters({ activity: "7", page: "-3" });
    expect(f.activity).toBe("");
    expect(f.page).toBe(1);
  });
  it("turns empty groups into no filter for the database", () => {
    const args = rpcArgs(parseFilters({ sector: "Health", page: "3" }));
    expect(args).toEqual({ p_sectors: ["Health"], p_stages: null, p_countries: null, p_evidence: null, p_active_days: null, p_limit: PAGE_SIZE, p_offset: 2 * PAGE_SIZE });
  });
  it("writes the same filters back as a query string", () => {
    const f = parseFilters({ sector: ["Fintech", "Health"], activity: "90" });
    expect(queryString(f)).toBe("?sector=Fintech&sector=Health&activity=90");
    expect(queryString(f, 2)).toBe("?sector=Fintech&sector=Health&activity=90&page=2");
    expect(queryString(parseFilters({}))).toBe("");
  });
  it("offers the groups the For investors page describes", () => {
    expect(FILTER_GROUPS.map((g) => g.label)).toEqual(["Sector", "Stage", "Geography", "Evidence"]);
  });
  it("words the count", () => {
    expect(matchText(1, true)).toBe("1 founder matches these filters. Sorted by company name.");
    expect(matchText(3, false)).toBe("3 founders are on IkonetU. Sorted by company name.");
  });
});

describe("momentum", () => {
  it("counts updates in 90 days and marks the weeks that had one", () => {
    const m = momentum(["2026-10-14T09:00:00Z", "2026-10-13T09:00:00Z", "2026-09-20T09:00:00Z", "2026-06-01T09:00:00Z"], NOW);
    expect(m.in90).toBe(3);
    expect(m.consistencyText).toBe("3 updates in 90 days");
    expect(m.weeks).toHaveLength(13);
    expect(m.weeks[12]).toEqual({ ago: 0, active: true });
    expect(m.weeks.filter((w) => w.active).map((w) => w.ago)).toEqual([3, 0]);
    expect(m.activeWeeks).toBe(2);
  });
  it("says so when there is no update", () => {
    expect(momentum([], NOW).consistencyText).toBe("No updates in 90 days");
    expect(momentum(["2026-10-01T00:00:00Z"], NOW).consistencyText).toBe("1 update in 90 days");
  });
  it("counts the evidence added in 90 days and its areas", () => {
    const e = (category: string, createdAt: string) => ({ category, createdAt });
    expect(evidenceAddedText([], NOW)).toBe("None in 90 days");
    expect(evidenceAddedText([e("financial", "2026-10-01T00:00:00Z"), e("financial", "2026-09-01T00:00:00Z"), e("legal", "2026-06-01T00:00:00Z")], NOW)).toBe("2 pieces in 90 days, in 1 of 8 areas");
    expect(evidenceAddedText([e("team", "2026-10-14T00:00:00Z")], NOW)).toBe("1 piece in 90 days, in 1 of 8 areas");
  });
  it("gives every area a reason it matters", () => {
    expect(AREAS.every((a) => AREA_WHY[a.code].length > 20)).toBe(true);
  });
});
