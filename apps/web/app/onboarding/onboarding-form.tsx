"use client";

import { useActionState } from "react";
import { STAGES } from "@/lib/account";
import { COUNTRIES } from "@/lib/constants";
import { IDLE } from "../form-state";
import { completeOnboarding } from "./actions";

export function OnboardingForm() {
  const [state, action, pending] = useActionState(completeOnboarding, IDLE);
  const errors = state.status === "error" ? state.errors : {};
  const values = state.status === "error" ? (state.values ?? {}) : {};
  // The key makes React rebuild the fields after each reply, so they show what was typed.
  const key = state.status === "error" ? JSON.stringify(values) : "new";
  const err = (name: string) => (errors[name] ? <p id={`${name}-err`} className="err">{errors[name]}</p> : null);
  const invalid = (name: string) => (errors[name] ? { "aria-invalid": true, "aria-describedby": `${name}-err` } : {});

  return (
    <form key={key} className="form" action={action} noValidate>
      {state.status === "error" && <p className="status status-err" role="alert">{state.message}</p>}

      <h2 className="legend" style={{ margin: 0 }}>About you</h2>
      <div className="field">
        <label htmlFor="o-name">Full name</label>
        <input id="o-name" name="fullName" className="input" type="text" autoComplete="name" required maxLength={120} defaultValue={values.fullName} {...invalid("fullName")} />
        {err("fullName")}
      </div>
      <div className="field">
        <label htmlFor="o-country">Country</label>
        <select id="o-country" name="country" className="input" defaultValue={values.country || "NG"} {...invalid("country")}>
          {COUNTRIES.map((c) => (
            <option key={c.code} value={c.code}>{c.name}</option>
          ))}
        </select>
        {err("country")}
      </div>
      <div className="field">
        <label htmlFor="o-city">City (optional)</label>
        <input id="o-city" name="city" className="input" type="text" autoComplete="address-level2" maxLength={80} defaultValue={values.city} {...invalid("city")} />
        {err("city")}
      </div>
      <div className="field">
        <label htmlFor="o-institution">University or institution (optional)</label>
        <input id="o-institution" name="institution" className="input" type="text" maxLength={120} defaultValue={values.institution} {...invalid("institution")} />
        {err("institution")}
      </div>

      <h2 className="legend" style={{ margin: "12px 0 0" }}>Your venture</h2>
      <div className="field">
        <label htmlFor="o-venture">Venture name</label>
        <input id="o-venture" name="ventureName" className="input" type="text" required maxLength={120} defaultValue={values.ventureName} {...invalid("ventureName")} />
        {err("ventureName")}
      </div>
      <div className="field">
        <label htmlFor="o-sector">Sector</label>
        <input id="o-sector" name="sector" className="input" type="text" required maxLength={60} defaultValue={values.sector} {...invalid("sector")} />
        <p className="hint">For example Fintech, Agritech or Edtech.</p>
        {err("sector")}
      </div>
      <div className="field">
        <label htmlFor="o-stage">Stage</label>
        <select id="o-stage" name="stage" className="input" defaultValue={values.stage || "idea"} {...invalid("stage")}>
          {STAGES.map((s) => (
            <option key={s.code} value={s.code}>{s.label}</option>
          ))}
        </select>
        {err("stage")}
      </div>
      <div className="field">
        <label htmlFor="o-description">What it does, in one or two sentences (optional)</label>
        <textarea id="o-description" name="description" className="input" rows={3} maxLength={280} defaultValue={values.description} {...invalid("description")} />
        {err("description")}
      </div>

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
      <button type="submit" className="btn btn-navy" style={{ alignSelf: "flex-start" }} disabled={pending}>
        {pending ? "Saving…" : "Create my profile"}
      </button>
    </form>
  );
}
