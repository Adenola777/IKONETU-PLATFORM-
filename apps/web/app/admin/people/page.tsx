import type { Metadata } from "next";
import Link from "next/link";
import { AppShell } from "@/components/app/shell";
import { ACCOUNT_STATUS_NAME, ROLE_NAME, type AccountStatus, type Role } from "@/lib/admin";
import { logError } from "@/lib/log";
import { dateText } from "@/lib/product";
import { requireStaff } from "@/lib/session";

export const metadata: Metadata = { title: "People and roles", robots: { index: false } };
export const dynamic = "force-dynamic";

const PAGE = 50;
const ROLES: Role[] = ["founder", "investor", "reviewer", "admin"];
const STATUSES: AccountStatus[] = ["active", "pending", "suspended"];

type Row = {
  user_id: string; full_name: string; email: string | null; role: Role; status: AccountStatus;
  created_at: string; last_sign_in_at: string | null; venture_name: string | null; firm: string | null; total_count: number;
};

/** Every account, newest first, with its email address. Admins only. */
export default async function PeoplePage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { supabase } = await requireStaff(true);
  const sp = await searchParams;
  const q = typeof sp.q === "string" ? sp.q.slice(0, 80) : "";
  const role = ROLES.find((r) => r === sp.role) ?? null;
  const status = STATUSES.find((s) => s === sp.status) ?? null;
  const page = Math.max(1, Number.parseInt(typeof sp.page === "string" ? sp.page : "1", 10) || 1);
  const { data, error } = await supabase.rpc("admin_accounts", {
    p_search: q || null, p_role: role, p_status: status, p_limit: PAGE, p_offset: (page - 1) * PAGE,
  });
  if (error) logError("admin.accounts_failed", { code: error.code });
  const rows = (data ?? []) as Row[];
  const total = rows[0]?.total_count ?? 0;
  const link = (p: number) =>
    `/admin/people?${new URLSearchParams({ ...(q ? { q } : {}), ...(role ? { role } : {}), ...(status ? { status } : {}), page: String(p) })}`;

  return (
    <AppShell role="admin" current="people">
      <h1 className="app-title">People and roles</h1>
      <p className="app-lede">
        Every account that has finished sign-up, newest first. Open a person to make them a reviewer or an admin, or to suspend
        their account. You cannot change your own account. Investors waiting for approval are on the Investors page.
      </p>

      <form className="tools" role="search" action="/admin/people">
        <div className="field">
          <label htmlFor="p-q">Name or email address</label>
          <input id="p-q" name="q" className="input" defaultValue={q} maxLength={80} />
        </div>
        <div className="field field-s">
          <label htmlFor="p-role">Role</label>
          <select id="p-role" name="role" className="input" defaultValue={role ?? ""}>
            <option value="">Any role</option>
            {ROLES.map((r) => <option key={r} value={r}>{ROLE_NAME[r]}</option>)}
          </select>
        </div>
        <div className="field field-s">
          <label htmlFor="p-status">Status</label>
          <select id="p-status" name="status" className="input" defaultValue={status ?? ""}>
            <option value="">Any status</option>
            {STATUSES.map((s) => <option key={s} value={s}>{ACCOUNT_STATUS_NAME[s]}</option>)}
          </select>
        </div>
        <button type="submit" className="btn btn-n">Search</button>
      </form>

      {error ? (
        <p className="status status-err" role="alert">The list could not be read. Please reload the page.</p>
      ) : rows.length === 0 ? (
        <div className="empty"><p>Nobody matches.</p></div>
      ) : (
        <>
          <p className="small" style={{ margin: "0 0 12px" }}>
            {total === 1 ? "One account" : `${total} accounts`}{total > PAGE ? `, ${(page - 1) * PAGE + 1} to ${(page - 1) * PAGE + rows.length} shown` : ""}.
          </p>
          <div className="scroll">
            <table className="tbl">
              <thead>
                <tr>
                  <th scope="col">Person</th><th scope="col">Role</th><th scope="col">Status</th>
                  <th scope="col">Venture or firm</th><th scope="col">Joined</th><th scope="col">Last signed in</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.user_id}>
                    <td><Link href={`/admin/people/${r.user_id}`}>{r.full_name}</Link><span className="sub">{r.email ?? "No email address"}</span></td>
                    <td>{ROLE_NAME[r.role]}</td>
                    <td>{r.status === "active" ? ACCOUNT_STATUS_NAME.active : <span className="chip chip-n">{ACCOUNT_STATUS_NAME[r.status]}</span>}</td>
                    <td>{r.venture_name ?? r.firm ?? ""}</td>
                    <td>{dateText(r.created_at)}</td>
                    <td>{r.last_sign_in_at ? dateText(r.last_sign_in_at) : "Not recorded"}</td>
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
