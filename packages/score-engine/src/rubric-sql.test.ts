import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { RUBRIC_V2 } from "./rubric";
import { rubricToSql } from "./rubric-sql";

describe("rubric seed migration", () => {
  it("matches the rubric the score engine uses", () => {
    const path = new URL("../../../supabase/migrations/20261005000002_rubric_v2.sql", import.meta.url);
    expect(readFileSync(path, "utf8")).toBe(rubricToSql(RUBRIC_V2));
  });
});
