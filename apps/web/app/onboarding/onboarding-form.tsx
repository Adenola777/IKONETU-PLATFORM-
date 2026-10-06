"use client";

import { useActionState } from "react";
import { OPTIONAL_CONSENTS, STAGES } from "@/lib/account";
import { COUNTRIES } from "@/lib/constants";
import { IDLE } from "../form-state";
import { completeOnboarding } from "./actions";

export function OnboardingForm({ askAdult }: { askAdult: boolean }) {
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

      <div className="field">
        <label htmlFor="o-graduate">Student or graduate status (optional)</label>
        <input id="o-graduate" name="graduateStatus" className="input" type="text" maxLength={80} defaultValue={values.graduateStatus} {...invalid("graduateStatus")} />
        <p className="hint">For example: final-year student, or graduated 2024.</p>
        {err("graduateStatus")}
      </div>
      <div className="field">
        <label htmlFor="o-bio">Short bio (optional)</label>
        <textarea id="o-bio" name="bio" className="input" rows={3} maxLength={600} defaultValue={values.bio} {...invalid("bio")} />
        {err("bio")}
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

      <div className="field">
        <label htmlFor="o-website">Website (optional)</label>
        <input id="o-website" name="website" className="input" type="url" inputMode="url" maxLength={200} defaultValue={values.website} {...invalid("website")} />
        {err("website")}
      </div>
      <div className="field">
        <label htmlFor="o-linkedin">LinkedIn (optional)</label>
        <input id="o-linkedin" name="linkedin" className="input" type="url" inputMode="url" maxLength={200} defaultValue={values.linkedin} {...invalid("linkedin")} />
        {err("linkedin")}
      </div>
      <div className="field">
        <label htmlFor="o-x">X (optional)</label>
        <input id="o-x" name="x" className="input" type="url" inputMode="url" maxLength={200} defaultValue={values.x} {...invalid("x")} />
        {err("x")}
      </div>
      <div className="field">
        <label htmlFor="o-instagram">Instagram (optional)</label>
        <input id="o-instagram" name="instagram" className="input" type="url" inputMode="url" maxLength={200} defaultValue={values.instagram} {...invalid("instagram")} />
        {err("instagram")}
      </div>

      <fieldset className="radios">
        <legend className="legend">Your choices</legend>
        <p className="hint" style={{ margin: 0 }}>Each of these is optional, and you can change it later. A check only runs when you have said yes to it.</p>
        {OPTIONAL_CONSENTS.map((c) => (
          <label key={c.code} className="check">
            <input type="checkbox" name={`consent_${c.code}`} /> <span>{c.label}</span>
          </label>
        ))}
      </fieldset>

      {askAdult && (
        <div>
          <label className="check">
            <input type="checkbox" name="confirmedAdult" {...invalid("confirmedAdult")} /> <span>I am 18 or older.</span>
          </label>
          {err("confirmedAdult")}
        </div>
      )}
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
