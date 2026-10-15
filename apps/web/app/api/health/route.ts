import { createClient } from "@supabase/supabase-js";
import { NextResponse } from "next/server";
import { logWarn } from "@/lib/log";
import { supabasePublicEnv } from "@/lib/supabase/env";
import { timedFetch } from "@/lib/timed-fetch";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const NO_STORE = { "cache-control": "no-store" };

/**
 * For an uptime monitor. It answers 200 when the app is running and the
 * database answers through Supabase, and 503 when Supabase cannot be reached
 * within five seconds or is not configured. It reads nothing: health() in
 * migration 20261015000004 returns true.
 *
 * Render's own health check stays on "/", which does not depend on Supabase,
 * so a Supabase outage does not make Render restart the app or hold a deploy.
 */
export async function GET() {
  const env = supabasePublicEnv();
  if (!env) return NextResponse.json({ status: "degraded", supabase: "not_configured" }, { status: 503, headers: NO_STORE });
  const supabase = createClient(env.url, env.key, {
    auth: { persistSession: false, autoRefreshToken: false },
    global: { fetch: timedFetch(undefined, () => 5_000) },
  });
  const { data, error } = await supabase.rpc("health");
  if (error || data !== true) {
    logWarn("health.supabase_unreachable", { code: error?.code || error?.message?.slice(0, 80) });
    return NextResponse.json({ status: "degraded", supabase: "unreachable" }, { status: 503, headers: NO_STORE });
  }
  return NextResponse.json({ status: "ok", supabase: "ok" }, { headers: NO_STORE });
}
