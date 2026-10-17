/**
 * The caller's address, for rate limits. Each proxy in front of the app adds
 * the address it received the request from to the end of X-Forwarded-For, so
 * only the entries added by trusted proxies can be believed. The caller writes
 * whatever it likes at the start of the header, and reading the first entry let
 * a caller choose a new address for every request (found on 15 October 2026).
 *
 * TRUSTED_PROXY_HOPS is the number of proxies in front of the app, and the
 * address is read that many entries from the end. It is 1 unless set. How many
 * proxies Render puts in front of a web service is unverified; HOSTING.md
 * describes the check to run after the first deployment.
 * CLIENT_IP_HEADER, when set, names a single header that the edge in front of
 * the app sets itself, such as one a CDN adds, and it is read instead.
 *
 * A request with fewer entries than the trusted hops did not pass through the
 * proxies, so its address cannot be believed and it is counted as "unknown".
 */
export function clientAddress(headers: Headers, env: Record<string, string | undefined> = process.env): string {
  const named = env.CLIENT_IP_HEADER?.trim().toLowerCase();
  if (named) return headers.get(named)?.trim() || "unknown";
  const hops = Math.max(1, Number.parseInt(env.TRUSTED_PROXY_HOPS ?? "1", 10) || 1);
  const list = (headers.get("x-forwarded-for") ?? "")
    .split(",")
    .map((s) => s.trim())
    .filter(Boolean);
  return list.length >= hops ? (list[list.length - hops] as string) : "unknown";
}
