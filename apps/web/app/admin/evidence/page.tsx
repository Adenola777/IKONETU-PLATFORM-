import type { Metadata } from "next";
import Link from "next/link";
import { AppShell } from "@/components/app/shell";
import { signalLabel } from "@/lib/forms";
import { dateText } from "@/lib/product";
import { requireStaff } from "@/lib/session";
import { recomputeScore } from "./[id]/actions";

export const metadata: Metadata = { title: "Evidence to review", robots: { index: false } };
export const dynamic = "force-dynamic";

type Stale = { venture_id: string; name: string; last_decided_at: string; scored_at: string | null };
type Row = { id: string; signal_code: string; summary: string | null; created_at: string; ventures: { name: string } | null };

/**
 * Evidence waiting for a decision, oldest first, and any venture whose score
 * missed an update after a decision, with a button to recompute it.
 */
export default async function EvidenceQueuePage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { supabase, profile } = await requireStaff();
  const failed = (await searchParams).score === "failed";
  const stale = await supabase.rpc("ventures_with_stale_scores");
  const staleRows = (stale.data ?? []) as Stale[];
  const { data, error } = await supabase
    .from("evidence")
    .select("id, signal_code, summary, created_at, ventures(name)")
    .in("status", ["submitted", "checking", "needs_review"])
    .order("created_at", { ascending: true })
    .limit(200);
  const rows = (data ?? []) as unknown as Row[];
  return (
    <AppShell role={profile.role === "admin" ? "admin" : "reviewer"} current="queue">
      <h1 className="app-title">Evidence to review</h1>
      <p className="app-lede">
        Until you decide, investors see each item as founder submitted. Approving it shows investors what you compared and when.
        Asking for more or rejecting it hides it from investors and tells the founder why.
      </p>
      {failed && (
        <p className="status status-err" role="alert">
          The decision is saved, but the founder&apos;s score did not update after three attempts. Recompute it below, or try again later.
        </p>
      )}
      {staleRows.length > 0 && (
        <section className="card" aria-labelledby="stale-h" style={{ marginBottom: 24 }}>
          <h2 id="stale-h" className="app-h2">Scores to update</h2>
          <p className="body2">Each of these ventures has a decision that is newer than its score, so its founder sees an out-of-date score.</p>
          <ul className="todo">
            {staleRows.map((v) => (
              <li key={v.venture_id} style={{ alignItems: "center", justifyContent: "space-between" }}>
                <span>{v.name} <span className="small">· decided {dateText(v.last_decided_at)}{v.scored_at ? `, scored ${dateText(v.scored_at)}` : ", never scored"}</span></span>
                <form action={recomputeScore}>
                  <input type="hidden" name="venture" value={v.venture_id} />
                  <button type="submit" className="btn btn-n btn-sm">Recompute the score</button>
                </form>
              </li>
            ))}
          </ul>
        </section>
      )}
      {error && <p className="status status-err" role="alert">The queue could not be read. Please reload the page.</p>}
      {rows.length === 0 ? (
        <div className="empty"><p>Nothing is waiting for review.</p></div>
      ) : (
        <div className="scroll">
          <table className="tbl">
            <thead>
              <tr><th scope="col">Venture</th><th scope="col">Evidence</th><th scope="col">Added on</th><th scope="col"><span className="sr-only">Review</span></th></tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id}>
                  <td>{r.ventures?.name ?? ""}</td>
                  <td><strong>{signalLabel(r.signal_code)}</strong>{r.summary ? <><br />{r.summary}</> : null}</td>
                  <td>{dateText(r.created_at)}</td>
                  <td><Link className="btn btn-i btn-sm" href={`/admin/evidence/${r.id}`}>Review</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </AppShell>
  );
}
