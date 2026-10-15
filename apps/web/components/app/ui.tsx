import { Icon } from "@/components/site/icons";
import { areaCells, areaSummaryText, STATUS, type AreaSummary, type ShownStatus } from "@/lib/product";

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
 * Eight cells, one per area, with the best status in each. The sentence next
 * to it says the same in words, so colour is never the only signal.
 */
export function AreaMeter({ areas }: { areas: AreaSummary[] }) {
  const cells = areaCells(areas);
  return (
    <p className="row small" style={{ margin: 0, gap: 10 }}>
      <span className="ameter" aria-hidden="true">
        {cells.map((c) => (
          <i key={c.code} className={c.status ?? ""} title={`${c.label}: ${c.status ? STATUS[c.status].name : "no evidence"}`} />
        ))}
      </span>
      <span>{areaSummaryText(areas)}</span>
    </p>
  );
}

export function MeterLegend() {
  return (
    <ul className="legend" aria-label="What the cells mean">
      <li><span className="ameter" aria-hidden="true"><i className="third_party" /></span>Third-party evidence</li>
      <li><span className="ameter" aria-hidden="true"><i className="reviewed" /></span>Platform reviewed</li>
      <li><span className="ameter" aria-hidden="true"><i className="submitted" /></span>Founder submitted</li>
      <li><span className="ameter" aria-hidden="true"><i /></span>No evidence</li>
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
