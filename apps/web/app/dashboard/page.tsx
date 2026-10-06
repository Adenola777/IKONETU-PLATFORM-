import type { Metadata } from "next";
import { redirect } from "next/navigation";
import { STAGES } from "@/lib/account";
import { COUNTRIES } from "@/lib/constants";
import { createClient } from "@/lib/supabase/server";
import { AppHeader } from "../app-header";
import { signOut } from "./actions";

export const metadata: Metadata = { title: "Your dashboard | IkonetU", robots: { index: false } };
export const dynamic = "force-dynamic";

const LEAGUE_NAME = { EARLY: "Early", RISING: "Rising", INVESTABLE: "Investable", ELITE: "Elite" } as const;

export default async function DashboardPage() {
  const supabase = await createClient();
  if (!supabase) redirect("/signin");
  const { data: auth } = await supabase.auth.getUser();
  if (!auth.user) redirect("/signin");

  const [profile, ventures] = await Promise.all([
    supabase.from("profiles").select("full_name, country, city, institution").eq("user_id", auth.user.id).maybeSingle(),
    supabase
      .from("ventures")
      .select("id, name, sector, stage, country, description")
      .eq("founder_id", auth.user.id)
      .order("created_at", { ascending: true })
      .limit(1),
  ]);
  const venture = ventures.data?.[0];
  if (!profile.data || !venture) redirect("/onboarding");

  const score = await supabase.from("scores").select("total, league").eq("venture_id", venture.id).maybeSingle();
  const country = (code: string) => COUNTRIES.find((c) => c.code === code)?.name ?? code;
  const stage = STAGES.find((s) => s.code === venture.stage)?.label ?? venture.stage;
  const place = [profile.data.city, country(profile.data.country ?? "")].filter(Boolean).join(", ");

  return (
    <>
      <AppHeader>
        <form action={signOut}>
          <button type="submit" className="btn btn-ghost">Sign out</button>
        </form>
      </AppHeader>
      <main id="main" className="section tint">
        <div className="wrap">
          <h1 className="title" style={{ marginBottom: 8 }}>Welcome, {profile.data.full_name}</h1>
          <p className="lede" style={{ marginBottom: 36 }}>{[place, profile.data.institution].filter(Boolean).join(" · ")}</p>
          <div className="split" style={{ marginTop: 0 }}>
            <section className="card" aria-labelledby="venture-title" style={{ padding: 32 }}>
              <h2 id="venture-title" style={{ marginTop: 0 }}>{venture.name}</h2>
              <p>{venture.sector} · {stage} · {country(venture.country)}</p>
              {venture.description ? <p>{venture.description}</p> : null}
            </section>
            <section className="card card-navy" aria-labelledby="score-title" style={{ padding: 32 }}>
              <h2 id="score-title" style={{ marginTop: 0 }}>IkonetU Score</h2>
              {score.data ? (
                <p>
                  <strong style={{ fontSize: 40 }}>{score.data.total.toLocaleString("en-GB")}</strong> of 1,000 ·{" "}
                  {LEAGUE_NAME[score.data.league as keyof typeof LEAGUE_NAME]} league
                </p>
              ) : (
                <p>You have no score yet. Your score starts when your first piece of evidence is approved.</p>
              )}
            </section>
          </div>
        </div>
      </main>
    </>
  );
}
