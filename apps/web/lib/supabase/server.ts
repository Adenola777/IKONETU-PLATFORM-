import { createServerClient } from "@supabase/ssr";
import { cookies } from "next/headers";
import { timedFetch } from "@/lib/timed-fetch";
import { supabasePublicEnv } from "./env";

/**
 * A Supabase client that acts as the signed-in person, for server components,
 * server actions and route handlers. Row level security applies to every query.
 * Every call has a time limit (lib/timed-fetch.ts). Returns null when Supabase
 * is not configured.
 */
export async function createClient() {
  const env = supabasePublicEnv();
  if (!env) return null;
  const cookieStore = await cookies();
  return createServerClient(env.url, env.key, {
    global: { fetch: timedFetch() },
    cookies: {
      getAll() {
        return cookieStore.getAll();
      },
      setAll(cookiesToSet) {
        try {
          cookiesToSet.forEach(({ name, value, options }) => cookieStore.set(name, value, options));
        } catch {
          // A server component cannot set cookies. The middleware refreshes the session instead.
        }
      },
    },
  });
}
