"use client";

import { useActionState } from "react";
import { FieldError, invalidProps } from "@/components/app/ui";
import { IDLE_STATE, one } from "@/lib/app-state";
import { sendMessage } from "./actions";

export function MessageForm({ introduction }: { introduction: string }) {
  const [state, action, pending] = useActionState(sendMessage, IDLE_STATE);
  const errors = state.status === "error" ? state.errors : {};
  const values = state.status === "error" ? (state.values ?? {}) : {};
  const key = state.status === "sent" ? `sent-${Date.now()}` : state.status === "error" ? JSON.stringify(values) : "new";
  return (
    <form key={key} className="form" action={action} noValidate>
      {state.status === "error" && <p className="status status-err" role="alert">{state.message}</p>}
      <input type="hidden" name="introduction" value={introduction} />
      <div className="field">
        <label htmlFor="m-body">Your message</label>
        <textarea id="m-body" name="body" className="input" rows={4} maxLength={2000} defaultValue={one(values, "body")} {...invalidProps("body", errors.body)} />
        <FieldError id="body" message={errors.body} />
      </div>
      <button type="submit" className="btn btn-i" style={{ alignSelf: "flex-start" }} disabled={pending}>
        {pending ? "Sending…" : "Send"}
      </button>
    </form>
  );
}
