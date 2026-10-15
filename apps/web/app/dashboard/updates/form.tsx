"use client";

import { useActionState } from "react";
import { FieldError, FormStatus, invalidProps } from "@/components/app/ui";
import { IDLE_STATE, one } from "@/lib/app-state";
import { postUpdate } from "./actions";

export function UpdateForm() {
  const [state, action, pending] = useActionState(postUpdate, IDLE_STATE);
  const errors = state.status === "error" ? state.errors : {};
  const values = state.status === "error" ? (state.values ?? {}) : {};
  const key = state.status === "sent" ? `sent-${Date.now()}` : state.status === "error" ? JSON.stringify(values) : "new";
  return (
    <form key={key} className="form" action={action} noValidate>
      <FormStatus state={state} />
      <div className="field">
        <label htmlFor="u-body">What changed?</label>
        <textarea id="u-body" name="body" className="input" rows={5} maxLength={600} defaultValue={one(values, "body")} aria-describedby="u-body-hint" {...invalidProps("body", errors.body)} />
        <p id="u-body-hint" className="hint">A sentence or two is enough: a customer signed, a feature shipped, a month's figures closed. Up to 600 characters.</p>
        <FieldError id="body" message={errors.body} />
      </div>
      <button type="submit" className="btn btn-f" style={{ alignSelf: "flex-start" }} disabled={pending}>
        {pending ? "Posting…" : "Post the update"}
      </button>
    </form>
  );
}
