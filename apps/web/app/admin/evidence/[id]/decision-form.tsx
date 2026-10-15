"use client";

import { useActionState, useState } from "react";
import { FieldError, invalidProps } from "@/components/app/ui";
import { STAGES } from "@/lib/account";
import { IDLE_STATE, one } from "@/lib/app-state";
import { REVIEW_LANES } from "@/lib/forms";
import { decide } from "./actions";

export function DecisionForm({ id, mode }: { id: string; mode: "fixed" | "per_item" | "months" | "revenue" | "stage" }) {
  const [state, action, pending] = useActionState(decide, IDLE_STATE);
  const errors = state.status === "error" ? state.errors : {};
  const values = state.status === "error" ? (state.values ?? {}) : {};
  const [decision, setDecision] = useState(one(values, "decision") || "approve");
  return (
    <form key={JSON.stringify(values)} className="form" action={action} noValidate>
      {state.status === "error" && <p className="status status-err" role="alert">{state.message}</p>}
      <input type="hidden" name="id" value={id} />
      <fieldset className="field">
        <legend>Decision</legend>
        <div className="opts opts-3">
          {[["approve", "Approve"], ["needs_more", "Ask for more"], ["reject", "Reject"]].map(([v, l]) => (
            <label key={v} className="opt">
              <input type="radio" name="decision" value={v} checked={decision === v} onChange={() => setDecision(v as string)} /> {l}
            </label>
          ))}
        </div>
        <FieldError id="decision" message={errors.decision} />
      </fieldset>

      {decision === "approve" ? (
        <>
          <fieldset className="field">
            <legend>How did you check it?</legend>
            <div className="stack-s">
              {REVIEW_LANES.map((l) => (
                <label key={l.code} className="opt opt-tall">
                  <input type="radio" name="lane" value={l.code} defaultChecked={one(values, "lane") === l.code} />
                  <span><b>{l.name}</b><span className="small">{l.hint}</span></span>
                </label>
              ))}
            </div>
            <FieldError id="lane" message={errors.lane} />
          </fieldset>
          <div className="field">
            <label htmlFor="d-note">What did you compare? Investors read this.</label>
            <textarea id="d-note" name="publicNote" className="input" rows={3} maxLength={280} defaultValue={one(values, "publicNote")} aria-describedby="d-note-hint" {...invalidProps("publicNote", errors.publicNote)} />
            <p id="d-note-hint" className="hint">For example: compared the stated revenue with twelve months of bank statements. Do not copy figures the founder has not chosen to show.</p>
            <FieldError id="publicNote" message={errors.publicNote} />
          </div>
          {mode === "per_item" && (
            <div className="field">
              <label htmlFor="d-count">How many items did you confirm?</label>
              <input id="d-count" name="itemCount" className="input" inputMode="numeric" defaultValue={one(values, "itemCount")} {...invalidProps("itemCount", errors.itemCount)} />
              <FieldError id="itemCount" message={errors.itemCount} />
            </div>
          )}
          {mode === "months" && (
            <div className="field">
              <label htmlFor="d-months">How many months did you confirm?</label>
              <input id="d-months" name="months" className="input" inputMode="numeric" defaultValue={one(values, "months")} {...invalidProps("months", errors.months)} />
              <FieldError id="months" message={errors.months} />
            </div>
          )}
          {mode === "revenue" && (
            <div className="field">
              <label htmlFor="d-rev">Revenue you confirmed over the last 12 months, in US dollars</label>
              <input id="d-rev" name="revenueUsd" className="input" inputMode="decimal" defaultValue={one(values, "revenueUsd")} aria-describedby="d-rev-hint" {...invalidProps("revenueUsd", errors.revenueUsd)} />
              <p id="d-rev-hint" className="hint">Used for the founder's score only. Investors do not see it.</p>
              <FieldError id="revenueUsd" message={errors.revenueUsd} />
            </div>
          )}
          {mode === "stage" && (
            <div className="field">
              <label htmlFor="d-stage">Stage you confirmed</label>
              <select id="d-stage" name="stage" className="input" defaultValue={one(values, "stage")}>
                <option value="">Choose a stage</option>
                {STAGES.map((s) => <option key={s.code} value={s.code}>{s.label}</option>)}
              </select>
            </div>
          )}
        </>
      ) : (
        <div className="field">
          <label htmlFor="d-reason">{decision === "reject" ? "Why is it not accepted?" : "What more do you need?"} The founder reads this.</label>
          <textarea id="d-reason" name="reason" className="input" rows={4} maxLength={600} defaultValue={one(values, "reason")} {...invalidProps("reason", errors.reason)} />
          <FieldError id="reason" message={errors.reason} />
        </div>
      )}
      <button type="submit" className="btn btn-i" style={{ alignSelf: "flex-start" }} disabled={pending}>
        {pending ? "Saving…" : "Save the decision"}
      </button>
    </form>
  );
}
