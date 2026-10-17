"use client";

import { createBrowserClient } from "@supabase/ssr";

/**
 * A Supabase client in the browser, acting as the signed-in person through the
 * session cookie. Only the pitch upload uses it, so a large video goes straight
 * to storage rather than through this app's server.
 */
export function browserClient() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  if (!url || !key) return null;
  return createBrowserClient(url, key);
}
