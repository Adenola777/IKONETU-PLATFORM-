import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { supabasePublicEnv } from "@/lib/supabase/env";

/**
 * Runs only on the signed-in pages listed in the matcher below. It refreshes
 * the Supabase session cookie and sends a person who is not signed in to the
 * sign-in page. The public pages stay static and never wait on Supabase.
 */
export async function middleware(request: NextRequest) {
  const env = supabasePublicEnv();
  if (!env) return NextResponse.redirect(new URL("/signin", request.url));

  let response = NextResponse.next({ request });
  const supabase = createServerClient(env.url, env.key, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet) {
        cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) => response.cookies.set(name, value, options));
      },
    },
  });

  // getUser asks Supabase to confirm the token, so a forged cookie is refused.
  const { data } = await supabase.auth.getUser();
  if (!data.user) {
    return NextResponse.redirect(new URL("/signin", request.url));
  }
  return response;
}

export const config = {
  matcher: ["/dashboard/:path*", "/onboarding/:path*"],
};
