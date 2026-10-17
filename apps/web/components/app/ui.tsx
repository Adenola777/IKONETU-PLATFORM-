import { Icon } from "@/components/site/icons";
import { areaCells, LEVEL, readinessText, STATUS, type AreaSummary, type ShownStatus } from "@/lib/product";

/** One evidence status, as a chip with its icon and name. */
export function StatusChip({ status }: { status: ShownStatus }) {
  const s = STATUS[status];
  return (
    <span className={`chip ${s.chip}`}>
      <Icon name={s.icon} size={14} />
      {s.name}
    </span>
  );
}

/**
 * The readiness check: eight cells, one per area, strong, building or a gap.
 * The sentence next to it says the same in words, so colour is never the only signal.
 */
export function AreaMeter({ areas }: { areas: AreaSummary[] }) {
  const cells = areaCells(areas);
  return (
    <p className="row small" style={{ margin: 0, gap: 10 }}>
      <span className="ameter" aria-hidden="true">
        {cells.map((c) => (
          <i key={c.code} className={c.level} title={`${c.label}: ${LEVEL[c.level].name}`} />
        ))}
      </span>
      <span>Readiness check: {readinessText(areas).replace(/^S/, "s").replace(/^No/, "no")}</span>
    </p>
  );
}

export function MeterLegend() {
  return (
    <ul className="legend" aria-label="What the cells mean">
      <li><span className="ameter" aria-hidden="true"><i className="strong" /></span>Strong: {LEVEL.strong.means.toLowerCase()}</li>
      <li><span className="ameter" aria-hidden="true"><i className="building" /></span>Building: {LEVEL.building.means.toLowerCase()}</li>
      <li><span className="ameter" aria-hidden="true"><i className="gap" /></span>Gap: {LEVEL.gap.means.toLowerCase()}</li>
    </ul>
  );
}

/** The error under a field, tied to it by id. */
export function FieldError({ id, message }: { id: string; message?: string }) {
  return message ? <p id={`${id}-err`} className="err">{message}</p> : null;
}

export function invalidProps(id: string, message?: string) {
  return message ? { "aria-invalid": true as const, "aria-describedby": `${id}-err` } : {};
}

/** The reply of a form's server action: an error at the top, or a short confirmation. */
export function FormStatus({ state }: { state: { status: string; message?: string } }) {
  if (state.status === "error") return <p className="status status-err" role="alert">{state.message}</p>;
  if (state.status === "sent") return <p className="status status-ok" role="status">{state.message}</p>;
  return null;
}
