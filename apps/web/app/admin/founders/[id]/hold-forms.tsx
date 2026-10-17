"use client";

import { useActionState } from "react";
import { FieldError, FormStatus, invalidProps } from "@/components/app/ui";
import { IDLE_STATE, one } from "@/lib/app-state";
import { hideVenture, liftHold } from "./actions";

/** Hides the profile from investors. The reason is required, because the founder reads it. */
export function HideForm({ id, name }: { id: string; name: string }) {
  const [state, action, pending] = useActionState(hideVenture, IDLE_STATE);
  const errors = state.status === "error" ? state.errors : {};
  const values = state.status === "error" ? (state.values ?? {}) : {};
  return (
    <form className="form" action={action} noValidate>
      <FormStatus state={state} />
      <input type="hidden" name="id" value={id} />
      <div className="field">
        <label htmlFor="h-reason">Why are you hiding {name}? The founder reads this.</label>
        <textarea id="h-reason" name="reason" className="input" rows={3} maxLength={280} required defaultValue={one(values, "reason")}
          aria-describedby="h-reason-hint" {...invalidProps("reason", errors.reason)} />
        <p id="h-reason-hint" className="hint">Say what is wrong and what would let you lift the hold. Up to 280 characters.</p>
        <FieldError id="reason" message={errors.reason} />
      </div>
      <div className="row">
        <button type="submit" className="btn danger" disabled={pending}>{pending ? "Hiding the profile" : "Hide the profile from investors"}</button>
      </div>
    </form>
  );
}

/** Lifts the hold. The note is optional and goes to the audit log only. */
export function LiftForm({ id }: { id: string }) {
  const [state, action, pending] = useActionState(liftHold, IDLE_STATE);
  const errors = state.status === "error" ? state.errors : {};
  const values = state.status === "error" ? (state.values ?? {}) : {};
  return (
    <form className="form" action={action} noValidate>
      <FormStatus state={state} />
      <input type="hidden" name="id" value={id} />
      <div className="field">
        <label htmlFor="l-note">Note for the audit log (optional)</label>
        <textarea id="l-note" name="note" className="input" rows={2} maxLength={280} defaultValue={one(values, "note")}
          {...invalidProps("note", errors.note)} />
        <FieldError id="note" message={errors.note} />
      </div>
      <div className="row">
        <button type="submit" className="btn btn-n" disabled={pending}>{pending ? "Lifting the hold" : "Lift the hold"}</button>
      </div>
    </form>
  );
}
