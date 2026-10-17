import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "@/components/app/shell";
import { STAGES } from "@/lib/account";
import { ACCOUNT_STATUS_NAME, ROLE_NAME, type AccountStatus, type Role } from "@/lib/admin";
import { COUNTRIES } from "@/lib/constants";
import { REVIEW_LANES, signalLabel } from "@/lib/forms";
import { clockText, dateText } from "@/lib/product";
import { requireStaff } from "@/lib/session";
import { HideForm, LiftForm } from "./hold-forms";

export const metadata: Metadata = { title: "Venture", robots: { index: false } };
export const dynamic = "force-dynamic";

type Venture = {
  id: string; founder_id: string; name: string; sector: string; stage: string; country: string;
  description: string | null; website: string | null; ask: string | null; created_at: string;
  published_at: string | null; hidden_at: string | null; hidden_reason: string | null; hidden_by: string | null;
};
type Evidence = { id: string; signal_code: string; summary: string | null; status: string; lane: string | null; created_at: string; decided_at: string | null };

const WAITING = ["submitted", "checking", "needs_review"];
const DONE: Record<string, string> = {
  hidden: "The profile is hidden from investors. The founder sees your reason on their dashboard.",
  lifted: "The hold is lifted. The founder can publish the profile again when they choose.",
};

function evidenceState(e: Evidence): string {
  if (WAITING.includes(e.status)) return "Waiting for review";
  if (e.status === "approved") return REVIEW_LANES.find((l) => l.code === e.lane)?.name ?? "Approved";
  if (e.status === "needs_more") return "More asked for";
  if (e.status === "rejected") return "Rejected";
  if (e.status === "expired") return "Expired";
  return e.status;
}

/**
 * Everything one venture holds, for staff: the founder's account, whether
 * investors see the profile, the pitch, every piece of evidence in every
 * status, recent updates and introductions by status. An admin can hide the
 * profile from investors here, or lift the hold.
 */
