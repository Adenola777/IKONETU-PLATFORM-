import { NextResponse, type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { logWarn } from "@/lib/log";

export const dynamic = "force-dynamic";

/** The sign-in email links here. The one-time code becomes a session cookie. */
export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get("code");
  const supabase = await createClient();
  if (code && supabase) {
    const { error } = await supabase.auth.exchangeCodeForSession(code);
    if (!error) return NextResponse.redirect(new URL("/dashboard", request.url));
    logWarn("auth.callback_failed", { status: error.status, code: error.code });
  }
  return NextResponse.redirect(new URL("/signin?error=link", request.url));
}
