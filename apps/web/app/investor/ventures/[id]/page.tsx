import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { withdrawIntroduction } from "@/app/introductions/actions";
import { AppShell } from "@/components/app/shell";
import { VentureProfileView } from "@/components/app/venture-profile";
import { Icon } from "@/components/site/icons";
import { dateText } from "@/lib/product";
import { requireInvestor } from "@/lib/session";
import { loadVentureProfile } from "@/lib/venture-profile";
import { RequestForm } from "./request-form";

export const metadata: Metadata = { title: "Founder profile", robots: { index: false } };
export const dynamic = "force-dynamic";

export default async function InvestorVenturePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const { supabase, user } = await requireInvestor();
  const p = await loadVentureProfile(supabase, id);
  if (!p) notFound();
  const mine = await supabase
    .from("introductions")
    .select("id, status, created_at, decided_at")
    .eq("venture_id", id)
    .eq("investor_id", user.id)
    .order("created_at", { ascending: false })
    .limit(1)
    .maybeSingle();
  const intro = mine.data;
  const founder = p.founder?.full_name ?? "The founder";

  const aside = (
    <section className="card card-i" aria-labelledby="intro-h" style={{ scrollMarginTop: 16 }}>
      <h2 id="intro-h" className="app-h2">Introduction</h2>
      {intro?.status === "pending" ? (
        <>
          <p className="body2">You asked on {dateText(intro.created_at)}. {founder} has not answered yet.</p>
          <form action={withdrawIntroduction} style={{ marginTop: 12 }}>
            <input type="hidden" name="id" value={intro.id} />
            <button type="submit" className="btn btn-n btn-sm">Withdraw my request</button>
          </form>
        </>
      ) : intro?.status === "accepted" ? (
        <>
          <p className="body2">{founder} accepted on {dateText(intro.decided_at)}.</p>
          <Link className="btn btn-i btn-sm" href={`/introductions/${intro.id}`} style={{ marginTop: 12 }}>Open the conversation</Link>
        </>
      ) : intro?.status === "declined" ? (
        <p className="body2">{founder} declined your request on {dateText(intro.decided_at)}. A declined request cannot be sent again.</p>
      ) : (
        <>
          <p className="body2" style={{ marginBottom: 16 }}>
            Every introduction starts here, so both sides know who is asking and why. The founder accepts or declines, and an
            accepted request opens a conversation on IkonetU.
          </p>
          <RequestForm venture={id} founder={founder} />
        </>
      )}
    </section>
  );

  return (
    <AppShell role="investor" current="discover">
      <Link href="/investor" className="back"><Icon name="arrow-left" size={16} /> All founders</Link>
      <VentureProfileView p={p} aside={aside} now={new Date()} jump={<a className="tlink jump" href="#intro-h">Introduction</a>} />
      <p className="small" style={{ marginTop: 48, maxWidth: 720 }}>
        Investing in early-stage companies can lose all the money invested. IkonetU facilitates discovery and introductions. It does
        not provide investment advice, and it does not endorse or approve any company.
      </p>
    </AppShell>
  );
}
