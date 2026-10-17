import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { RUBRIC_V2 } from "@ikonetu/score-engine";
import { AppShell } from "@/components/app/shell";
import { Icon } from "@/components/site/icons";
import { signalLabel } from "@/lib/forms";
import { areaLabel, dateText } from "@/lib/product";
import { requireStaff } from "@/lib/session";
import { DecisionForm } from "./decision-form";

export const metadata: Metadata = { title: "Review evidence", robots: { index: false } };
export const dynamic = "force-dynamic";

type Ev = {
  id: string; venture_id: string; signal_code: string; status: string; summary: string | null; source_ref: string | null; created_at: string;
  ventures: { name: string; founder_id: string } | null;
  evidence_files: { id: string; storage_path: string; mime_type: string; size_bytes: number; sha256: string }[];
};

export default async function ReviewEvidencePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const { supabase, user, profile } = await requireStaff();
  const res = await supabase
    .from("evidence")
    .select("id, venture_id, signal_code, status, summary, source_ref, created_at, ventures(name, founder_id), evidence_files(id, storage_path, mime_type, size_bytes, sha256)")
    .eq("id", id)
    .maybeSingle();
  const e = res.data as unknown as Ev | null;
  if (!e) notFound();
  const signal = RUBRIC_V2.signals.find((s) => s.code === e.signal_code);
  // Files open through links that last five minutes (SRD SEC-E2).
  const files = await Promise.all(
    e.evidence_files.map(async (f) => {
      const s = await supabase.storage.from("evidence").createSignedUrl(f.storage_path, 300);
      return { ...f, url: s.data?.signedUrl ?? null };
    }),
  );
  // The same file used elsewhere, found by its SHA-256.
  const sums = e.evidence_files.map((f) => f.sha256);
  const twins = sums.length
    ? await supabase.from("evidence_files").select("evidence_id, sha256").in("sha256", sums).neq("evidence_id", e.id).limit(20)
    : { data: [] };
  const own = e.ventures?.founder_id === user.id;
  const open = ["submitted", "checking", "needs_review"].includes(e.status);

  return (
    <AppShell role={profile.role === "admin" ? "admin" : "reviewer"} current="queue">
      <Link href="/admin/evidence" className="back"><Icon name="arrow-left" size={16} /> Evidence to review</Link>
      <p className="lbl" style={{ marginBottom: 8 }}>{areaLabel(signal?.category ?? "")} · {e.ventures?.name}</p>
      <h1 className="app-title">{signalLabel(e.signal_code)}</h1>
      <div className="side">
        <section className="card stack-s" aria-labelledby="what-h">
          <h2 id="what-h" className="app-h2">What the founder sent</h2>
          <p className="body2">{e.summary ?? "No description."}</p>
          <p className="small" style={{ margin: 0 }}>Added on {dateText(e.created_at)}.</p>
          {e.source_ref && <p className="body2">Link: <a href={e.source_ref} target="_blank" rel="noopener nofollow noreferrer">{e.source_ref}</a></p>}
          {files.length === 0 ? (
            <p className="body2">No files.</p>
          ) : (
            <ul className="ev">
              {files.map((f, i) => (
                <li key={f.id}>
                  <span className="what">File {i + 1}, {f.mime_type === "application/pdf" ? "PDF" : f.mime_type === "image/png" ? "PNG" : "JPEG"}, {(f.size_bytes / 1024 / 1024).toFixed(1)} MB</span>
                  <p className="small" style={{ margin: "4px 0 0" }}>
                    {f.url ? <a href={f.url} target="_blank" rel="noopener noreferrer">Open the file</a> : "The file could not be opened."} The link lasts five minutes.
                  </p>
                </li>
              ))}
            </ul>
          )}
          {(twins.data?.length ?? 0) > 0 && (
            <p className="status status-err" role="note">
              The same file is attached to {twins.data?.length} other {twins.data?.length === 1 ? "piece" : "pieces"} of evidence. Check that it belongs to this venture.
            </p>
          )}
        </section>
        <aside className="card" aria-labelledby="dec-h">
          <h2 id="dec-h" className="app-h2">Your decision</h2>
          {own ? (
            <p className="body2">This is evidence on your own venture, so someone else must decide it.</p>
          ) : !open ? (
            <p className="body2">This evidence has already been decided.</p>
          ) : (
            <DecisionForm id={e.id} mode={signal?.mode ?? "fixed"} />
          )}
        </aside>
      </div>
    </AppShell>
  );
}
