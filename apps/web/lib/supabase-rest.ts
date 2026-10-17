import type { WaitlistRow } from "./waitlist";

export type InsertOutcome = "created" | "duplicate" | "not_configured" | "failed";

/**
 * Writes one row through the Supabase REST API with the service role key. The
 * key stays on the server: this module is only imported by route handlers, and
 * the variable has no NEXT_PUBLIC_ prefix.
 */
async function insertRow(table: string, row: object, fetchImpl: typeof fetch): Promise<InsertOutcome> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return "not_configured";
  try {
    const res = await fetchImpl(`${url.replace(/\/$/, "")}/rest/v1/${table}`, {
      method: "POST",
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        "Content-Type": "application/json",
        Prefer: "return=minimal",
      },
      body: JSON.stringify(row),
      cache: "no-store",
      signal: AbortSignal.timeout(10_000),
    });
    if (res.ok) return "created";
    if (res.status === 409) return "duplicate";
    return "failed";
  } catch {
    return "failed";
  }
}

export function insertWaitlistRow(row: WaitlistRow, fetchImpl: typeof fetch = fetch): Promise<InsertOutcome> {
  return insertRow("waitlist", row, fetchImpl);
}
