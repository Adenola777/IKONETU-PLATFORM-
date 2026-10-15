import { STAGES } from "@/lib/account";
import { COUNTRIES } from "@/lib/constants";
import { activityText, AREAS, dateText, evidenceAddedText, isRecent, LEVEL, levelOf, momentum, STATUS, type AreaSummary } from "@/lib/product";
import type { VentureProfile } from "@/lib/venture-profile";
import { PitchVideo } from "./pitch-video";
import { AreaMeter, MeterLegend, StatusChip } from "./ui";

const country = (code: string | null) => COUNTRIES.find((c) => c.code === code)?.name ?? code ?? "";
const stage = (code: string) => STAGES.find((s) => s.code === code)?.label ?? code;
const RANK = { third_party: 3, reviewed: 2, submitted: 1 } as const;

/** "a, b and c". */
function listText(items: string[]): string {
  return items.length <= 1 ? (items[0] ?? "") : `${items.slice(0, -1).join(", ")} and ${items.at(-1)}`;
}

/** A founder profile as approved investors see it. The founder's preview shows the same. */
export function VentureProfileView({ p, aside, jump, now }: { p: VentureProfile; aside?: React.ReactNode; jump?: React.ReactNode; now: Date }) {
  const areas: AreaSummary[] = AREAS.flatMap((a) => {
    const items = p.evidence.filter((e) => e.category === a.code);
    if (!items.length) return [];
    const best = items.reduce((b, e) => (RANK[e.status] > RANK[b.status] ? e : b));
    return [{ category: a.code, status: best.status, count: items.length }];
  });
  const place = [p.founder?.city, country(p.venture.country)].filter(Boolean).join(", ");
  const empty = AREAS.filter((a) => !p.evidence.some((e) => e.category === a.code));
  const m = momentum(p.recentUpdates, now);

  return (
    <div className="stack">
      <header>
        <p className="lbl lbl-i" style={{ marginBottom: 8 }}>{p.venture.sector} · {stage(p.venture.stage)} · {country(p.venture.country)}</p>
        <h1 className="app-title">{p.venture.name}</h1>
        <p className="app-lede" style={{ marginBottom: 12 }}>
          {p.founder ? `${p.founder.full_name}${place ? `, ${place}` : ""}` : place}
          {p.founder?.institution ? ` · ${p.founder.institution}` : ""}
        </p>
        {p.venture.ask && (
          <p className="body2" style={{ margin: "0 0 12px" }}><strong style={{ color: "#101828" }}>Ask:</strong> {p.venture.ask}</p>
        )}
        <div className="row">
          <span className={`chip ${isRecent(p.lastActivity, now) ? "chip-f" : "chip-n"}`}>
            <span className="dot" aria-hidden="true" />{activityText(p.lastActivity, now)}
          </span>
          {p.venture.website && <a href={p.venture.website} target="_blank" rel="noopener nofollow">{p.venture.website.replace(/^https?:\/\//, "")}</a>}
          {jump}
        </div>
      </header>

      <div className="side">
        <div className="stack">
          <section aria-labelledby="pitch-h">
            <h2 id="pitch-h" className="app-h2">Pitch</h2>
            {p.pitch ? (
              <PitchVideo src={p.pitch.url} transcript={p.pitch.transcript} duration={p.pitch.duration} title={`${p.venture.name} pitch`} />
            ) : (
              <div className="empty"><p>No pitch has been added.</p></div>
            )}
          </section>

          {(p.venture.description || p.founder?.bio) && (
            <section aria-labelledby="about-h" className="card">
              <h2 id="about-h" className="app-h2">About</h2>
              {p.venture.description && <p className="body2">{p.venture.description}</p>}
              {p.founder?.bio && <p className="body2" style={{ marginTop: 12 }}>{p.founder.bio}</p>}
            </section>
          )}

          <section aria-labelledby="ev-h" className="card">
            <h2 id="ev-h" className="app-h2">Readiness check</h2>
            <AreaMeter areas={areas} />
            <div style={{ margin: "12px 0 20px" }}><MeterLegend /></div>
            <p className="small" style={{ marginTop: 0 }}>
              An area is strong when it holds evidence IkonetU reviewed or an outside source backs, building when it holds the
              founder's own evidence only, and a gap when it holds none. Each status says what happened to that piece of evidence and
              nothing more. It is not a judgement of the company, and IkonetU does not endorse or rank any company. Your own diligence
              decides.
            </p>
            {AREAS.filter((a) => p.evidence.some((e) => e.category === a.code)).map((a) => {
              const items = p.evidence.filter((e) => e.category === a.code);
              return (
                <div key={a.code} className="area">
                  <h3 className="app-h3 row" style={{ gap: 10 }}>
                    {a.label}
                    {(() => {
                      const l = levelOf(items.reduce((b, e) => (RANK[e.status] > RANK[b.status] ? e : b)).status);
                      return <span className={`chip ${LEVEL[l].chip}`}>{LEVEL[l].name}</span>;
                    })()}
                  </h3>
                  <ul className="ev">
                    {items.map((e) => (
                      <li key={e.id}>
                        <span className="what">{e.label}</span>
                        {e.summary && <p className="body2" style={{ margin: "4px 0 8px" }}>{e.summary}</p>}
                        <div className="row"><StatusChip status={e.status} /></div>
                        <p className="small" style={{ margin: "6px 0 0" }}>{STATUS[e.status].means}</p>
                        {e.publicNote && (
                          <p className="note">
                            What was compared{e.reviewedAt ? `, on ${dateText(e.reviewedAt)}` : ""}: {e.publicNote}
                          </p>
                        )}
                        {e.status === "submitted" && <p className="small" style={{ margin: "6px 0 0" }}>Added on {dateText(e.createdAt)}.</p>}
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
            {empty.length > 0 && (
              <p className="small area" style={{ margin: 0 }}>
                {empty.length === 8 ? "No evidence has been added yet, so all eight areas are gaps." : `Gap, with no evidence yet: ${listText(empty.map((a) => a.label))}.`}
              </p>
            )}
          </section>
        </div>

        <aside className="stack">
          {aside}
          <section aria-labelledby="mo-h" className="card">
            <h2 id="mo-h" className="app-h2">Momentum</h2>
            <dl className="kv kv-stack" style={{ marginBottom: 16 }}>
              <dt>Recency</dt><dd>{activityText(p.lastActivity, now)}</dd>
              <dt>Consistency</dt><dd>{m.consistencyText}</dd>
              <dt>Evidence added</dt><dd>{evidenceAddedText(p.evidence, now)}</dd>
            </dl>
            <div className="weeks" role="img" aria-label={`Updates in ${m.activeWeeks} of the last 13 weeks`}>
              {m.weeks.map((w) => <i key={w.ago} className={w.active ? "on" : ""} />)}
            </div>
            <p className="small row" style={{ justifyContent: "space-between", margin: "6px 0 0" }}><span>13 weeks ago</span><span>This week</span></p>
            <p className="small" style={{ margin: "8px 0 0" }}>Orange marks a week with a progress update. There are no streaks, points or ranks.</p>
          </section>
          <section aria-labelledby="up-h" className="card">
            <h2 id="up-h" className="app-h2">Progress updates</h2>
            {p.updates.length === 0 ? (
              <p className="body2">No updates have been posted.</p>
            ) : (
              <ul className="updates">
                {p.updates.map((u) => (
                  <li key={u.id}>
                    <time dateTime={u.created_at}>{dateText(u.created_at)}</time>
                    <p>{u.body}</p>
                  </li>
                ))}
              </ul>
            )}
          </section>
        </aside>
      </div>
    </div>
  );
}
