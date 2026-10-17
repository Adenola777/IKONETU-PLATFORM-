import { afterEach, describe, expect, it, vi } from "vitest";
import { clientAddress } from "./client-ip";
import { logError, logInfo } from "./log";
import { isRepeat, requestKey } from "./request-key";
import { withRetry } from "./retry";
import { QUICK_MS, timedFetch, timeoutFor, UPLOAD_MS } from "./timed-fetch";

const h = (v: Record<string, string>) => new Headers(v);

describe("the caller's address for rate limits", () => {
  it("reads the entry the nearest proxy added, not the one the caller wrote", () => {
    expect(clientAddress(h({ "x-forwarded-for": "1.1.1.1, 9.9.9.9" }), {})).toBe("9.9.9.9");
    expect(clientAddress(h({ "x-forwarded-for": "2.2.2.2, 9.9.9.9" }), {})).toBe("9.9.9.9");
  });
  it("counts back as many entries as there are trusted proxies", () => {
    expect(clientAddress(h({ "x-forwarded-for": "6.6.6.6, 7.7.7.7, 10.0.0.1" }), { TRUSTED_PROXY_HOPS: "2" })).toBe("7.7.7.7");
  });
  it("treats a request that skipped the proxies as unknown", () => {
    expect(clientAddress(h({}), {})).toBe("unknown");
    expect(clientAddress(h({ "x-forwarded-for": "7.7.7.7" }), { TRUSTED_PROXY_HOPS: "2" })).toBe("unknown");
  });
  it("reads a single named header when one is configured", () => {
    expect(clientAddress(h({ "x-forwarded-for": "1.1.1.1", "cf-connecting-ip": "5.5.5.5" }), { CLIENT_IP_HEADER: "CF-Connecting-IP" })).toBe("5.5.5.5");
  });
});

describe("time limits on calls to Supabase", () => {
  it("gives uploads to storage longer than everything else", () => {
    expect(timeoutFor("https://x.supabase.co/storage/v1/object/evidence/u/f", { method: "POST" })).toBe(UPLOAD_MS);
    expect(timeoutFor("https://x.supabase.co/storage/v1/object/sign/pitches/u/f", { method: "POST" })).toBe(QUICK_MS);
    expect(timeoutFor("https://x.supabase.co/rest/v1/evidence", { method: "POST" })).toBe(QUICK_MS);
    expect(timeoutFor("https://x.supabase.co/storage/v1/object/evidence/u/f")).toBe(QUICK_MS);
  });
  it("gives up on a call that never answers", async () => {
    const never: typeof fetch = (_i, init) => new Promise((_r, reject) => init?.signal?.addEventListener("abort", () => reject(init.signal?.reason)));
    await expect(timedFetch(never, () => 30)("https://x.supabase.co/rest/v1/evidence")).rejects.toMatchObject({ name: "TimeoutError" });
  });
  it("still lets the caller cancel", async () => {
    const never: typeof fetch = (_i, init) => new Promise((_r, reject) => init?.signal?.addEventListener("abort", () => reject(new Error("cancelled"))));
    const c = new AbortController();
    const p = timedFetch(never, () => 10_000)("https://x.supabase.co/rest/v1/evidence", { signal: c.signal });
    c.abort();
    await expect(p).rejects.toThrow("cancelled");
  });
});

describe("retries", () => {
  it("waits 250, 500 and so on between attempts, and stops at the first success", async () => {
    const waits: number[] = [];
    let n = 0;
    const r = await withRetry(async () => (++n < 3 ? { ok: false as const, error: "busy" } : { ok: true as const, value: n }), { sleep: async (ms) => void waits.push(ms) });
    expect(r).toEqual({ ok: true, value: 3, attempts: 3 });
    expect(waits).toEqual([250, 500]);
  });
  it("reports the last error after the last attempt, and counts a thrown error as a failure", async () => {
    let n = 0;
    const r = await withRetry(async () => { n++; throw new Error(`down ${n}`); }, { attempts: 2, sleep: async () => {} });
    expect(r).toEqual({ ok: false, error: "down 2", attempts: 2 });
  });
});

describe("request keys", () => {
  it("accepts a UUID and ignores anything else", () => {
    const f = new FormData();
    f.set("requestKey", "0B6C2F4E-1111-4222-8333-944455556666");
    expect(requestKey(f)).toBe("0b6c2f4e-1111-4222-8333-944455556666");
    f.set("requestKey", "abc");
    expect(requestKey(f)).toBeNull();
    expect(requestKey(new FormData())).toBeNull();
  });
  it("recognises only the request key's own unique index", () => {
    expect(isRepeat({ code: "23505", message: 'duplicate key value violates unique constraint "venture_updates_request_key"' })).toBe(true);
    expect(isRepeat({ code: "23505", message: 'duplicate key value violates unique constraint "introductions_once"' })).toBe(false);
    expect(isRepeat(null)).toBe(false);
  });
});

describe("structured logs", () => {
  afterEach(() => vi.restoreAllMocks());
  it("writes one line of JSON with the time, level, event and fields", () => {
    const out = vi.spyOn(console, "error").mockImplementation(() => {});
    logError("evidence.save_failed", { venture: "v1", code: "42501" });
    const line = JSON.parse(String(out.mock.calls[0]?.[0]));
    expect(line).toMatchObject({ level: "error", event: "evidence.save_failed", venture: "v1", code: "42501" });
    expect(Date.parse(line.time)).not.toBeNaN();
  });
  it("logs information on standard output", () => {
    const out = vi.spyOn(console, "log").mockImplementation(() => {});
    logInfo("introduction.request_refused", { code: "23505" });
    expect(JSON.parse(String(out.mock.calls[0]?.[0]))).toMatchObject({ level: "info", event: "introduction.request_refused" });
  });
});

describe("what reaches Sentry", () => {
  it("keeps the method and the path of the request, and drops cookies, headers, form text, user and breadcrumbs", async () => {
    const { scrub } = await import("./sentry-scrub");
    const e = scrub({
      type: undefined,
      message: "update.post_failed",
      request: { method: "POST", url: "http://localhost:3100/dashboard/updates?x=1", cookies: { "sb-token": "secret" }, headers: { cookie: "sb-token=secret" }, data: "We signed a supplier" },
      user: { id: "u1", email: "a@b.test" },
      breadcrumbs: [{ message: "x" }],
    });
    expect(e.request).toEqual({ method: "POST", url: "http://localhost:3100/dashboard/updates" });
    expect(e.user).toBeUndefined();
    expect(e.breadcrumbs).toBeUndefined();
    expect(JSON.stringify(e)).not.toMatch(/secret|supplier|a@b\.test/);
  });
});
