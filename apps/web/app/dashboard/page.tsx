import type { Metadata } from "next";
import Link from "next/link";
import { AppShell } from "@/components/app/shell";
import { Icon } from "@/components/site/icons";
import { STAGES } from "@/lib/account";
import { COUNTRIES } from "@/lib/constants";
import { AreaMeter, MeterLegend } from "@/components/app/ui";
import { nextSteps, type OwnEvidence } from "@/lib/next-steps";
import { activityText, AREA_WHY, areaCells, areaLabel, dateText, isShownStatus, LEVEL, type AreaSummary, type ShownStatus } from "@/lib/product";
import { requireFounder } from "@/lib/session";
import { setPublished } from "./actions";
import { VentureForm } from "./venture-form";

export const metadata: Metadata = { title: "Your dashboard", robots: { index: false } };
export const dynamic = "force-dynamic";

const LEAGUE_NAME = { EARLY: "Early", RISING: "Rising", INVESTABLE: "Investable", ELITE: "Elite" } as const;

export default async function DashboardPage() {
  const { supabase, user, profile, venture } = await requireFounder();
  const [pitch, evidence, updates, requests, score] = await Promise.all([
    supabase.from("pitches").select("duration_seconds, updated_at").eq("venture_id", venture.id).maybeSingle(),
    supabase.from("evidence").select("id, signal_code, status, lane, expires_at, item_count, months, revenue_usd, stage").eq("venture_id", venture.id),
    supabase.from("venture_updates").select("created_at").eq("venture_id", venture.id).order("created_at", { ascending: false }).limit(1),
    supabase.from("introductions").select("id").eq("founder_id", user.id).eq("status", "pending"),
    supabase.from("scores").select("total, league").eq("venture_id", venture.id).maybeSingle(),
  ]);
  // The readiness check reads the evidence the way investors see it, so the two always agree.
  const shown = await supabase.rpc("venture_evidence", { p_venture: venture.id });
  const RANK: Record<ShownStatus, number> = { third_party: 3, reviewed: 2, submitted: 1 };
  const best = new Map<string, AreaSummary>();
  for (const e of (shown.data ?? []) as { category: string; shown_status: string }[]) {
    if (!isShownStatus(e.shown_status)) continue;
    const had = best.get(e.category);
    best.set(e.category, {
      category: e.category,
      status: had && RANK[had.status] >= RANK[e.shown_status] ? had.status : e.shown_status,
      count: (had?.count ?? 0) + 1,
    });
  }
  const areas = [...best.values()];
  const steps = nextSteps((evidence.data ?? []) as OwnEvidence[]);
  const evidenceCount = evidence.data?.length ?? 0;
  const reviewed = evidence.data?.filter((e) => e.status === "approved").length ?? 0;
  const lastUpdate = updates.data?.[0]?.created_at ?? null;
  const waiting = requests.data?.length ?? 0;
  const country = COUNTRIES.find((c) => c.code === venture.country)?.name ?? venture.country;
  const stage = STAGES.find((s) => s.code === venture.stage)?.label ?? venture.stage;
  const published = Boolean(venture.published_at);
  const hasPitch = Boolean(pitch.data);
  const now = new Date();

  return (
    <AppShell role="founder" current="overview">
      <h1 className="app-title">Welcome, {profile.full_name}</h1>
      <p className="app-lede">{venture.name} · {venture.sector} · {stage} · {country}</p>

      {waiting > 0 && (
        <p className="status status-info" role="status" style={{ marginBottom: 24 }}>
          {waiting === 1 ? "One investor has" : `${waiting} investors have`} asked for an introduction.{" "}
          <Link href="/dashboard/introductions">Answer the {waiting === 1 ? "request" : "requests"}</Link>
        </p>
      )}

      <div className="side">
        <div className="stack">
          <section className="card" aria-labelledby="vis-h">
            <h2 id="vis-h" className="app-h2">Who can see your profile</h2>
            {published ? (
              <p className="body2">
                Your profile is published. Approved investors have been able to find it since {dateText(venture.published_at)}. Hide
                it at any time, and it leaves their search at once.
              </p>
            ) : (
              <p className="body2">
                Your profile is hidden. Nobody but you and IkonetU staff can see it. Publish it when your pitch is ready, and approved
                investors can find it.
              </p>
            )}
            <form action={setPublished} className="row" style={{ marginTop: 16 }}>
              <input type="hidden" name="publish" value={published ? "no" : "yes"} />
              {published ? (
                <button type="submit" className="btn btn-n">Hide my profile</button>
              ) : (
                <button type="submit" className="btn btn-f" disabled={!hasPitch} aria-describedby={hasPitch ? undefined : "pub-need"}>
                  Publish my profile
                </button>
              )}
              <Link href="/dashboard/preview" className="tlink">See what investors see</Link>
            </form>
            {!hasPitch && !published && (
              <p id="pub-need" className="hint" style={{ marginTop: 8 }}>Add your one-minute pitch first. A profile cannot be published without one.</p>
            )}
          </section>

          <section className="card" aria-labelledby="ready-h">
            <h2 id="ready-h" className="app-h2">Readiness check</h2>
            <AreaMeter areas={areas} />
            <div style={{ margin: "12px 0 16px" }}><MeterLegend /></div>
            <ul className="todo" aria-label="The eight areas">
              {areaCells(areas).map((c) => (
                <li key={c.code}>
                  <span className={`chip ${LEVEL[c.level].chip}`} style={{ minWidth: 84, justifyContent: "center" }}>{LEVEL[c.level].name}</span>
                  <span>{c.label}{c.count ? ` · ${c.count} ${c.count === 1 ? "piece" : "pieces"} of evidence` : ""}</span>
                </li>
              ))}
            </ul>
            <h3 className="app-h3" style={{ marginTop: 24 }}>Your next three steps</h3>
            {steps.length === 0 ? (
              <p className="body2">Every area is as strong as your evidence can make it. Keep it current as things change.</p>
            ) : (
              <ol className="todo">
                {steps.map((s, i) => (
                  <li key={s.code}>
                    <span className="ico open" aria-hidden="true" style={{ fontWeight: 600, fontSize: 13 }}>{i + 1}</span>
                    <span>
                      <Link href={`/dashboard/evidence?signal=${s.code}`}>{s.label}</Link> <span className="small">({areaLabel(s.category)})</span>
                      <span className="small" style={{ display: "block" }}>Why it matters: {AREA_WHY[s.category].charAt(0).toLowerCase() + AREA_WHY[s.category].slice(1)}</span>
                    </span>
                  </li>
                ))}
              </ol>
            )}
            <p className="small" style={{ margin: "12px 0 0" }}>
              The steps come from the evidence that would strengthen your profile most. Evidence already waiting for a reviewer is left
              out. Investors see the same readiness check, never your score.
            </p>
          </section>

          <section className="card" aria-labelledby="todo-h">
            <h2 id="todo-h" className="app-h2">Your profile</h2>
            <ul className="todo">
              <Todo done={hasPitch} href="/dashboard/pitch" label={hasPitch ? "Your one-minute pitch is added." : "Add your one-minute pitch."} />
              <Todo
                done={evidenceCount > 0}
                href="/dashboard/evidence"
                label={evidenceCount ? `${evidenceCount} ${evidenceCount === 1 ? "piece" : "pieces"} of evidence added, ${reviewed} reviewed.` : "Add your first piece of evidence."}
              />
              <Todo
                done={Boolean(lastUpdate)}
                href="/dashboard/updates"
                label={lastUpdate ? `Last progress update: ${activityText(lastUpdate, now).replace("Updated ", "")}.` : "Post your first progress update."}
              />
            </ul>
          </section>

          <section className="card" aria-labelledby="venture-h">
            <h2 id="venture-h" className="app-h2">Your venture</h2>
            <VentureForm venture={venture} />
          </section>
        </div>

        <aside className="stack" aria-label="Your score">
          <section className="card" aria-labelledby="score-h">
            <h2 id="score-h" className="app-h2">IkonetU Score</h2>
            {score.data ? (
              <p className="body2">
                <strong style={{ fontSize: 36, color: "#101828" }}>{score.data.total.toLocaleString("en-GB")}</strong> of 1,000 ·{" "}
                {LEAGUE_NAME[score.data.league as keyof typeof LEAGUE_NAME]} league
              </p>
            ) : (
              <p className="body2">You have no score yet. Your score starts when your first piece of evidence is approved.</p>
            )}
            <p className="small" style={{ margin: "12px 0 0" }}>
              Only you and IkonetU staff see your score. Investors see your evidence by area and its status, never a score or a
              league.
            </p>
          </section>
        </aside>
      </div>
    </AppShell>
  );
}

function Todo({ done, href, label }: { done: boolean; href: string; label: string }) {
  return (
    <li>
      <span className={`ico ${done ? "done" : "open"}`} aria-hidden="true"><Icon name={done ? "check" : "plus"} size={14} /></span>
      <span><Link href={href}>{label}</Link><span className="sr-only">{done ? " Done." : " Not done yet."}</span></span>
    </li>
  );
}
