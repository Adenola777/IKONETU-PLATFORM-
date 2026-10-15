import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AppShell } from "@/components/app/shell";
import { homeFor, requireViewer } from "@/lib/session";
import { OnboardingForm } from "../founder-form";

export const metadata: Metadata = { title: "Create your founder profile", robots: { index: false } };
export const dynamic = "force-dynamic";

export default async function FounderOnboardingPage() {
  const { supabase, user, profile } = await requireViewer();
  if (profile && profile.role !== "founder") redirect(homeFor(profile));
  if (profile) {
    const ventures = await supabase.from("ventures").select("id").eq("founder_id", user.id).limit(1);
    if (ventures.data && ventures.data.length > 0) redirect("/dashboard");
  }

  return (
    <AppShell role="none">
      <div className="app-narrow">
        <h1 className="app-title">Create your founder profile</h1>
        <p className="app-lede">
          Tell us about you and your venture. Nobody sees your profile until you publish it, and then only approved investors
          see it. Nobody else can see your email or phone number.
        </p>
        <OnboardingForm askAdult={user.user_metadata?.confirmed_adult !== true} />
      </div>
    </AppShell>
  );
}
