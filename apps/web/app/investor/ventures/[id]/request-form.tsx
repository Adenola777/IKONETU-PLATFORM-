"use client";

import { useActionState } from "react";
import { requestIntroduction } from "@/app/introductions/actions";
import { FieldError, invalidProps } from "@/components/app/ui";
import { IDLE_STATE, one } from "@/lib/app-state";

export function RequestForm({ venture, founder }: { venture: string; founder: string }) {
  const [state, action, pending] = useActionState(requestIntroduction, IDLE_STATE);
  if (state.status === "sent") return <p className="status status-ok" role="status">{state.message}</p>;
  const errors = state.status === "error" ? state.errors : {};
  const values = state.status === "error" ? (state.values ?? {}) : {};
  return (
    <form key={JSON.stringify(values)} className="form" action={action} noValidate>
      {state.status === "error" && <p className="status status-err" role="alert">{state.message}</p>}
      <input type="hidden" name="venture" value={venture} />
      <div className="field">
        <label htmlFor="r-note">Why do you want to talk?</label>
        <textarea id="r-note" name="note" className="input" rows={5} maxLength={600} defaultValue={one(values, "note")} aria-describedby="r-note-hint" {...invalidProps("note", errors.note)} />
        <p id="r-note-hint" className="hint">{founder} sees this note with your name, investor type and firm, and decides whether to accept. Up to 600 characters.</p>
        <FieldError id="note" message={errors.note} />
      </div>
      <button type="submit" className="btn btn-i" style={{ alignSelf: "flex-start" }} disabled={pending}>
        {pending ? "Sending…" : "Request an introduction"}
      </button>
    </form>
  );
}
