"use client";

import { useActionState, useEffect, useState } from "react";
import { IDLE } from "../../form-state";
import { resendCode, verifyCode } from "./actions";

function useSecondsLeft(expiresAt: number) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  return Math.max(0, Math.round((expiresAt - now) / 1000));
}

export function CodeForm({ expiresAt, isPhone }: { expiresAt: number; isPhone: boolean }) {
  const [state, action, pending] = useActionState(verifyCode, IDLE);
  const [resent, resend, resending] = useActionState(resendCode, IDLE);
  const [expiry, setExpiry] = useState(expiresAt);
  useEffect(() => {
    if (resent.status === "sent") setExpiry(Date.now() + 300_000);
  }, [resent]);
  const left = useSecondsLeft(expiry);
  const error = state.status === "error" ? state.errors.code : undefined;
  const clock = `${Math.floor(left / 60)}:${String(left % 60).padStart(2, "0")}`;

  return (
    <div className="form">
      <form className="form" action={action} noValidate>
        {state.status === "error" && <p className="status status-err" role="alert">{state.message}</p>}
        <div className="field">
          <label htmlFor="c-code">6-digit code</label>
          <input
            id="c-code"
            name="code"
            className="input code-input"
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]*"
            maxLength={7}
            required
            {...(error ? { "aria-invalid": true, "aria-describedby": "code-err" } : {})}
          />
          {error ? <p id="code-err" className="err">{error}</p> : null}
          <p className="hint" aria-live="polite">{left > 0 ? `The code expires in ${clock}.` : "The code has expired. Ask for a new one below."}</p>
        </div>
        <button type="submit" className="btn btn-navy" style={{ alignSelf: "flex-start" }} disabled={pending}>
          {pending ? "Checking…" : "Continue"}
        </button>
      </form>

      <form action={resend}>
        {resent.status === "sent" && <p className="status status-ok" role="status">{resent.message}</p>}
        {resent.status === "error" && <p className="status status-err" role="alert">{resent.message}</p>}
        {isPhone && <input type="hidden" name="channel" value="sms" />}
        <button type="submit" className="link-button" disabled={resending}>
          {isPhone ? "Send the code by SMS instead" : "Send a new code"}
        </button>
      </form>
      <a href="/signin" className="link-button" style={{ display: "inline-flex", alignItems: "center" }}>Use a different {isPhone ? "number" : "email"}</a>
    </div>
  );
}
