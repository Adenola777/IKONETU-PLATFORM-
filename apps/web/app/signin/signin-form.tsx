"use client";

import { useActionState } from "react";
import { IDLE } from "../form-state";
import { sendSignInLink } from "./actions";

export function SignInForm() {
  const [state, action, pending] = useActionState(sendSignInLink, IDLE);

  if (state.status === "sent") {
    return <p className="status status-ok" role="status">{state.message}</p>;
  }
  const error = state.status === "error" ? state.errors.email : undefined;
  const typed = state.status === "error" ? state.values?.email : undefined;

  return (
    <form key={typed ?? "new"} className="form" action={action} noValidate>
      {state.status === "error" && <p className="status status-err" role="alert">{state.message}</p>}
      <div className="field">
        <label htmlFor="s-email">Email</label>
        <input
          id="s-email"
          name="email"
          className="input"
          type="email"
          autoComplete="email"
          required
          maxLength={160}
          defaultValue={typed}
          {...(error ? { "aria-invalid": true, "aria-describedby": "email-err" } : {})}
        />
        {error ? <p id="email-err" className="err">{error}</p> : null}
        <p className="hint">We email you a link. You do not need a password.</p>
      </div>
      <button type="submit" className="btn btn-navy" style={{ alignSelf: "flex-start" }} disabled={pending}>
        {pending ? "Sending…" : "Email me a link"}
      </button>
    </form>
  );
}
