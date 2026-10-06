/**
 * The two public values the sign-in client needs. Both are safe in the browser.
 * When either is missing, sign-in reports that it is not open yet.
 */
export function supabasePublicEnv(): { url: string; key: string } | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const key = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;
  return url && key ? { url, key } : null;
}
