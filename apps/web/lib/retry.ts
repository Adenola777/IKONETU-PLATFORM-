/**
 * Runs a step again when it fails, waiting longer each time: 250 ms, then
 * 500 ms, then 1 s by default. Use it only for a step that is safe to repeat.
 * The result says how many attempts it took and the last error when every
 * attempt failed.
 */
export async function withRetry<T>(
  step: () => Promise<{ ok: true; value: T } | { ok: false; error: string }>,
  { attempts = 3, baseMs = 250, sleep = (ms: number) => new Promise<void>((r) => setTimeout(r, ms)) } = {},
): Promise<{ ok: true; value: T; attempts: number } | { ok: false; error: string; attempts: number }> {
  let last = "";
  for (let i = 1; i <= attempts; i++) {
    try {
      const r = await step();
      if (r.ok) return { ok: true, value: r.value, attempts: i };
      last = r.error;
    } catch (e) {
      last = e instanceof Error ? e.message : String(e);
    }
    if (i < attempts) await sleep(baseMs * 2 ** (i - 1));
  }
  return { ok: false, error: last, attempts };
}
