import type { Metadata } from "next";
import Link from "next/link";
import { redirect } from "next/navigation";
import { AppShell } from "@/components/app/shell";
import { homeFor, requireViewer } from "@/lib/session";

export const metadata: Metadata = { title: "Join IkonetU", robots: { index: false } };
export const dynamic = "force-dynamic";

/** The first step after sign-in: a person says whether they are a founder or an investor. */
export default async function OnboardingPage() {
  const { supabase, user, profile } = await requireViewer();
  if (profile) {
    if (profile.role === "founder") {
      const ventures = await supabase.from("ventures").select("id").eq("founder_id", user.id).limit(1);
      if (!ventures.data?.length) redirect("/onboarding/founder");
    }
    redirect(homeFor(profile));
  }

  return (
    <AppShell role="none">
      <h1 className="app-title">How will you use IkonetU?</h1>
      <p className="app-lede">Choose one. Each account is either a founder account or an investor account.</p>
      <div className="choice">
        <section className="card card-f" aria-labelledby="c-founder">
          <h2 id="c-founder" className="app-h2" style={{ margin: 0 }}>I am a founder</h2>
          <p className="body2">
            Create your profile and your venture, upload a one-minute pitch, add evidence, and publish when you are ready.
            Approved investors can then find you and ask for an introduction, which you accept or decline.
          </p>
          <Link className="btn btn-f" href="/onboarding/founder">Create a founder profile</Link>
        </section>
        <section className="card card-i" aria-labelledby="c-investor">
          <h2 id="c-investor" className="app-h2" style={{ margin: 0 }}>I am an investor</h2>
          <p className="body2">
            Tell us what you invest in. An IkonetU admin checks each investor account before it can browse founder profiles
            and request introductions.
          </p>
          <Link className="btn btn-i" href="/onboarding/investor">Create an investor profile</Link>
        </section>
      </div>
    </AppShell>
  );
}
