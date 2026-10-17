const UUID = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

/**
 * The request key a form sends with evidence, an update or a message. The form
 * makes a new key each time it is shown, so the same key arriving twice means
 * the same submission was sent twice, and the database keeps it once
 * (migration 20261015000004). A missing or malformed key is treated as none.
 */
export function requestKey(form: FormData): string | null {
  const v = String(form.get("requestKey") ?? "");
  return UUID.test(v) ? v.toLowerCase() : null;
}

/** True when a database error is the request key's unique index refusing a second copy. */
export function isRepeat(error: { code?: string; message?: string } | null | undefined): boolean {
  return Boolean(error && error.code === "23505" && /request_key/.test(error.message ?? ""));
}