export default async function VentureStaffPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { id } = await params;
  const done = DONE[String((await searchParams).done ?? "")];
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const { supabase, profile } = await requireStaff();
  const admin = profile.role === "admin";
  const v = await supabase
    .from("ventures")
    .select("id, founder_id, name, sector, stage, country, description, website, ask, created_at, published_at, hidden_at, hidden_reason, hidden_by")
    .eq("id", id)
    .maybeSingle();
  if (!v.data) notFound();
  const venture = v.data as Venture;
  const [founder, holder, pitch, evidence, updates, intros, score] = await Promise.all([
    supabase.from("profiles").select("full_name, role, status, city, created_at").eq("user_id", venture.founder_id).maybeSingle(),
    venture.hidden_by
      ? supabase.from("profiles").select("full_name").eq("user_id", venture.hidden_by).maybeSingle()
      : Promise.resolve({ data: null }),
    supabase.from("pitches").select("duration_seconds, updated_at").eq("venture_id", id).maybeSingle(),
    supabase.from("evidence").select("id, signal_code, summary, status, lane, created_at, decided_at").eq("venture_id", id).order("created_at", { ascending: false }),
    supabase.from("venture_updates").select("body, created_at").eq("venture_id", id).order("created_at", { ascending: false }).limit(3),
    supabase.from("introductions").select("status").eq("venture_id", id),
    supabase.from("scores").select("total, league, computed_at").eq("venture_id", id).maybeSingle(),
  ]);
  const f = founder.data as { full_name: string; role: Role; status: AccountStatus; city: string | null; created_at: string } | null;
  const ev = (evidence.data ?? []) as Evidence[];
  const introCount = (s: string) => (intros.data ?? []).filter((i) => i.status === s).length;
  const country = COUNTRIES.find((c) => c.code === venture.country)?.name ?? venture.country;
  const stage = STAGES.find((s) => s.code === venture.stage)?.label ?? venture.stage;

  return (
    <AppShell role={admin ? "admin" : "reviewer"} current="founders">
      <Link className="back" href="/admin/founders">Back to founders</Link>
      <h1 className="app-title">{venture.name}</h1>
      <p className="app-lede">{venture.sector} · {stage} · {country} · on IkonetU since {dateText(venture.created_at)}</p>
      {done && <p className="status status-ok" role="status" style={{ marginBottom: 24 }}>{done}</p>}

      <div className="side">
        <div className="stack">
          <section className={`card${venture.hidden_at ? " hold" : ""}`} aria-labelledby="vis-h">
            <h2 id="vis-h" className="app-h2">Who can see this profile</h2>
            {venture.hidden_at ? (
              <>
                <p className="body2">
                  {holder.data?.full_name ?? "An admin"} hid this profile from investors on {dateText(venture.hidden_at)}. The founder
                  cannot publish it until an admin lifts the hold. The founder reads this reason on their dashboard:
                </p>
                <blockquote className="quote" style={{ margin: "12px 0 20px" }}>{venture.hidden_reason}</blockquote>
                {admin && <LiftForm id={venture.id} />}
              </>
            ) : (
              <>
                <p className="body2" style={{ marginBottom: admin ? 20 : 0 }}>
                  {venture.published_at
                    ? `Published. Approved investors have been able to find it since ${dateText(venture.published_at)}.`
                    : "Not published. Only the founder and IkonetU staff can see it."}
                </p>
                {admin && <HideForm id={venture.id} name={venture.name} />}
              </>
            )}
          </section>

          <section className="card" aria-labelledby="ev-h">
            <h2 id="ev-h" className="app-h2">Evidence ({ev.length})</h2>
            {ev.length === 0 ? (
              <p className="body2" style={{ margin: 0 }}>The founder has not added evidence yet.</p>
            ) : (
              <div className="scroll">
                <table className="tbl">
                  <thead><tr><th scope="col">Evidence</th><th scope="col">State</th><th scope="col">Added</th></tr></thead>
                  <tbody>
                    {ev.map((e) => (
                      <tr key={e.id}>
                        <td>
                          {WAITING.includes(e.status) ? <Link href={`/admin/evidence/${e.id}`}>{signalLabel(e.signal_code)}</Link> : signalLabel(e.signal_code)}
                          {e.summary && <span className="sub">{e.summary}</span>}
                        </td>
                        <td>{evidenceState(e)}{e.decided_at && <span className="sub">{dateText(e.decided_at)}</span>}</td>
                        <td>{dateText(e.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="card" aria-labelledby="up-h">
            <h2 id="up-h" className="app-h2">Latest progress updates</h2>
            {(updates.data ?? []).length === 0 ? (
              <p className="body2" style={{ margin: 0 }}>No updates yet.</p>
            ) : (
              <ul className="updates">
                {(updates.data ?? []).map((u) => (
                  <li key={u.created_at}><time dateTime={u.created_at}>{dateText(u.created_at)}</time><p>{u.body}</p></li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <aside className="stack" aria-label="The founder and the venture">
          <section className="card" aria-labelledby="f-h">
            <h2 id="f-h" className="app-h3">Founder</h2>
            {f ? (
              <dl className="kv kv-stack">
                <dt>Name</dt><dd>{f.full_name}</dd>
                <dt>Account</dt><dd>{ROLE_NAME[f.role]}, {ACCOUNT_STATUS_NAME[f.status].toLowerCase()}</dd>
                <dt>City</dt><dd>{f.city ?? "Not given"}</dd>
                <dt>Joined</dt><dd>{dateText(f.created_at)}</dd>
              </dl>
            ) : (
              <p className="body2">The founder's profile could not be read.</p>
            )}
            {admin && <Link className="tlink" href={`/admin/people/${venture.founder_id}`}>Change the account</Link>}
          </section>
          <section className="card" aria-labelledby="d-h">
            <h2 id="d-h" className="app-h3">On the profile</h2>
            <dl className="kv kv-stack">
              <dt>Pitch</dt><dd>{pitch.data ? `${clockText(pitch.data.duration_seconds)}, updated ${dateText(pitch.data.updated_at)}` : "None yet"}</dd>
              <dt>The ask</dt><dd>{venture.ask ?? "Not given"}</dd>
              <dt>Description</dt><dd>{venture.description ?? "Not given"}</dd>
              <dt>Website</dt><dd>{venture.website ? <a href={venture.website} target="_blank" rel="noopener nofollow">{venture.website}</a> : "Not given"}</dd>
              <dt>Score</dt><dd>{score.data ? `${score.data.total} of 1,000, ${score.data.league.toLowerCase()} league. Investors never see it.` : "Not computed yet"}</dd>
            </dl>
          </section>
          <section className="card" aria-labelledby="i-h">
            <h2 id="i-h" className="app-h3">Introductions</h2>
            <dl className="kv kv-stack">
              <dt>Waiting for the founder</dt><dd>{introCount("pending")}</dd>
              <dt>Accepted</dt><dd>{introCount("accepted")}</dd>
              <dt>Declined</dt><dd>{introCount("declined")}</dd>
              <dt>Withdrawn by the investor</dt><dd>{introCount("withdrawn")}</dd>
            </dl>
            <p className="hint">Staff see counts only. Nobody but the founder and the investor reads a conversation.</p>
          </section>
        </aside>
      </div>
    </AppShell>
  );
}
