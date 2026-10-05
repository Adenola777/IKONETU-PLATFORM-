"use client";

import { useState, type FormEvent } from "react";
import { COUNTRIES, ROLES } from "@/lib/constants";

type State =
  | { kind: "idle" }
  | { kind: "sending" }
  | { kind: "done"; message: string }
  | { kind: "error"; message: string; errors: Record<string, string> };

const ROLE_LABEL: Record<(typeof ROLES)[number], string> = { founder: "Founder", investor: "Investor", mentor: "Mentor" };

export function WaitlistForm() {
  const [state, setState] = useState<State>({ kind: "idle" });
  const errors = state.kind === "error" ? state.errors : {};

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const f = new FormData(e.currentTarget);
    setState({ kind: "sending" });
    try {
      const res = await fetch("/api/v1/waitlist", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          fullName: f.get("fullName") ?? "",
          contact: f.get("contact") ?? "",
          country: f.get("country") ?? "",
          role: f.get("role") ?? "",
          confirmedAdult: f.get("confirmedAdult") === "on",
          acceptedPrivacy: f.get("acceptedPrivacy") === "on",
          website: f.get("website") ?? "",
        }),
      });
      const data = (await res.json().catch(() => ({}))) as { message?: string; errors?: Record<string, string> };
      if (res.ok) setState({ kind: "done", message: data.message ?? "You are on the list." });
      else setState({ kind: "error", message: data.message ?? "Something went wrong. Please try again.", errors: data.errors ?? {} });
    } catch {
      setState({ kind: "error", message: "We could not reach the server. Check your connection and try again.", errors: {} });
    }
  }

  if (state.kind === "done") {
    return <p className="status status-ok" role="status">{state.message}</p>;
  }

  const err = (name: string) =>
    errors[name] ? <p id={`${name}-err`} className="err">{errors[name]}</p> : null;
  const invalid = (name: string) => (errors[name] ? { "aria-invalid": true, "aria-describedby": `${name}-err` } : {});

  return (
    <form className="form" onSubmit={onSubmit} noValidate>
      {state.kind === "error" && (
        <p className="status status-err" role="alert">{state.message}</p>
      )}
      <div className="field">
        <label htmlFor="w-name">Full name</label>
        <input id="w-name" name="fullName" className="input" type="text" autoComplete="name" required maxLength={120} {...invalid("fullName")} />
        {err("fullName")}
      </div>
      <div className="field">
        <label htmlFor="w-contact">Phone number or email</label>
        <input id="w-contact" name="contact" className="input" type="text" autoComplete="tel" inputMode="text" required maxLength={160} {...invalid("contact")} />
        <p className="hint">You can enter a local number, for example 0803 123 4567.</p>
        {err("contact")}
      </div>
      <div className="field">
        <label htmlFor="w-country">Country</label>
        <select id="w-country" name="country" className="input" defaultValue="NG" {...invalid("country")}>
          {COUNTRIES.map((c) => (
            <option key={c.code} value={c.code}>{c.name}</option>
          ))}
        </select>
        {err("country")}
      </div>
      <fieldset className="radios">
        <legend className="legend">I am joining as</legend>
        {ROLES.map((r) => (
          <label key={r} className="check" style={{ fontSize: 16 }}>
            <input type="radio" name="role" value={r} defaultChecked={r === "founder"} /> {ROLE_LABEL[r]}
          </label>
        ))}
      </fieldset>
      {err("role")}
      <div>
        <label className="check">
          <input type="checkbox" name="confirmedAdult" {...invalid("confirmedAdult")} /> <span>I am 18 or older.</span>
        </label>
        {err("confirmedAdult")}
      </div>
      <div>
        <label className="check">
          <input type="checkbox" name="acceptedPrivacy" {...invalid("acceptedPrivacy")} />
          <span>I have read the <a href="/privacy" target="_blank" rel="noopener">privacy notice</a>.</span>
        </label>
        {err("acceptedPrivacy")}
      </div>
      <div className="hp" aria-hidden="true">
        <label htmlFor="w-website">Website</label>
        <input id="w-website" name="website" type="text" tabIndex={-1} autoComplete="off" />
      </div>
      <button type="submit" className="btn btn-navy" style={{ alignSelf: "flex-start" }} disabled={state.kind === "sending"}>
        {state.kind === "sending" ? "Sending…" : "Join the waitlist"}
      </button>
    </form>
  );
}
