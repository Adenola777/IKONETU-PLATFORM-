import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { RUBRIC_V2 } from "../src/rubric.ts";
import { rubricToSql } from "../src/rubric-sql.ts";

const target = fileURLToPath(new URL("../../../supabase/migrations/20261005000002_rubric_v2.sql", import.meta.url));
writeFileSync(target, rubricToSql(RUBRIC_V2));
console.log(`Wrote ${target}`);
