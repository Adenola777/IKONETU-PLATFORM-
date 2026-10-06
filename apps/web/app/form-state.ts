/** What a server action hands back to the form that called it. */
export type FormState =
  | { status: "idle" }
  | { status: "sent"; message: string }
  | { status: "error"; message: string; errors: Record<string, string>; values?: Record<string, string> };

export const IDLE: FormState = { status: "idle" };

/** The text fields a person typed, so a form can show them again after an error. */
export function typedValues(form: FormData, names: readonly string[]): Record<string, string> {
  return Object.fromEntries(names.map((n) => [n, String(form.get(n) ?? "")]));
}
