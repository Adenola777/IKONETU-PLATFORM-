import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { AppHeader } from "../app-header";
import { signOut } from "../dashboard/actions";
import { OnboardingForm } from "./onboarding-form";

export const metadata: Metadata = { title: "Create your profile | IkonetU", robots: { index: false } };
export const dynamic = "force-dynamic";

export default async function OnboardingPage() {
  const supabase = await createClient();
  if (!supabase) redirect("/signin");
  const { data: auth } = await supabase.auth.getUser();
  if (!auth.user) redirect("/signin");

  const [profile, ventures] = await Promise.all([
    supabase.from("profiles").select("user_id").eq("user_id", auth.user.id).maybeSingle(),
    supabase.from("ventures").select("id").eq("founder_id", auth.user.id).limit(1),
  ]);
  if (profile.data && ventures.data && ventures.data.length > 0) redirect("/dashboard");

  return (
    <>
      <AppHeader>
        <form action={signOut}>
          <button type="submit" className="btn btn-ghost">Sign out</button>
        </form>
      </AppHeader>
      <main id="main" className="section tint">
        <div className="wrap form-wrap">
          <h1 className="title" style={{ marginBottom: 12 }}>Create your profile</h1>
          <p className="lede" style={{ marginBottom: 36 }}>
            Tell us about you and your venture. Other signed-in members can see your name, country, city, institution, bio
            and venture. Nobody else can see your email or phone number.
          </p>
          <OnboardingForm askAdult={auth.user.user_metadata?.confirmed_adult !== true} />
        </div>
      </main>
    </>
  );
}
