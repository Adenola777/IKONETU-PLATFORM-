"use client";

import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { ACTIVITY_OPTIONS, FILTER_GROUPS, type Filters } from "@/lib/discovery";

/**
 * The filters, as a form that sends a GET request, so the filtered list has
 * its own address and works without script. With script, each change applies
 * at once and focus stays where it was.
 */
export function DiscoveryFilters({ filters, chosen }: { filters: Filters; chosen: number }) {
  const router = useRouter();
  const form = useRef<HTMLFormElement | null>(null);
  // On narrow screens the filters fold away behind a button, so the results come first.
  const [open, setOpen] = useState(false);
  const apply = () => {
    const f = form.current;
    if (!f) return;
    const q = new URLSearchParams();
    for (const [k, v] of new FormData(f)) if (typeof v === "string" && v) q.append(k, v);
    const s = q.toString();
    router.replace(s ? `/investor?${s}` : "/investor", { scroll: false });
  };
  return (
    <div>
    <button type="button" className="btn btn-n btn-sm ftoggle" aria-expanded={open} aria-controls="disc-filters" onClick={() => setOpen(!open)}>
      {open ? "Hide filters" : chosen ? `Filters (${chosen} chosen)` : "Filters"}
    </button>
    <form ref={form} id="disc-filters" className={`filters${open ? " open" : ""}`} action="/investor" method="get" onChange={apply} aria-label="Filter founders">
      {FILTER_GROUPS.map((g) => (
        <fieldset key={g.key} className="fgroup">
          <legend className="flabel">{g.label}</legend>
          <div className="fchips">
            {g.options.map((o) => (
              <label key={o.value} className="fchip">
                <input type="checkbox" name={g.key} value={o.value} defaultChecked={filters[g.key].includes(o.value)} />
                {o.label}
              </label>
            ))}
          </div>
        </fieldset>
      ))}
      <fieldset className="fgroup">
        <legend className="flabel">Last updated</legend>
        <div className="fchips">
          {ACTIVITY_OPTIONS.map((o) => (
            <label key={o.value || "any"} className="fchip">
              <input type="radio" name="activity" value={o.value} defaultChecked={filters.activity === o.value} />
              {o.label}
            </label>
          ))}
        </div>
      </fieldset>
      <noscript>
        <button type="submit" className="btn btn-i btn-sm">Show founders</button>
      </noscript>
    </form>
    </div>
  );
}
