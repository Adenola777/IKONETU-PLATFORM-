import type { Metadata } from "next";
import Link from "next/link";
import { AppShell } from "@/components/app/shell";
import { logError } from "@/lib/log";
import { daysBetween } from "@/lib/product";
import { requireStaff } from "@/lib/session";

export const metadata: Metadata = { title: "Overview", robots: { index: false } };
export const dynamic = "force-dynamic";

type Overview = {
  founders: number; ventures: number; ventures_published: number; ventures_hidden: number;
  investors_pending: number; investors_active: number; investors_suspended: number;
  staff: number; accounts_suspended: number;
  evidence_waiting: number; evidence_oldest_at: string | null; scores_to_update: number;
  introductions_pending: number; introductions_30d: number; accepted_30d: number; declined_30d: number;
  north_star_30d: number; north_star_months: { month: string; count: number }[] | null;
  waitlist: number; investor_interest: number;
};

/**
 * What needs staff now, the north star, and the counts behind it. Every
 * figure comes from admin_overview(), which returns counts only.
 */
export default async function AdminOverviewPage() {
  const { supabase, profile } = await requireStaff();
  const admin = profile.role === "admin";
  const { data, error } = await supabase.rpc("admin_overview");
  if (error) logError("admin.overview_failed", { code: error.code });
  const o = (Array.isArray(data) ? data[0] : data) as Overview | undefined;

  return (
    <AppShell role={admin ? "admin" : "reviewer"} current="overview">
      <h1 className="app-title">Overview</h1>
      <p className="app-lede">
        What is waiting for staff, how many introductions reach founders with reviewed evidence, and the accounts behind them. The
        figures are counted when the page opens.
      </p>
      {!o ? (
        <p className="status status-err" role="alert">The overview could not be read. Please reload the page.</p>
      ) : (
        <div className="stack" style={{ gap: 48 }}>
          <section aria-labelledby="wait-h">
            <h2 id="wait-h" className="app-h2">Waiting for staff</h2>
            <div className="grid3 tiles">
              <Tile
                label="Evidence to review"
                value={o.evidence_waiting}
                note={o.evidence_oldest_at ? `The oldest was sent ${ageText(o.evidence_oldest_at)}.` : "Nothing is waiting."}
                href="/admin/evidence"
                link="Open the queue"
              />
              <Tile
                label="Investors waiting for approval"
                value={o.investors_pending}
                note={o.investors_pending ? "An admin checks each one before it can browse." : "Nobody is waiting."}
                href={admin ? "/admin/investors" : undefined}
                link="Approve or decline"
              />
              <Tile
                label="Scores to update"
                value={o.scores_to_update}
                note={o.scores_to_update ? "A decision was saved but the score did not update." : "Every score is up to date."}
                href="/admin/evidence"
                link="Recompute them"
              />
            </div>
          </section>

          <section aria-labelledby="ns-h" className="card ns-card">
            <h2 id="ns-h" className="app-h2">The north star</h2>
            <p className="body2" style={{ margin: "0 0 20px", maxWidth: 720 }}>
              Introductions a founder accepted when their profile already held evidence that an IkonetU reviewer or an outside source
              had confirmed. IkonetU stops counting there, because no money moves through it.
            </p>
            <div className="ns-grid">
              <p className="ns-big">
                <span className="ns-num">{o.north_star_30d}</span>
                <span className="ns-lbl">in the last 30 days</span>
              </p>
              <MonthBars months={o.north_star_months ?? []} />
            </div>
          </section>

          <section aria-labelledby="intro-h">
            <h2 id="intro-h" className="app-h2">Introductions</h2>
            <dl className="counts">
              <Count label="Requested in the last 30 days" value={o.introductions_30d} />
              <Count label="Accepted in the last 30 days" value={o.accepted_30d} />
              <Count label="Declined in the last 30 days" value={o.declined_30d} />
              <Count label="Waiting for the founder now" value={o.introductions_pending} />
            </dl>
            <p className="hint" style={{ marginTop: 12 }}>Staff see counts only. Nobody but the founder and the investor reads a conversation.</p>
          </section>

          <section aria-labelledby="people-h">
            <h2 id="people-h" className="app-h2">Founders and investors</h2>
            <dl className="counts">
              <Count label="Active founders" value={o.founders} href="/admin/founders" />
              <Count label="Ventures published to investors" value={o.ventures_published} of={o.ventures} href="/admin/founders?state=published" />
              <Count label="Profiles hidden by IkonetU" value={o.ventures_hidden} href="/admin/founders?state=hidden" />
              <Count label="Approved investors" value={o.investors_active} href={admin ? "/admin/investors" : undefined} />
              <Count label="Investors not approved" value={o.investors_suspended} href={admin ? "/admin/investors" : undefined} />
              <Count label="Suspended accounts" value={o.accounts_suspended} href={admin ? "/admin/people?status=suspended" : undefined} />
              <Count label="Active staff" value={o.staff} />
              <Count label="Waitlist sign-ups" value={o.waitlist} />
              <Count label="Rows on the retired investor interest list" value={o.investor_interest} />
            </dl>
          </section>
        </div>
      )}
    </AppShell>
  );
}

