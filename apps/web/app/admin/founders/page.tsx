import type { Metadata } from "next";
import Link from "next/link";
import { AppShell } from "@/components/app/shell";
import { COUNTRIES } from "@/lib/constants";
import { logError } from "@/lib/log";
import { activityText, dateText } from "@/lib/product";
import { requireStaff } from "@/lib/session";

export const metadata: Metadata = { title: "Founders", robots: { index: false } };
export const dynamic = "force-dynamic";

const PAGE = 50;
const STATES = [
  { code: "all", label: "Every venture" },
  { code: "published", label: "Published to investors" },
  { code: "unpublished", label: "Not published" },
  { code: "hidden", label: "Hidden by IkonetU" },
] as const;

type Row = {
  venture_id: string; name: string; sector: string; country: string;
  founder_name: string; founder_status: "active" | "pending" | "suspended"; founder_role: string;
  published_at: string | null; hidden_at: string | null; has_pitch: boolean;
  evidence_total: number; evidence_waiting: number; evidence_reviewed: number;
  updates_90d: number; introductions: number; last_activity: string | null; total_count: number;
};

/** Every venture and its founder, sorted by name, for reviewers and admins. */
export default async function FoundersPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { supabase, profile } = await requireStaff();
  const sp = await searchParams;
  const q = typeof sp.q === "string" ? sp.q.slice(0, 80) : "";
  const state = STATES.find((s) => s.code === sp.state)?.code ?? "all";
  const page = Math.max(1, Number.parseInt(typeof sp.page === "string" ? sp.page : "1", 10) || 1);
  const { data, error } = await supabase.rpc("admin_ventures", { p_search: q || null, p_state: state, p_limit: PAGE, p_offset: (page - 1) * PAGE });
  if (error) logError("admin.ventures_failed", { code: error.code });
  const rows = (data ?? []) as Row[];
  const total = rows[0]?.total_count ?? 0;
  const now = new Date();
  const link = (p: number) => `/admin/founders?${new URLSearchParams({ ...(q ? { q } : {}), state, page: String(p) })}`;

  return (
    <AppShell role={profile.role === "admin" ? "admin" : "reviewer"} current="founders">
      <h1 className="app-title">Founders</h1>
      <p className="app-lede">
        Every venture and its founder, whether or not it is published. Open a venture to see everything it holds
        {profile.role === "admin" ? ", or to hide its profile from investors with a reason the founder reads." : "."}
      </p>

      <form className="tools" role="search" action="/admin/founders">
        <div className="field">
          <label htmlFor="f-q">Venture or founder</label>
          <input id="f-q" name="q" className="input" defaultValue={q} maxLength={80} />
        </div>
        <div className="field field-s">
          <label htmlFor="f-state">Show</label>
          <select id="f-state" name="state" className="input" defaultValue={state}>
            {STATES.map((s) => <option key={s.code} value={s.code}>{s.label}</option>)}
          </select>
        </div>
        <button type="submit" className="btn btn-n">Search</button>
      </form>

      {error ? (
        <p className="status status-err" role="alert">The list could not be read. Please reload the page.</p>
      ) : rows.length === 0 ? (
        <div className="empty"><p>No venture matches.</p></div>
      ) : (
        <>
          <p className="small" style={{ margin: "0 0 12px" }}>
            {total === 1 ? "One venture" : `${total} ventures`}{total > PAGE ? `, ${(page - 1) * PAGE + 1} to ${(page - 1) * PAGE + rows.length} shown` : ""}.
          </p>
          <div className="scroll">
            <table className="tbl">
              <thead>
                <tr>
                  <th scope="col">Venture</th><th scope="col">Founder</th><th scope="col">Investors see it</th>
                  <th scope="col">Evidence</th><th scope="col">Updates in 90 days</th><th scope="col">Introductions</th><th scope="col">Last activity</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.venture_id}>
                    <td>
                      <Link href={`/admin/founders/${r.venture_id}`}>{r.name}</Link>
                      <span className="sub">{r.sector} · {COUNTRIES.find((c) => c.code === r.country)?.name ?? r.country}</span>
                    </td>
                    <td>
                      {r.founder_name}
                      {r.founder_status !== "active" && <span className="sub"><span className="chip chip-n">Suspended</span></span>}
                      {r.founder_role !== "founder" && <span className="sub">Now {r.founder_role === "admin" ? "an admin" : `a ${r.founder_role}`}</span>}
                    </td>
                    <td>
                      {r.hidden_at ? (
                        <span className="chip chip-f">Hidden by IkonetU</span>
                      ) : r.published_at ? (
                        <>Since {dateText(r.published_at)}</>
                      ) : (
                        <>No{r.has_pitch ? "" : <span className="sub">No pitch yet</span>}</>
                      )}
                    </td>
                    <td>
                      {r.evidence_total}
                      <span className="sub">{r.evidence_reviewed} approved, {r.evidence_waiting} waiting</span>
                    </td>
                    <td>{r.updates_90d}</td>
                    <td>{r.introductions}</td>
                    <td>{activityText(r.last_activity, now)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {total > PAGE && (
            <nav className="pager" aria-label="Pages">
              {page > 1 ? <Link className="btn btn-n btn-sm" href={link(page - 1)}>Previous page</Link> : <span />}
              {page * PAGE < total ? <Link className="btn btn-n btn-sm" href={link(page + 1)}>Next page</Link> : <span />}
            </nav>
          )}
        </>
      )}
    </AppShell>
  );
}
