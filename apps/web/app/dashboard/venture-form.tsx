"use client";

import { useActionState } from "react";
import { FieldError, FormStatus, invalidProps } from "@/components/app/ui";
import { STAGES } from "@/lib/account";
import { IDLE_STATE, one } from "@/lib/app-state";
import { SECTORS } from "@/lib/product";
import { updateVenture } from "./actions";

type Venture = { name: string; sector: string; stage: string; description: string | null; website: string | null };

export function VentureForm({ venture }: { venture: Venture }) {
  const [state, action, pending] = useActionState(updateVenture, IDLE_STATE);
  const errors = state.status === "error" ? state.errors : {};
  const values =
    state.status === "error" && state.values
      ? state.values
      : { name: venture.name, sector: venture.sector, stage: venture.stage, description: venture.description ?? "", website: venture.website ?? "" };
  const key = state.status === "error" ? JSON.stringify(values) : "saved";
  const known = (SECTORS as readonly string[]).includes(one(values, "sector"));
  return (
    <form key={key} className="form" action={action} noValidate>
      <FormStatus state={state} />
      <div className="field">
        <label htmlFor="v-name">Venture name</label>
        <input id="v-name" name="name" className="input" type="text" maxLength={120} defaultValue={one(values, "name")} {...invalidProps("name", errors.name)} />
        <FieldError id="name" message={errors.name} />
      </div>
      <div className="grid2">
        <div className="field">
          <label htmlFor="v-sector">Sector</label>
          <select id="v-sector" name="sector" className="input" defaultValue={known ? one(values, "sector") : ""} {...invalidProps("sector", errors.sector)}>
            <option value="" disabled>Choose a sector</option>
            {SECTORS.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
          {!known && one(values, "sector") && <p className="hint">You entered “{one(values, "sector")}”. Investors filter by the sectors listed, so choose the closest.</p>}
          <FieldError id="sector" message={errors.sector} />
        </div>
        <div className="field">
          <label htmlFor="v-stage">Stage</label>
          <select id="v-stage" name="stage" className="input" defaultValue={one(values, "stage")} {...invalidProps("stage", errors.stage)}>
            {STAGES.map((s) => (
              <option key={s.code} value={s.code}>{s.label}</option>
            ))}
          </select>
          <FieldError id="stage" message={errors.stage} />
        </div>
      </div>
      <div className="field">
        <label htmlFor="v-description">What it does, in one or two sentences</label>
        <textarea id="v-description" name="description" className="input" rows={3} maxLength={280} defaultValue={one(values, "description")} {...invalidProps("description", errors.description)} />
        <FieldError id="description" message={errors.description} />
      </div>
      <div className="field">
        <label htmlFor="v-website">Website</label>
        <input id="v-website" name="website" className="input" type="url" inputMode="url" maxLength={300} defaultValue={one(values, "website")} {...invalidProps("website", errors.website)} />
        <FieldError id="website" message={errors.website} />
      </div>
      <button type="submit" className="btn btn-n" style={{ alignSelf: "flex-start" }} disabled={pending}>
        {pending ? "Saving…" : "Save changes"}
      </button>
    </form>
  );
}
