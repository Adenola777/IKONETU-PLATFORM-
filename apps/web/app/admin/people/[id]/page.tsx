import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { AppShell } from "@/components/app/shell";
import { ACCOUNT_STATUS_NAME, actionText, changeLines, entryReason, ROLE_NAME, rolesFor, type AccountStatus, type Role } from "@/lib/admin";
import { logError } from "@/lib/log";
import { dateText } from "@/lib/product";
import { requireStaff } from "@/lib/session";
import { RoleForm, StatusForm } from "./forms";

export const metadata: Metadata = { title: "Person", robots: { index: false } };
export const dynamic = "force-dynamic";

type Account = {
  user_id: string; full_name: string; email: string | null; role: Role; status: AccountStatus;
  created_at: string; last_sign_in_at: string | null; venture_id: string | null; venture_name: string | null; firm: string | null;
};
const DONE: Record<string, string> = {
  role: "The role is changed, and the change is in the audit log.",
  suspended: "The account is suspended, and the change is in the audit log.",
  active: "The account is active again. A founder's profile stays unpublished until the founder publishes it.",
};

type Entry = { id: number; actor_id: string | null; action: string; created_at: string; before: Record<string, unknown> | null; after: Record<string, unknown> | null };

/** One account: its details, a role change, a suspension, and its entries in the audit log. Admins only. */
export default async function PersonPage({
  params,
  searchParams,
}: {
  params: Promise<{ id: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { id } = await params;
  const done = DONE[String((await searchParams).done ?? "")];
  if (!/^[0-9a-f-]{36}$/.test(id)) notFound();
  const { supabase, user } = await requireStaff(true);
  const { data, error } = await supabase.rpc("admin_accounts", { p_user: id, p_limit: 1 });
  if (error) logError("admin.account_failed", { code: error.code });
  const a = ((data ?? []) as Account[])[0];
  if (!a) notFound();
  const [investor, log] = await Promise.all([
    supabase.from("investor_profiles").select("user_id").eq("user_id", id).maybeSingle(),
    supabase.from("audit_log").select("id, actor_id, action, created_at, before, after").eq("entity", "profiles").eq("entity_id", id)
      .order("id", { ascending: false }).limit(20),
  ]);
  const entries = (log.data ?? []) as Entry[];
  const actorIds = [...new Set(entries.map((e) => e.actor_id).filter(Boolean))] as string[];
  const actors = actorIds.length
    ? await supabase.from("profiles").select("user_id, full_name").in("user_id", actorIds)
    : { data: [] as { user_id: string; full_name: string }[] };
  const actorName = new Map((actors.data ?? []).map((p) => [p.user_id, p.full_name]));
  const self = a.user_id === user.id;
  const roles = rolesFor(a.role, { venture: Boolean(a.venture_id), investorProfile: Boolean(investor.data) });

  return (
    <AppShell role="admin" current="people">
      <Link className="back" href="/admin/people">Back to people</Link>
      <h1 className="app-title">{a.full_name}</h1>
      <p className="app-lede">{ROLE_NAME[a.role]} · {ACCOUNT_STATUS_NAME[a.status]} · {a.email ?? "No email address"}</p>
      {done && <p className="status status-ok" role="status" style={{ marginBottom: 24 }}>{done}</p>}

      <div className="side">
        <div className="stack">
          {self ? (
            <p className="status status-info" role="status">
              This is your own account. Nobody can change their own role or status, so another admin makes any change here.
            </p>
          ) : (
            <>
              <section className="card" aria-labelledby="role-h">
                <h2 id="role-h" className="app-h2">Role</h2>
                <p className="body2" style={{ marginBottom: 16 }}>
                  {a.full_name} is {a.role === "admin" ? "an admin" : `a ${a.role}`}. A person becomes a founder only if they have a
                  venture, and an investor only if they have investor details.
                </p>
                {roles.length > 0 ? (
                  <RoleForm id={a.user_id} roles={roles} founderNow={a.role === "founder"} />
                ) : (
                  <p className="body2" style={{ margin: 0 }}>No other role fits this account.</p>
                )}
              </section>

              <section className={`card${a.status === "suspended" ? " hold" : ""}`} aria-labelledby="status-h">
                <h2 id="status-h" className="app-h2">Status</h2>
                {a.status === "pending" ? (
                  <p className="body2" style={{ margin: 0 }}>
                    This investor is waiting for approval. <Link href="/admin/investors">Approve or decline on the Investors page</Link>.
                  </p>
                ) : a.status === "active" ? (
                  <>
                    <p className="body2" style={{ marginBottom: 16 }}>
                      The account is active. A suspended account can sign in but cannot change anything, and investors cannot see a
                      suspended founder&apos;s profile.
                    </p>
                    <StatusForm id={a.user_id} suspend founder={a.role === "founder"} />
                  </>
                ) : (
                  <>
                    <p className="body2" style={{ marginBottom: 16 }}>The account is suspended. Making it active again does not publish a founder&apos;s profile.</p>
                    <StatusForm id={a.user_id} suspend={false} founder={a.role === "founder"} />
                  </>
                )}
              </section>
            </>
          )}

          <section className="card" aria-labelledby="log-h">
            <h2 id="log-h" className="app-h2">Changes to this account</h2>
            {entries.length === 0 ? (
              <p className="body2" style={{ margin: 0 }}>The audit log holds no change to this account.</p>
            ) : (
              <ul className="log">
                {entries.map((e) => (
                  <li key={e.id}>
                    <time dateTime={e.created_at}>{dateText(e.created_at)}</time>
                    <div>
                      <p>{(e.actor_id && actorName.get(e.actor_id)) ?? "The system"} {actionText(e.action)}.</p>
                      <ul className="lines">
                        {changeLines(e.before, e.after).map((l) => <li key={l}>{l}</li>)}
                        {entryReason(e.after) && <li>Reason: {entryReason(e.after)}</li>}
                      </ul>
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </div>

        <aside className="card" aria-labelledby="acct-h">
          <h2 id="acct-h" className="app-h3">Account</h2>
          <dl className="kv kv-stack">
            <dt>Email address</dt><dd>{a.email ?? "None"}</dd>
            <dt>Joined</dt><dd>{dateText(a.created_at)}</dd>
            <dt>Last signed in</dt><dd>{a.last_sign_in_at ? dateText(a.last_sign_in_at) : "Not recorded"}</dd>
            {a.venture_id && <><dt>Venture</dt><dd><Link href={`/admin/founders/${a.venture_id}`}>{a.venture_name}</Link></dd></>}
            {investor.data && <><dt>Investor details</dt><dd>{a.firm ?? "No fund or firm given"}. <Link href="/admin/investors">Investors page</Link></dd></>}
          </dl>
        </aside>
      </div>
    </AppShell>
  );
}
