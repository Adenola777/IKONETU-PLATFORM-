import { NextResponse, type NextRequest } from "next/server";
import { createLimiter } from "@/lib/rate-limit";
import { insertWaitlistRow } from "@/lib/supabase-rest";
import { parseWaitlist } from "@/lib/waitlist";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const allow = createLimiter(5, 10 * 60 * 1000);
const MAX_BODY_BYTES = 4_096;

const DONE = { ok: true, message: "You are on the list. We will tell you when Season 1 opens in your country." };

export async function POST(req: NextRequest) {
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "unknown";
  if (!allow(ip)) {
    return NextResponse.json({ ok: false, message: "Too many attempts. Please try again in a few minutes." }, { status: 429 });
  }
  if (!req.headers.get("content-type")?.includes("application/json")) {
    return NextResponse.json({ ok: false, message: "Send the form as JSON." }, { status: 415 });
  }
  const text = await req.text();
  if (text.length > MAX_BODY_BYTES) {
    return NextResponse.json({ ok: false, message: "The form is too large." }, { status: 413 });
  }
  let body: unknown;
  try {
    body = JSON.parse(text);
  } catch {
    return NextResponse.json({ ok: false, message: "The form could not be read." }, { status: 400 });
  }

  const parsed = parseWaitlist(body);
  // A filled honeypot gets the normal success reply so bots learn nothing.
  if (!parsed.ok && parsed.bot) return NextResponse.json(DONE, { status: 201 });
  if (!parsed.ok) {
    return NextResponse.json({ ok: false, message: "Please check the form.", errors: parsed.errors }, { status: 422 });
  }

  const outcome = await insertWaitlistRow(parsed.row);
  switch (outcome) {
    case "created":
    case "duplicate": // same reply, so the form never reveals who has already joined
      return NextResponse.json(DONE, { status: 201 });
    case "not_configured":
      return NextResponse.json({ ok: false, message: "The waitlist is not open yet. Please try again soon." }, { status: 503 });
    default:
      return NextResponse.json({ ok: false, message: "Something went wrong on our side. Please try again." }, { status: 502 });
  }
}
