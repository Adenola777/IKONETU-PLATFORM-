import type { Metadata } from "next";
import { AppShell } from "@/components/app/shell";
import { requireInvestor } from "@/lib/session";
import { InvestorEditForm } from "./form";

export const metadata: Metadata = { title: "Your investor profile", robots: { index: false } };
export const dynamic = "force-dynamic";

export default async function InvestorProfilePage() {
  const { supabase, user, profile } = await requireInvestor();
  const d = await supabase
    .from("investor_profiles")
    .select("investor_type, firm, website, based_in, sectors, stages, countries, cheque_size, thesis")
    .eq("user_id", user.id)
    .maybeSingle();
  const initial: Record<string, string | string[]> = d.data
    ? {
        fullName: profile.full_name,
        investorType: d.data.investor_type,
        firm: d.data.firm ?? "",
        website: d.data.website ?? "",
        basedIn: d.data.based_in,
        sectors: d.data.sectors,
        stages: d.data.stages,
        countries: d.data.countries,
        chequeSize: d.data.cheque_size,
        thesis: d.data.thesis ?? "",
      }
    : { fullName: profile.full_name };
  return (
    <AppShell role="investor" current="profile">
      <div className="app-narrow">
        <h1 className="app-title">Your investor profile</h1>
        <p className="app-lede">
          Founders see your name, investor type and firm when you ask them for an introduction. A request you already sent keeps the
          details it was sent with.
        </p>
        <InvestorEditForm initial={initial} />
      </div>
    </AppShell>
  );
}
