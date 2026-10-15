/**
 * Error tracking with Sentry, on the server only. It stays off until
 * SENTRY_DSN is set on the host, so nothing leaves the app before then.
 *
 * Only the server reports, because the failures that matter here happen in
 * server actions and route handlers. Visitors' browsers send nothing to Sentry,
 * so the Content-Security-Policy and the cookie policy are unchanged.
 * Sentry must be named in the privacy policy before SENTRY_DSN is set.
 */
export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs" || !process.env.SENTRY_DSN) return;
  const Sentry = await import("@sentry/nextjs");
  const { scrub } = await import("./lib/sentry-scrub");
  Sentry.init({
    dsn: process.env.SENTRY_DSN,
    environment: process.env.SENTRY_ENVIRONMENT || "production",
    sendDefaultPii: false,
    tracesSampleRate: 0,
    maxBreadcrumbs: 0,
    beforeSend: scrub,
  });
}

/** Errors Next.js catches while it renders a page or runs an action or route. */
export async function onRequestError(
  error: unknown,
  request: { path: string; method: string; headers: Record<string, string | string[] | undefined> },
  context: { routerKind: string; routePath: string; routeType: string },
) {
  if (process.env.NEXT_RUNTIME !== "nodejs" || !process.env.SENTRY_DSN) return;
  const Sentry = await import("@sentry/nextjs");
  Sentry.captureRequestError(error, { ...request, headers: {} }, context);
}
