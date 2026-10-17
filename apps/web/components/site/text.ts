/** Turns a value into text for an attribute, the way the design boards do: nothing for null, undefined and false. */
export function t(value: unknown): string {
  return value === null || value === undefined || value === false ? "" : String(value);
}
