import type { WaitlistRow } from "./waitlist";

export type InsertOutcome = "created" | "duplicate" | "not_configured" | "failed";

/**
 * Writes one waitlist row through the Supabase REST API with the service role
 * key. The key stays on the server: this module is only imported by route
 * handlers, and the variable has no NEXT_PUBLIC_ prefix.
 */
export async function insertWaitlistRow(row: WaitlistRow, fetchImpl: typeof fetch = fetch): Promise<InsertOutcome> {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;
  if (!url || !key) return "not_configured";
  try {
    const res = await fetchImpl(`${url.replace(/\/$/, "")}/rest/v1/waitlist`, {
      method: "POST",
      headers: {
        apikey: key,
        Authorization: `Bearer ${key}`,
        "Content-Type": "application/json",
        Prefer: "return=minimal",
      },
      body: JSON.stringify(row),
      cache: "no-store",
    });
    if (res.ok) return "created";
    if (res.status === 409) return "duplicate";
    return "failed";
  } catch {
    return "failed";
  }
}
