import type { Metadata } from "next";
import Link from "next/link";
import { AppShell } from "@/components/app/shell";
import { ACTION_GROUPS, actionText, changeLines, entityHref, entryReason } from "@/lib/admin";
import { logError } from "@/lib/log";
import { requireStaff } from "@/lib/session";

export const metadata: Metadata = { title: "Audit log", robots: { index: false } };
export const dynamic = "force-dynamic";

const PAGE = 50;
const WHEN = new Intl.DateTimeFormat("en-GB", { day: "numeric", month: "long", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "UTC" });

type Entry = {
  id: number; actor_id: string | null; action: string; entity: string; entity_id: string | null;
  before: Record<string, unknown> | null; after: Record<string, unknown> | null; created_at: string;
};

/**
 * Every staff decision, newest first. The log is append-only in the database,
 * and only admins can read it. Older entries are reached page by page.
 */
export default async function AuditPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { supabase } = await requireStaff(true);
  const sp = await searchParams;
  const group = ACTION_GROUPS.find((g) => g.code === sp.group)?.code ?? null;
  const before = typeof sp.before === "string" && /^\d+$/.test(sp.before) ? Number(sp.before) : null;
  let query = supabase.from("audit_log").select("id, actor_id, action, entity, entity_id, before, after, created_at").order("id", { ascending: false }).limit(PAGE + 1);
  if (group) query = query.like("action", `${group}.%`);
  if (before) query = query.lt("id", before);
  const { data, error } = await query;
  if (error) logError("admin.audit_failed", { code: error.code });
  const all = (data ?? []) as Entry[];
  const entries = all.slice(0, PAGE);
  const more = all.length > PAGE;
  const actorIds = [...new Set(entries.map((e) => e.actor_id).filter(Boolean))] as string[];
  const actors = actorIds.length
    ? await supabase.from("profiles").select("user_id, full_name").in("user_id", actorIds)
    : { data: [] as { user_id: string; full_name: string }[] };
  const actorName = new Map((actors.data ?? []).map((p) => [p.user_id, p.full_name]));
  const last = entries[entries.length - 1];
  const older = more && last ? `/admin/audit?${new URLSearchParams({ ...(group ? { group } : {}), before: String(last.id) })}` : null;

  return (
    <AppShell role="admin" current="audit">
      <h1 className="app-title">Audit log</h1>
      <p className="app-lede">
        Every decision staff have made: investor approvals, evidence decisions, profile holds, role changes and suspensions. Nobody
        can change or remove an entry. Times are in UTC.
      </p>

      <form className="tools" action="/admin/audit">
        <div className="field field-s">
          <label htmlFor="a-group">Show</label>
          <select id="a-group" name="group" className="input" defaultValue={group ?? ""}>
            <option value="">Every decision</option>
            {ACTION_GROUPS.map((g) => <option key={g.code} value={g.code}>{g.label}</option>)}
          </select>
        </div>
        <button type="submit" className="btn btn-n">Show</button>
      </form>

      {error ? (
        <p className="status status-err" role="alert">The audit log could not be read. Please reload the page.</p>
      ) : entries.length === 0 ? (
        <div className="empty"><p>The audit log holds no entry{group ? " of this kind" : ""}{before ? " older than these" : ""}.</p></div>
      ) : (
        <div className="card">
          <ul className="log">
            {entries.map((e) => {
              const href = entityHref(e.entity, e.entity_id);
              const reason = entryReason(e.after);
              return (
                <li key={e.id}>
                  <time dateTime={e.created_at}>{WHEN.format(new Date(e.created_at))}</time>
                  <div>
                    <p>
                      {(e.actor_id && actorName.get(e.actor_id)) ?? "The system"} {actionText(e.action)}.{" "}
                      {href && <Link href={href}>Open the record</Link>}
                    </p>
                    <ul className="lines">
                      {changeLines(e.before, e.after).map((l) => <li key={l}>{l}</li>)}
                      {reason && <li>Reason: {reason}</li>}
                      {typeof e.after?.profiles_hidden === "number" && e.after.profiles_hidden > 0 && (
                        <li>Profiles taken out of investors&apos; view: {e.after.profiles_hidden}</li>
                      )}
                    </ul>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
      {(older || before) && (
        <nav className="pager" aria-label="Pages">
          {before ? <Link className="btn btn-n btn-sm" href={`/admin/audit${group ? `?group=${group}` : ""}`}>Newest entries</Link> : <span />}
          {older ? <Link className="btn btn-n btn-sm" href={older}>Older entries</Link> : <span />}
        </nav>
      )}
    </AppShell>
  );
}
