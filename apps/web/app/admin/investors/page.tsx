import type { Metadata } from "next";
import { AppShell } from "@/components/app/shell";
import { COUNTRIES } from "@/lib/constants";
import { BASED_IN } from "@/lib/investor-profile";
import { dateText, INVESTOR_TYPE_NAME } from "@/lib/product";
import { STAGES } from "@/lib/account";
import { requireStaff } from "@/lib/session";
import { decideInvestor } from "./actions";

export const metadata: Metadata = { title: "Investors", robots: { index: false } };
export const dynamic = "force-dynamic";

type Row = {
  user_id: string;
  full_name: string;
  status: "pending" | "active" | "suspended";
  created_at: string;
  investor_profiles: {
    investor_type: string; firm: string | null; website: string | null; based_in: string; sectors: string[];
    stages: string[]; countries: string[]; cheque_size: string; thesis: string | null;
  } | null;
};

const STATUS_NAME = { pending: "Waiting for approval", active: "Approved", suspended: "Not approved" } as const;
const place = (code: string) => BASED_IN.find((c) => c.code === code)?.name ?? code;
const stage = (code: string) => STAGES.find((s) => s.code === code)?.label ?? code;
const country = (code: string) => COUNTRIES.find((c) => c.code === code)?.name ?? code;

/** Admins approve or decline investor accounts. Pending accounts come first, oldest first. */
export default async function AdminInvestorsPage() {
  const { supabase, profile } = await requireStaff(true);
  const { data, error } = await supabase
    .from("profiles")
    .select("user_id, full_name, status, created_at, investor_profiles(investor_type, firm, website, based_in, sectors, stages, countries, cheque_size, thesis)")
    .eq("role", "investor")
    .order("created_at", { ascending: true })
    .limit(200);
  const rows = (data ?? []) as unknown as Row[];
  const pending = rows.filter((r) => r.status === "pending");
  const decided = rows.filter((r) => r.status !== "pending").reverse();

  return (
    <AppShell role={profile.role === "admin" ? "admin" : "reviewer"} current="investors">
      <h1 className="app-title">Investors</h1>
      <p className="app-lede">
        An investor account can browse published founder profiles and request introductions once you approve it. Check that the
        person and any fund or firm they name exist before you approve. Each decision goes to the audit log.
      </p>
      {error && <p className="status status-err" role="alert">The investor list could not be read. Please reload the page.</p>}

      <section aria-labelledby="pending-h" className="stack">
        <h2 id="pending-h" className="app-h2">Waiting for approval ({pending.length})</h2>
        {pending.length === 0 ? (
          <div className="empty"><p>No investor is waiting for approval.</p></div>
        ) : (
          <ul className="reqs">
            {pending.map((r) => (
              <li key={r.user_id} className="card">
                <InvestorDetails row={r} />
                <div className="row" style={{ marginTop: 16 }}>
                  <form action={decideInvestor}>
                    <input type="hidden" name="user" value={r.user_id} />
                    <input type="hidden" name="approve" value="yes" />
                    <button type="submit" className="btn btn-i btn-sm">Approve {r.full_name}</button>
                  </form>
                  <form action={decideInvestor}>
                    <input type="hidden" name="user" value={r.user_id} />
                    <input type="hidden" name="approve" value="no" />
                    <button type="submit" className="btn btn-n btn-sm">Decline</button>
                  </form>
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <section aria-labelledby="decided-h" className="stack" style={{ marginTop: 48 }}>
        <h2 id="decided-h" className="app-h2">Decided</h2>
        {decided.length === 0 ? (
          <div className="empty"><p>No investor has been approved or declined yet.</p></div>
        ) : (
          <div className="scroll">
            <table className="tbl">
              <thead>
                <tr><th scope="col">Investor</th><th scope="col">Type</th><th scope="col">Status</th><th scope="col">Change</th></tr>
              </thead>
              <tbody>
                {decided.map((r) => (
                  <tr key={r.user_id}>
                    <td>{r.full_name}{r.investor_profiles?.firm ? `, ${r.investor_profiles.firm}` : ""}</td>
                    <td>{INVESTOR_TYPE_NAME[r.investor_profiles?.investor_type ?? ""] ?? ""}</td>
                    <td>{STATUS_NAME[r.status]}</td>
                    <td>
                      <form action={decideInvestor}>
                        <input type="hidden" name="user" value={r.user_id} />
                        <input type="hidden" name="approve" value={r.status === "active" ? "no" : "yes"} />
                        <button type="submit" className="linkbtn">{r.status === "active" ? `Suspend ${r.full_name}` : `Approve ${r.full_name}`}</button>
                      </form>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </AppShell>
  );
}

function InvestorDetails({ row }: { row: Row }) {
  const d = row.investor_profiles;
  return (
    <>
      <h3 className="app-h3">{row.full_name}</h3>
      <p className="small" style={{ margin: "0 0 12px" }}>Sent on {dateText(row.created_at)}</p>
      {d ? (
        <dl className="kv">
          <dt>Type</dt><dd>{INVESTOR_TYPE_NAME[d.investor_type] ?? d.investor_type}</dd>
          <dt>Fund or firm</dt><dd>{d.firm ?? "None given"}</dd>
          <dt>Website</dt><dd>{d.website ? <a href={d.website} target="_blank" rel="noopener nofollow">{d.website}</a> : "None given"}</dd>
          <dt>Based in</dt><dd>{place(d.based_in)}</dd>
          <dt>Sectors</dt><dd>{d.sectors.join(", ")}</dd>
          <dt>Stages</dt><dd>{d.stages.length ? d.stages.map(stage).join(", ") : "Any"}</dd>
          <dt>Countries</dt><dd>{d.countries.length ? d.countries.map(country).join(", ") : "Any"}</dd>
          <dt>Cheque size</dt><dd>{d.cheque_size}</dd>
          <dt>Looks for</dt><dd>{d.thesis ?? "Not given"}</dd>
        </dl>
      ) : (
        <p className="body2">This person has not finished their investor details.</p>
      )}
    </>
  );
}
