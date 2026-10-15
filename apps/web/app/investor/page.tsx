import type { Metadata } from "next";
import Link from "next/link";
import { AppShell } from "@/components/app/shell";
import { AreaMeter, MeterLegend } from "@/components/app/ui";
import { PreviewThumb } from "@/components/app/preview-thumb";
import { STAGES } from "@/lib/account";
import { COUNTRIES } from "@/lib/constants";
import { filterCount, matchText, PAGE_SIZE, parseFilters, queryString, rpcArgs } from "@/lib/discovery";
import { activityText, clockText, isRecent, isShownStatus, type AreaSummary } from "@/lib/product";
import { requireInvestor } from "@/lib/session";
import { DiscoveryFilters } from "./filters";

export const metadata: Metadata = { title: "Discover founders", robots: { index: false } };
export const dynamic = "force-dynamic";

type Row = {
  venture_id: string; name: string; sector: string; stage: string; country: string; description: string | null; ask: string | null;
  founder_name: string; city: string | null; pitch_seconds: number | null; last_activity: string | null;
  updates_90d: number; areas: AreaSummary[]; total_count: number;
};

const country = (code: string) => COUNTRIES.find((c) => c.code === code)?.name ?? code;
const stage = (code: string) => STAGES.find((s) => s.code === code)?.label ?? code;
const consistency = (n: number) => (n === 0 ? "no updates in 90 days" : `${n} ${n === 1 ? "update" : "updates"} in 90 days`);

/** Published founder profiles, filtered and sorted by company name. Nothing here is ranked. */
export default async function DiscoverPage({ searchParams }: { searchParams: Promise<Record<string, string | string[] | undefined>> }) {
  const { supabase } = await requireInvestor();
  const filters = parseFilters(await searchParams);
  const { data, error } = await supabase.rpc("discover_ventures", rpcArgs(filters));
  const rows = ((data ?? []) as Row[]).map((r) => ({ ...r, areas: (r.areas ?? []).filter((a) => isShownStatus(a.status)) }));
  // Each card's muted preview plays from a signed link, made only for the pitches on this page.
  const pitches = rows.length
    ? await supabase.from("pitches").select("venture_id, storage_path, transcript, duration_seconds").in("venture_id", rows.map((r) => r.venture_id))
    : { data: [] };
  const previews = new Map<string, { src: string | null; transcript: string; duration: number }>();
  await Promise.all(
    (pitches.data ?? []).map(async (p) => {
      const signed = await supabase.storage.from("pitches").createSignedUrl(p.storage_path, 3600);
      previews.set(p.venture_id, { src: signed.data?.signedUrl ?? null, transcript: p.transcript, duration: Number(p.duration_seconds) });
    }),
  );
  const total = rows[0]?.total_count ?? 0;
  const filtered = filterCount(filters) > 0;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  const now = new Date();

  return (
    <AppShell role="investor" current="discover">
      <h1 className="app-title">Discover founders</h1>
      <p className="app-lede">
        Founders who have published their profile. Choices inside one filter widen the list, and filters in different groups narrow
        it. Results are sorted by company name, never by a score.
      </p>
      <div className="disc">
        <DiscoveryFilters filters={filters} chosen={filterCount(filters)} />
        <section aria-labelledby="res-h" className="stack">
          <h2 id="res-h" className="sr-only">Results</h2>
          <div className="row" style={{ justifyContent: "space-between" }}>
            <p role="status" className="small" style={{ margin: 0 }}>{error ? "The list could not be loaded. Please reload the page." : matchText(total, filtered)}</p>
            {filtered && <Link className="tlink" href="/investor">Clear filters</Link>}
          </div>
          <MeterLegend />
          {!error && rows.length === 0 ? (
            <div className="empty">
              <p>{filtered ? "No founder matches these filters." : "No founder has published a profile yet."}</p>
              {filtered && <p><Link href="/investor">Clear the filters</Link> to see every published founder.</p>}
            </div>
          ) : (
            <ul className="results">
              {rows.map((r) => (
                <li key={r.venture_id} className="res">
                  <PreviewThumb
                    href={`/investor/ventures/${r.venture_id}`}
                    src={previews.get(r.venture_id)?.src ?? null}
                    transcript={previews.get(r.venture_id)?.transcript ?? ""}
                    duration={previews.get(r.venture_id)?.duration ?? 0}
                    label={`Watch the ${r.name} pitch${r.pitch_seconds ? `, ${clockText(r.pitch_seconds)}` : ""}`}
                    length={r.pitch_seconds ? clockText(r.pitch_seconds) : ""}
                  />
                  <div className="res-body">
                    <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start" }}>
                      <h3 className="res-name"><Link href={`/investor/ventures/${r.venture_id}`}>{r.name}</Link></h3>
                      <span className={`chip ${isRecent(r.last_activity, now) ? "chip-f" : "chip-n"}`}>
                        <span className="dot" aria-hidden="true" style={isRecent(r.last_activity, now) ? undefined : { background: "#858FA1" }} />
                        {activityText(r.last_activity, now)}
                      </span>
                    </div>
                    <p className="small" style={{ margin: 0 }}>
                      {r.founder_name}{r.city ? `, ${r.city}` : ""}, {country(r.country)} · {r.sector} · {stage(r.stage)}
                      {r.pitch_seconds ? ` · ${clockText(r.pitch_seconds)} pitch` : ""} · {consistency(r.updates_90d)}
                    </p>
                    {r.description && <p className="body2" style={{ margin: 0 }}>{r.description}</p>}
                    {r.ask && <p className="small" style={{ margin: 0 }}><strong style={{ color: "#101828" }}>Ask:</strong> {r.ask}</p>}
                    <AreaMeter areas={r.areas} />
                  </div>
                </li>
              ))}
            </ul>
          )}
          {pages > 1 && (
            <nav className="pager" aria-label="Pages">
              {filters.page > 1 ? <Link className="btn btn-n btn-sm" href={`/investor${queryString(filters, filters.page - 1)}`}>Previous page</Link> : <span />}
              <span className="small">Page {filters.page} of {pages}</span>
              {filters.page < pages ? <Link className="btn btn-n btn-sm" href={`/investor${queryString(filters, filters.page + 1)}`}>Next page</Link> : <span />}
            </nav>
          )}
        </section>
      </div>
    </AppShell>
  );
}
