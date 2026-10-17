import * as Sentry from "@sentry/nextjs";

/**
 * Logging for the server. Each event is one line of JSON on standard output,
 * so the host's log search can filter on its fields: the time, the level, the
 * event name and a few codes. Fields carry ids and error codes only, never a
 * name, an email address or anything a person typed.
 *
 * An error is also sent to Sentry. Sentry starts only when SENTRY_DSN is set
 * (instrumentation.ts), and until then sending to it does nothing.
 *
 * Import this from server code only: server actions, route handlers and
 * server components.
 */
export type LogFields = Record<string, string | number | boolean | null | undefined>;

function line(level: "info" | "warn" | "error", event: string, fields: LogFields) {
  return JSON.stringify({ time: new Date().toISOString(), level, event, ...fields });
}

export function logInfo(event: string, fields: LogFields = {}) {
  console.log(line("info", event, fields));
}

export function logWarn(event: string, fields: LogFields = {}) {
  console.warn(line("warn", event, fields));
}

export function logError(event: string, fields: LogFields = {}, error?: unknown) {
  console.error(line("error", event, fields));
  if (error instanceof Error) Sentry.captureException(error, { tags: { event }, extra: fields });
  else Sentry.captureMessage(event, { level: "error", tags: { event }, extra: fields });
}
