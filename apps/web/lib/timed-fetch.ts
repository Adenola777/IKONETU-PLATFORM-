/**
 * fetch with a time limit, for every call the server makes to Supabase. Without
 * one, a Supabase outage left each request waiting for as long as the runtime
 * allows. A file upload to storage gets longer, because an evidence file of
 * 10 MB on a slow link takes time to send; everything else gets 15 seconds.
 * A signal the caller passes still works alongside the time limit.
 */
export const QUICK_MS = 15_000;
export const UPLOAD_MS = 120_000;

export function timeoutFor(input: RequestInfo | URL, init?: RequestInit): number {
  const url = typeof input === "string" ? input : input instanceof URL ? input.href : input.url;
  const method = (init?.method ?? (typeof input === "object" && "method" in input ? input.method : "GET")).toUpperCase();
  const upload = (method === "POST" || method === "PUT") && /\/storage\/v1\/object\/(?!sign\/|list\/|info\/)/.test(url);
  return upload ? UPLOAD_MS : QUICK_MS;
}

/** Either signal aborts the result. Uses AbortSignal.any where the runtime has it. */
function either(a: AbortSignal, b: AbortSignal): AbortSignal {
  if (typeof AbortSignal.any === "function") return AbortSignal.any([a, b]);
  const c = new AbortController();
  const stop = (s: AbortSignal) => () => c.abort(s.reason);
  if (a.aborted) c.abort(a.reason);
  else if (b.aborted) c.abort(b.reason);
  else {
    a.addEventListener("abort", stop(a), { once: true });
    b.addEventListener("abort", stop(b), { once: true });
  }
  return c.signal;
}

export function timedFetch(base?: typeof fetch, pick: typeof timeoutFor = timeoutFor): typeof fetch {
  return (input, init) => {
    const limit = AbortSignal.timeout(pick(input, init));
    const signal = init?.signal ? either(init.signal, limit) : limit;
    return (base ?? fetch)(input, { ...init, signal });
  };
}
