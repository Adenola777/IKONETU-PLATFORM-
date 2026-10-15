import type { Metadata } from "next";
import { AppShell } from "@/components/app/shell";
import { StatusChip } from "@/components/app/ui";
import { signalLabel } from "@/lib/forms";
import { areaLabel, dateText } from "@/lib/product";
import { requireFounder } from "@/lib/session";
import { RUBRIC_V2 } from "@ikonetu/score-engine";
import { EvidenceForm } from "./form";

export const metadata: Metadata = { title: "Your evidence", robots: { index: false } };
export const dynamic = "force-dynamic";

type Row = {
  id: string; signal_code: string; status: string; lane: string | null; summary: string | null; source_ref: string | null;
  public_note: string | null; reason: string | null; decided_at: string | null; created_at: string; evidence_files: { id: string }[];
};

const areaOf = (code: string) => RUBRIC_V2.signals.find((s) => s.code === code)?.category ?? "";

/** What the founder sees about each item. Investors see less: venture_evidence decides that. */
function founderStatus(r: Row): { text: string; investors: "third_party" | "reviewed" | "submitted" | null } {
  switch (r.status) {
    case "approved":
      return r.lane === "government" || r.lane === "source"
        ? { text: "Approved from an outside source.", investors: "third_party" }
        : { text: "Approved by an IkonetU reviewer.", investors: "reviewed" };
    case "needs_more":
      return { text: "A reviewer asked for more. Investors do not see this item. Add the evidence again with what was asked for.", investors: null };
    case "rejected":
      return { text: "Not accepted. Investors do not see this item.", investors: null };
    case "expired":
      return { text: "Expired. Investors no longer see this item.", investors: null };
    default:
      return { text: "Waiting for a reviewer.", investors: "submitted" };
  }
}

export default async function EvidencePage() {
  const { supabase, venture } = await requireFounder();
  const { data } = await supabase
    .from("evidence")
    .select("id, signal_code, status, lane, summary, source_ref, public_note, reason, decided_at, created_at, evidence_files(id)")
    .eq("venture_id", venture.id)
    .order("created_at", { ascending: false });
  const rows = (data ?? []) as Row[];

  return (
    <AppShell role="founder" current="evidence">
      <h1 className="app-title">Your evidence</h1>
      <p className="app-lede">
        Each piece of evidence shows investors one of three statuses: founder submitted until a reviewer has looked at it, then
        platform reviewed or third-party evidence available. Investors see what it shows, your sentence and its status, never your
        files.
      </p>
      <div className="side">
        <section aria-labelledby="list-h" className="stack">
          <h2 id="list-h" className="app-h2">Added so far ({rows.length})</h2>
          {rows.length === 0 ? (
            <div className="empty"><p>You have not added any evidence yet.</p><p>Start with what an investor would ask for first, such as your company registration or revenue.</p></div>
          ) : (
            <ul className="reqs">
              {rows.map((r) => {
                const s = founderStatus(r);
                return (
                  <li key={r.id} className="card">
                    <p className="lbl" style={{ marginBottom: 6 }}>{areaLabel(areaOf(r.signal_code))}</p>
                    <h3 className="app-h3">{signalLabel(r.signal_code)}</h3>
                    {r.summary && <p className="body2" style={{ margin: "0 0 8px" }}>{r.summary}</p>}
                    <div className="row" style={{ marginBottom: 8 }}>
                      {s.investors ? <StatusChip status={s.investors} /> : <span className="chip chip-none">Not shown to investors</span>}
                    </div>
                    <p className="small" style={{ margin: 0 }}>{s.text}</p>
                    {r.public_note && <p className="note">What the reviewer compared: {r.public_note}</p>}
                    {r.reason && <p className="note" style={{ background: "#FEF3F2", color: "#B42318" }}>The reviewer said: {r.reason}</p>}
                    <p className="small" style={{ margin: "8px 0 0" }}>
                      Added on {dateText(r.created_at)}
                      {r.decided_at ? `, decided on ${dateText(r.decided_at)}` : ""} · {r.evidence_files.length} {r.evidence_files.length === 1 ? "file" : "files"}
                      {r.source_ref ? <> · <a href={r.source_ref} target="_blank" rel="noopener nofollow">link</a></> : null}
                    </p>
                  </li>
                );
              })}
            </ul>
          )}
        </section>
        <aside className="card" aria-labelledby="add-h">
          <h2 id="add-h" className="app-h2">Add evidence</h2>
          <EvidenceForm />
        </aside>
      </div>
    </AppShell>
  );
}
