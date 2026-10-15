import type { Metadata } from "next";
import Link from "next/link";
import { AppShell } from "@/components/app/shell";
import { signalLabel } from "@/lib/forms";
import { dateText } from "@/lib/product";
import { requireStaff } from "@/lib/session";

export const metadata: Metadata = { title: "Evidence to review", robots: { index: false } };
export const dynamic = "force-dynamic";

type Row = { id: string; signal_code: string; summary: string | null; created_at: string; ventures: { name: string } | null };

/** Evidence waiting for a decision, oldest first. */
export default async function EvidenceQueuePage() {
  const { supabase, profile } = await requireStaff();
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
