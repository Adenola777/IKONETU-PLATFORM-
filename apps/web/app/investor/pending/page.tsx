import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { AppShell } from "@/components/app/shell";
import { dateText } from "@/lib/product";
import { homeFor, requireViewer } from "@/lib/session";

export const metadata: Metadata = { title: "Your investor account", robots: { index: false } };
export const dynamic = "force-dynamic";

/** Where an investor waits for an admin's decision, or learns it was declined. */
export default async function InvestorPendingPage() {
  const { supabase, user, profile } = await requireViewer();
  if (!profile || profile.role !== "investor") redirect(homeFor(profile));
  if (profile.status === "active") redirect("/investor");
  const details = await supabase.from("investor_profiles").select("created_at").eq("user_id", user.id).maybeSingle();
  if (!details.data) redirect("/onboarding/investor");

  const declined = profile.status === "suspended";
  return (
    <AppShell role="none">
      <div className="app-narrow stack">
        {declined ? (
          <>
            <h1 className="app-title">Your investor account is not approved</h1>
            <p className="app-lede" style={{ margin: 0 }}>
              An IkonetU admin did not approve this account, so it cannot browse founder profiles or request introductions. If you
              think this is a mistake, write to <a href="mailto:info@ikonetu.com">info@ikonetu.com</a> from the address you signed
              in with.
            </p>
          </>
        ) : (
          <>
            <h1 className="app-title">Your investor account is waiting for approval</h1>
            <p className="app-lede" style={{ margin: 0 }}>
              You sent your details on {dateText(details.data.created_at)}. An IkonetU admin checks each investor account before it
              can browse founder profiles and request introductions. Sign in again later to see the decision.
            </p>
            <div className="card card-i">
              <h2 className="app-h3">While you wait</h2>
              <p className="body2" style={{ margin: 0 }}>
                You can read <a href="/for-investors">what investors see</a> and the{" "}
                <a href="/terms#terms-investor">investor terms</a>.
              </p>
            </div>
          </>
        )}
      </div>
    </AppShell>
  );
}
