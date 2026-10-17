/** What a server action of the signed-in pages hands back to its form. */
export type AppState =
  | { status: "idle" }
  | { status: "sent"; message: string }
  | { status: "error"; message: string; errors: Record<string, string>; values?: Record<string, string | string[]> };

export const IDLE_STATE: AppState = { status: "idle" };

/** Everything the person typed or ticked, so the form can show it again after an error. */
export function formValues(form: FormData): Record<string, string | string[]> {
  const out: Record<string, string | string[]> = {};
  for (const key of new Set(form.keys())) {
    if (key.startsWith("$ACTION")) continue;
    const all = form.getAll(key).filter((v): v is string => typeof v === "string");
    out[key] = all.length > 1 ? all : (all[0] ?? "");
  }
  return out;
}

export function one(values: Record<string, string | string[]> | undefined, key: string): string {
  const v = values?.[key];
  return Array.isArray(v) ? (v[0] ?? "") : (v ?? "");
}

export function many(values: Record<string, string | string[]> | undefined, key: string): string[] {
  const v = values?.[key];
  return Array.isArray(v) ? v : v ? [v] : [];
}
