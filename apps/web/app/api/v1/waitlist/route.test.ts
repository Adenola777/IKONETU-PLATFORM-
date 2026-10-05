import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

const body = {
  fullName: "Kwame Mensah",
  contact: "kwame@example.com",
  country: "GH",
  role: "mentor",
  confirmedAdult: true,
  acceptedPrivacy: true,
};

let n = 0;
function req(payload: unknown, headers: Record<string, string> = {}) {
  n += 1;
  return new NextRequest("http://localhost/api/v1/waitlist", {
    method: "POST",
    headers: { "content-type": "application/json", "x-forwarded-for": `10.0.0.${n}`, ...headers },
    body: typeof payload === "string" ? payload : JSON.stringify(payload),
  });
}

async function load() {
  vi.resetModules();
  return import("./route");
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("POST /api/v1/waitlist", () => {
  it("returns 503 when Supabase is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("SUPABASE_SERVICE_ROLE_KEY", "");
    const { POST } = await load();
    expect((await POST(req(body))).status).toBe(503);
  });

  it("writes the row and returns 201", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co");
    vi.stubEnv("SUPABASE_SERVICE_ROLE_KEY", "test-key");
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await load();
    const res = await POST(req(body));
    expect(res.status).toBe(201);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("https://example.supabase.co/rest/v1/waitlist");
    expect(JSON.parse(init.body)).toMatchObject({ contact: "kwame@example.com", contact_type: "email", country: "GH", role: "mentor" });
  });

  it("gives the same reply for a contact that already joined", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co");
    vi.stubEnv("SUPABASE_SERVICE_ROLE_KEY", "test-key");
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 409 })));
    const { POST } = await load();
    expect((await POST(req(body))).status).toBe(201);
  });

  it("returns 422 with field errors for a bad form", async () => {
    const { POST } = await load();
    const res = await POST(req({ ...body, confirmedAdult: false }));
    expect(res.status).toBe(422);
    expect((await res.json()).errors.confirmedAdult).toBeTruthy();
  });

  it("pretends to accept a bot and writes nothing", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co");
    vi.stubEnv("SUPABASE_SERVICE_ROLE_KEY", "test-key");
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await load();
    expect((await POST(req({ ...body, website: "spam.example" }))).status).toBe(201);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("rejects non-JSON and oversized bodies", async () => {
    const { POST } = await load();
    expect((await POST(req("x", { "content-type": "text/plain" }))).status).toBe(415);
    expect((await POST(req("x".repeat(5000)))).status).toBe(413);
    expect((await POST(req("{not json"))).status).toBe(400);
  });

  it("limits repeated attempts from one address", async () => {
    const { POST } = await load();
    const ip = { "x-forwarded-for": "203.0.113.9" };
    const codes = [];
    for (let i = 0; i < 6; i++) codes.push((await POST(req({}, ip))).status);
    expect(codes.slice(0, 5).every((c) => c === 422)).toBe(true);
    expect(codes[5]).toBe(429);
  });
});
