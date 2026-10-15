import type { ErrorEvent } from "@sentry/nextjs";

/**
 * Keeps only what explains the error. A check on 15 October 2026 against a
 * stand-in for Sentry found that, with sendDefaultPii off, the event still
 * carried the whole request: the sign-in cookies with the access and refresh
 * tokens, every header and the text of the form. So the request is cut down to
 * its method and its path, the user is dropped, and no breadcrumbs are kept.
 */
export function scrub(event: ErrorEvent): ErrorEvent {
  const req = event.request;
  event.request = req ? { method: req.method, url: req.url?.split("?")[0] } : undefined;
  delete event.user;
  delete event.breadcrumbs;
  return event;
}
