import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { phoneSignInEnabled } from "@/lib/pending-sign-in";
import { createClient } from "@/lib/supabase/server";
import { SignInFrame } from "@/components/site/sign-in-frame";
import { SignInForm } from "./signin-form";

export const metadata: Metadata = { title: "Sign in", robots: { index: false } };
export const dynamic = "force-dynamic";

export default async function SignInPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const supabase = await createClient();
  if (supabase) {
    const { data } = await supabase.auth.getUser();
    if (data.user) redirect("/dashboard");
  }
  const { error } = await searchParams;
  const phoneEnabled = phoneSignInEnabled();

  return (
    <SignInFrame label="Sign in">
      <h1>Sign in or create your account</h1>
      <p className="si-lede">
        {phoneEnabled
          ? "Enter your phone number to create your account or to sign back in. A new account then chooses founder or investor."
          : "Enter your email to create your account or to sign back in. A new account then chooses founder or investor."}
      </p>
      {error === "link" && (
        <p className="status status-err" role="alert" style={{ marginBottom: 20 }}>
          That sign-in link has expired or was already used. Please ask for a new code.
        </p>
      )}
      <SignInForm phoneEnabled={phoneEnabled} />
    </SignInFrame>
  );
}
