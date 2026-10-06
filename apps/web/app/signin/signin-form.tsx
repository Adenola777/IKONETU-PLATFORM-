"use client";

import { useActionState, useState } from "react";
import { COUNTRIES } from "@/lib/constants";
import { IDLE } from "../form-state";
import { sendCode } from "./actions";

export function SignInForm({ phoneEnabled }: { phoneEnabled: boolean }) {
  const [state, action, pending] = useActionState(sendCode, IDLE);
  const [method, setMethod] = useState<"phone" | "email">(phoneEnabled ? "phone" : "email");
  const errors = state.status === "error" ? state.errors : {};
  const values = state.status === "error" ? (state.values ?? {}) : {};
  // The key makes React rebuild the fields after each reply, so they show what was typed.
  const key = `${method}:${state.status === "error" ? JSON.stringify(values) : "new"}`;
  const err = (name: string) => (errors[name] ? <p id={`${name}-err`} className="err">{errors[name]}</p> : null);
  const invalid = (name: string) => (errors[name] ? { "aria-invalid": true, "aria-describedby": `${name}-err` } : {});

  return (
    <form key={key} className="form" action={action} noValidate>
      {state.status === "error" && <p className="status status-err" role="alert">{state.message}</p>}
      <input type="hidden" name="method" value={method} />

      {method === "phone" ? (
        <div className="field">
          <label htmlFor="s-phone">Phone number</label>
          <div style={{ display: "flex", gap: 8 }}>
            <select name="country" aria-label="Country code" className="input" style={{ width: "auto" }} defaultValue={values.country || "NG"}>
              {COUNTRIES.map((c) => (
                <option key={c.code} value={c.code}>+{c.dial}</option>
              ))}
            </select>
            <input id="s-phone" name="phone" className="input" type="tel" autoComplete="tel-national" inputMode="tel" required maxLength={30} defaultValue={values.phone} {...invalid("phone")} />
          </div>
          {err("phone")}
          <p className="hint">We send a 6-digit code by WhatsApp, or by SMS if you ask.</p>
        </div>
      ) : (
        <div className="field">
          <label htmlFor="s-email">Email</label>
          <input id="s-email" name="email" className="input" type="email" autoComplete="email" required maxLength={160} defaultValue={values.email} {...invalid("email")} />
          {err("email")}
          <p className="hint">We send a 6-digit code to this email. You do not need a password.</p>
        </div>
      )}

      <div>
        <label className="check">
          <input type="checkbox" name="confirmedAdult" {...invalid("confirmedAdult")} /> <span>I am 18 or older.</span>
        </label>
        {err("confirmedAdult")}
      </div>

      <button type="submit" className="btn btn-navy" style={{ alignSelf: "flex-start" }} disabled={pending}>
        {pending ? "Sending…" : "Send my code"}
      </button>

      {phoneEnabled && (
        <button type="button" className="link-button" onClick={() => setMethod(method === "phone" ? "email" : "phone")}>
          {method === "phone" ? "Use email instead" : "Use my phone number instead"}
        </button>
      )}
      <p className="hint">
        By continuing you confirm you have read the <a href="/privacy" target="_blank" rel="noopener">privacy notice</a>.
      </p>
    </form>
  );
}
