"use client";

import { useActionState } from "react";
import { InvestorFields } from "@/components/app/investor-fields";
import { FormStatus } from "@/components/app/ui";
import { IDLE_STATE } from "@/lib/app-state";
import { updateInvestor } from "./actions";

export function InvestorEditForm({ initial }: { initial: Record<string, string | string[]> }) {
  const [state, action, pending] = useActionState(updateInvestor, IDLE_STATE);
  const errors = state.status === "error" ? state.errors : {};
  const values = state.status === "error" && state.values ? state.values : initial;
  return (
    <form key={state.status === "error" ? JSON.stringify(values) : state.status} className="form" action={action} noValidate>
      <FormStatus state={state} />
      <InvestorFields values={values} errors={errors} />
      <button type="submit" className="btn btn-i" style={{ alignSelf: "flex-start" }} disabled={pending}>
        {pending ? "Saving…" : "Save changes"}
      </button>
    </form>
  );
}
