import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AppShell } from "@/components/app/shell";
import { homeFor, requireViewer } from "@/lib/session";
import { InvestorSignUpForm } from "./form";

export const metadata: Metadata = { title: "Create your investor profile", robots: { index: false } };
export const dynamic = "force-dynamic";

export default async function InvestorOnboardingPage() {
  const { supabase, user, profile } = await requireViewer();
  if (profile && profile.role !== "investor") redirect(homeFor(profile));
  if (profile) {
    const details = await supabase.from("investor_profiles").select("user_id").eq("user_id", user.id).maybeSingle();
    if (details.data) redirect(homeFor(profile));
  }
  return (
    <AppShell role="none">
      <div className="app-narrow">
        <h1 className="app-title">Create your investor profile</h1>
        <p className="app-lede">
          Tell us who you are and what you invest in. An IkonetU admin checks each investor account before it can browse founder
          profiles. We will show you here when yours is approved.
        </p>
        <InvestorSignUpForm askAdult={user.user_metadata?.confirmed_adult !== true} name={profile?.full_name ?? ""} />
      </div>
    </AppShell>
  );
}
