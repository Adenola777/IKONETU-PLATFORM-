"use client";

import { useActionState } from "react";
import { FieldError, FormStatus, invalidProps } from "@/components/app/ui";
import { IDLE_STATE, one } from "@/lib/app-state";
import { EVIDENCE_FILE_TYPES, signalOptions } from "@/lib/forms";
import { AREAS } from "@/lib/product";
import { submitEvidence } from "./actions";

const OPTIONS = signalOptions();

export function EvidenceForm() {
  const [state, action, pending] = useActionState(submitEvidence, IDLE_STATE);
  const errors = state.status === "error" ? state.errors : {};
  const values = state.status === "error" ? (state.values ?? {}) : {};
  const key = state.status === "sent" ? `sent-${Date.now()}` : state.status === "error" ? JSON.stringify(values) : "new";
  return (
    <form key={key} className="form" action={action} noValidate>
      <FormStatus state={state} />
      <div className="field">
        <label htmlFor="e-signal">What does it show?</label>
        <select id="e-signal" name="signal" className="input" defaultValue={one(values, "signal")} {...invalidProps("signal", errors.signal)}>
          <option value="" disabled>Choose one</option>
          {AREAS.map((a) => (
            <optgroup key={a.code} label={a.label}>
              {OPTIONS.filter((o) => o.category === a.code).map((o) => (
                <option key={o.code} value={o.code}>{o.label}</option>
              ))}
            </optgroup>
          ))}
        </select>
        <FieldError id="signal" message={errors.signal} />
      </div>
      <div className="field">
        <label htmlFor="e-summary">Describe it in a sentence</label>
        <textarea id="e-summary" name="summary" className="input" rows={3} maxLength={280} defaultValue={one(values, "summary")} aria-describedby="e-summary-hint" {...invalidProps("summary", errors.summary)} />
        <p id="e-summary-hint" className="hint">Investors read this next to the evidence's status. For example: twelve months of bank statements for the business account.</p>
        <FieldError id="summary" message={errors.summary} />
      </div>
      <div className="field">
        <label htmlFor="e-files">Files (optional if you give a link)</label>
        <input id="e-files" name="files" type="file" multiple accept={EVIDENCE_FILE_TYPES.join(",")} className="input" aria-describedby="e-files-hint" {...invalidProps("files", errors.files)} />
        <p id="e-files-hint" className="hint">Up to 3 files, each a PDF, JPEG or PNG of 10 MB or less. Only you and IkonetU reviewers can open them. Investors never see the files.</p>
        <FieldError id="files" message={errors.files} />
      </div>
      <div className="field">
        <label htmlFor="e-link">Link (optional if you add a file)</label>
        <input id="e-link" name="link" type="url" inputMode="url" className="input" maxLength={300} defaultValue={one(values, "link")} aria-describedby="e-link-hint" {...invalidProps("link", errors.link)} />
        <p id="e-link-hint" className="hint">For example a press article, an app store page or a registry record.</p>
        <FieldError id="link" message={errors.link} />
      </div>
      <button type="submit" className="btn btn-f" style={{ alignSelf: "flex-start" }} disabled={pending}>
        {pending ? "Adding…" : "Add this evidence"}
      </button>
    </form>
  );
}
