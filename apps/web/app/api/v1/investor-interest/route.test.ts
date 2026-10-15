import { NextRequest } from "next/server";
import { afterEach, describe, expect, it, vi } from "vitest";

const body = {
  fullName: "Ngozi Eze",
  email: "Ngozi@Example.com",
  country: "other",
  firm: "Eze Capital",
  sectors: ["Fintech", "Health"],
  chequeSize: "$25,000 to $100,000",
  investorType: "angel",
  confirmedAdult: true,
  acceptedPrivacy: true,
  emailConsent: true,
  confirmedStatement: true,
};

let n = 0;
function req(payload: unknown, headers: Record<string, string> = {}) {
  n += 1;
  return new NextRequest("http://localhost/api/v1/investor-interest", {
    method: "POST",
    headers: { "content-type": "application/json", "x-forwarded-for": `10.1.0.${n}`, ...headers },
    body: typeof payload === "string" ? payload : JSON.stringify(payload),
  });
}

async function load() {
  vi.resetModules();
  return import("./route");
}

function configured() {
  vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "https://example.supabase.co");
  vi.stubEnv("SUPABASE_SERVICE_ROLE_KEY", "test-key");
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
});

describe("POST /api/v1/investor-interest", () => {
  it("returns 503 when Supabase is not configured", async () => {
    vi.stubEnv("NEXT_PUBLIC_SUPABASE_URL", "");
    vi.stubEnv("SUPABASE_SERVICE_ROLE_KEY", "");
    const { POST } = await load();
    expect((await POST(req(body))).status).toBe(503);
  });

  it("writes every answer to investor_interest and returns 201", async () => {
    configured();
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await load();
    const res = await POST(req(body));
    expect(res.status).toBe(201);
    const [url, init] = fetchMock.mock.calls[0]!;
    expect(url).toBe("https://example.supabase.co/rest/v1/investor_interest");
    expect(JSON.parse(init.body)).toEqual({
      full_name: "Ngozi Eze",
      email: "ngozi@example.com",
      country: "other",
      firm: "Eze Capital",
      sectors: ["Fintech", "Health"],
      cheque_size: "$25,000 to $100,000",
      investor_type: "angel",
      confirmed_adult: true,
      confirmed_statement: true,
      email_consent: true,
      privacy_version: "2026-10-15",
      source: "website",
    });
  });

  it("stores an empty firm as no firm", async () => {
    configured();
    const fetchMock = vi.fn().mockResolvedValue(new Response(null, { status: 201 }));
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await load();
    await POST(req({ ...body, firm: "  " }));
    expect(JSON.parse(fetchMock.mock.calls[0]![1].body).firm).toBeNull();
  });

  it("gives the same reply for an email that already registered", async () => {
    configured();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 409 })));
    const { POST } = await load();
    expect((await POST(req(body))).status).toBe(201);
  });

  it("returns 502 when the database refuses the row", async () => {
    configured();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 400 })));
    const { POST } = await load();
    expect((await POST(req(body))).status).toBe(502);
  });

  it("names each wrong answer by its field", async () => {
    configured();
    const { POST } = await load();
    const res = await POST(req({ ...body, email: "not-an-email", sectors: [], investorType: "trader", emailConsent: false }));
    expect(res.status).toBe(422);
    const json = await res.json();
    expect(Object.keys(json.errors).sort()).toEqual(["email", "emailConsent", "investorType", "sectors"]);
  });

  it("refuses a sector outside the list and a repeated sector", async () => {
    configured();
    const { POST } = await load();
    expect((await POST(req({ ...body, sectors: ["Crypto"] }))).status).toBe(422);
    expect((await POST(req({ ...body, sectors: ["Fintech", "Fintech"] }))).status).toBe(422);
  });

  it("refuses fields the form does not have", async () => {
    configured();
    const { POST } = await load();
    expect((await POST(req({ ...body, role: "admin" }))).status).toBe(422);
  });

  it("answers a filled honeypot as a success and writes nothing", async () => {
    configured();
    const fetchMock = vi.fn();
    vi.stubGlobal("fetch", fetchMock);
    const { POST } = await load();
    expect((await POST(req({ ...body, website: "http://spam.example" }))).status).toBe(201);
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("refuses a body that is not JSON", async () => {
    configured();
    const { POST } = await load();
    expect((await POST(req("name=x", { "content-type": "application/x-www-form-urlencoded" }))).status).toBe(415);
    expect((await POST(req("{not json"))).status).toBe(400);
  });

  it("limits each address to five attempts in ten minutes", async () => {
    configured();
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(new Response(null, { status: 201 })));
    const { POST } = await load();
    const same = { "x-forwarded-for": "10.9.9.9" };
    const codes = [];
    for (let i = 0; i < 6; i++) codes.push((await POST(req(body, same))).status);
    expect(codes).toEqual([201, 201, 201, 201, 201, 429]);
  });
});