function ageText(iso: string): string {
  const d = daysBetween(new Date(iso), new Date());
  return d === 0 ? "today" : d === 1 ? "yesterday" : `${d} days ago`;
}

function Tile({ label, value, note, href, link }: { label: string; value: number; note: string; href?: string; link: string }) {
  return (
    <div className={`card tile${value > 0 ? " tile-due" : ""}`}>
      <p className="tile-lbl">{label}</p>
      <p className="tile-num">{value}</p>
      <p className="small" style={{ margin: 0 }}>{note}</p>
      {href && value > 0 && <Link href={href} className="tlink" style={{ marginTop: 8 }}>{link}</Link>}
    </div>
  );
}

function Count({ label, value, of, href }: { label: string; value: number; of?: number; href?: string }) {
  const text = of === undefined ? String(value) : `${value} of ${of}`;
  return (
    <div className="count">
      <dt>{label}</dt>
      <dd>{href ? <Link href={href}>{text}</Link> : text}</dd>
    </div>
  );
}

const MONTH = new Intl.DateTimeFormat("en-GB", { month: "short", timeZone: "UTC" });
const MONTH_LONG = new Intl.DateTimeFormat("en-GB", { month: "long", year: "numeric", timeZone: "UTC" });

/**
 * The last six months as bars drawn to scale from zero, one series, so the
 * title names it and no legend is needed. Each bar carries its count, and the
 * table under it gives the same figures for a screen reader.
 */
function MonthBars({ months }: { months: { month: string; count: number }[] }) {
  const max = Math.max(1, ...months.map((m) => m.count));
  const W = 360, H = 160, top = 22, base = 132, bw = 36, gap = (W - bw * months.length) / months.length;
  return (
    <figure className="ns-chart">
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-labelledby="ns-chart-t">
        <title id="ns-chart-t">The north star by month, for the last six months</title>
        <line x1="0" x2={W} y1={base} y2={base} className="ns-axis" />
        {months.map((m, i) => {
          const h = ((base - top) * m.count) / max;
          const x = gap / 2 + i * (bw + gap);
          const date = new Date(`${m.month}-01T00:00:00Z`);
          return (
            <g key={m.month}>
              <title>{`${MONTH_LONG.format(date)}: ${m.count}`}</title>
              {m.count > 0 && <path d={bar(x, base, bw, h)} className="ns-bar" />}
              <text x={x + bw / 2} y={base - h - 6} textAnchor="middle" className="ns-val">{m.count}</text>
              <text x={x + bw / 2} y={base + 18} textAnchor="middle" className="ns-mon">{MONTH.format(date)}</text>
            </g>
          );
        })}
      </svg>
      {/* A table cannot shrink to the 1 px of .sr-only, so it sits in a clipped box. */}
      <div className="sr-only">
        <table>
          <caption>The north star by month</caption>
          <thead><tr><th scope="col">Month</th><th scope="col">Accepted introductions to founders with reviewed evidence</th></tr></thead>
          <tbody>
            {months.map((m) => (
              <tr key={m.month}><td>{MONTH_LONG.format(new Date(`${m.month}-01T00:00:00Z`))}</td><td>{m.count}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}

/** A bar anchored to the baseline, with its top corners rounded by four pixels. */
function bar(x: number, base: number, w: number, h: number): string {
  const r = Math.min(4, h, w / 2);
  const t = base - h;
  return `M${x} ${base}V${t + r}Q${x} ${t} ${x + r} ${t}H${x + w - r}Q${x + w} ${t} ${x + w} ${t + r}V${base}Z`;
}
