/**
 * Small fixed-window limiter kept in memory. Each server instance keeps its
 * own count, so this slows down casual abuse only. SRD SEC-W4 asks for a limit
 * in front of the app as well, which docs/HOSTING.md records as not yet set up.
 */
export function createLimiter(limit: number, windowMs: number) {
  const hits = new Map<string, { count: number; resetAt: number }>();
  return function allow(key: string, now = Date.now()): boolean {
    const entry = hits.get(key);
    if (!entry || entry.resetAt <= now) {
      if (hits.size > 10_000) hits.clear();
      hits.set(key, { count: 1, resetAt: now + windowMs });
      return true;
    }
    entry.count += 1;
    return entry.count <= limit;
  };
}
