"use client";

import { useActionState } from "react";
import { FieldError, FormStatus, invalidProps } from "@/components/app/ui";
import { IDLE_STATE, one } from "@/lib/app-state";
import { saveTranscript } from "./actions";

export function TranscriptForm({ transcript }: { transcript: string }) {
  const [state, action, pending] = useActionState(saveTranscript, IDLE_STATE);
  const errors = state.status === "error" ? state.errors : {};
  const value = state.status === "error" && state.values ? one(state.values, "transcript") : transcript;
  return (
    <form key={state.status === "error" ? value : "t"} className="form" action={action} noValidate>
      <FormStatus state={state} />
      <div className="field">
        <label htmlFor="t-transcript">Transcript</label>
        <textarea id="t-transcript" name="transcript" className="input" rows={6} maxLength={2000} defaultValue={value} {...invalidProps("transcript", errors.transcript)} />
        <FieldError id="transcript" message={errors.transcript} />
      </div>
      <button type="submit" className="btn btn-n" style={{ alignSelf: "flex-start" }} disabled={pending}>
        {pending ? "Saving…" : "Save the transcript"}
      </button>
    </form>
  );
}
