import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppHeader } from "../app-header";
import { SignInForm } from "./signin-form";

export const metadata: Metadata = { title: "Get started | IkonetU", robots: { index: false } };
export const dynamic = "force-dynamic";

export default async function SignInPage({ searchParams }: { searchParams: Promise<{ error?: string }> }) {
  const supabase = await createClient();
  if (supabase) {
    const { data } = await supabase.auth.getUser();
    if (data.user) redirect("/dashboard");
  }
  const { error } = await searchParams;

  return (
    <>
      <AppHeader />
      <main id="main" className="section tint">
        <div className="wrap form-wrap">
          <h1 className="title" style={{ marginBottom: 12 }}>Get started</h1>
          <p className="lede" style={{ marginBottom: 36 }}>
            Enter your email to create your founder account or to sign back in.
          </p>
          {error === "link" && (
            <p className="status status-err" role="alert" style={{ marginBottom: 20 }}>
              That sign-in link has expired or was already used. Please ask for a new one.
            </p>
          )}
          <SignInForm />
        </div>
      </main>
    </>
  );
}
