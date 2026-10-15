"use client";

import { useActionState } from "react";
import { InvestorFields } from "@/components/app/investor-fields";
import { FieldError, invalidProps } from "@/components/app/ui";
import { IDLE_STATE } from "@/lib/app-state";
import { createInvestor } from "./actions";

export function InvestorSignUpForm({ askAdult, name }: { askAdult: boolean; name: string }) {
  const [state, action, pending] = useActionState(createInvestor, IDLE_STATE);
  const errors = state.status === "error" ? state.errors : {};
  const values = state.status === "error" ? (state.values ?? {}) : { fullName: name };
  const key = state.status === "error" ? JSON.stringify(values) : "new";
  return (
    <form key={key} className="form" action={action} noValidate>
      {state.status === "error" && <p className="status status-err" role="alert">{state.message}</p>}
      <InvestorFields values={values} errors={errors} />
      <label className="check">
        <input type="checkbox" name="notifications" defaultChecked={values.notifications === "on"} />
        <span>IkonetU may email me about my account and my introductions (optional). IkonetU does not send these emails yet.</span>
      </label>
      {askAdult && (
        <div>
          <label className="check">
            <input type="checkbox" name="confirmedAdult" {...invalidProps("confirmedAdult", errors.confirmedAdult)} /> <span>I am 18 or older.</span>
          </label>
          <FieldError id="confirmedAdult" message={errors.confirmedAdult} />
        </div>
      )}
      <div>
        <label className="check">
          <input type="checkbox" name="acceptedPrivacy" {...invalidProps("acceptedPrivacy", errors.acceptedPrivacy)} />
          <span>I have read the <a href="/privacy" target="_blank" rel="noopener">privacy policy</a>.</span>
        </label>
        <FieldError id="acceptedPrivacy" message={errors.acceptedPrivacy} />
      </div>
      <button type="submit" className="btn btn-i" style={{ alignSelf: "flex-start" }} disabled={pending}>
        {pending ? "Saving…" : "Send for approval"}
      </button>
    </form>
  );
}
