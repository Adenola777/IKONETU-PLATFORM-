import { STAGES } from "@/lib/account";
import { many, one } from "@/lib/app-state";
import { COUNTRIES } from "@/lib/constants";
import { CHEQUE_SIZES } from "@/lib/investor-options";
import { BASED_IN, INVESTOR_TYPE_OPTIONS } from "@/lib/investor-profile";
import { SECTORS } from "@/lib/product";
import { FieldError, invalidProps } from "./ui";

type Values = Record<string, string | string[]>;

/** The investor's details, shared by sign-up and the profile page. */
export function InvestorFields({ values, errors }: { values: Values; errors: Record<string, string> }) {
  const v = (k: string) => one(values, k);
  const has = (k: string, x: string) => many(values, k).includes(x);
  return (
    <>
      <div className="field">
        <label htmlFor="i-name">Full name</label>
        <input id="i-name" name="fullName" className="input" type="text" autoComplete="name" maxLength={120} defaultValue={v("fullName")} {...invalidProps("fullName", errors.fullName)} />
        <FieldError id="fullName" message={errors.fullName} />
      </div>

      <fieldset className="field">
        <legend>Which describes you best?</legend>
        <div className="stack-s">
          {INVESTOR_TYPE_OPTIONS.map((o) => (
            <label key={o.code} className="opt opt-tall">
              <input type="radio" name="investorType" value={o.code} defaultChecked={v("investorType") === o.code} />
              <span><b>{o.name}</b><span className="small">{o.hint}</span></span>
            </label>
          ))}
        </div>
        <FieldError id="investorType" message={errors.investorType} />
      </fieldset>

      <div className="grid2">
        <div className="field">
          <label htmlFor="i-firm">Fund or firm (needed for a fund investor)</label>
          <input id="i-firm" name="firm" className="input" type="text" autoComplete="organization" maxLength={120} defaultValue={v("firm")} {...invalidProps("firm", errors.firm)} />
          <FieldError id="firm" message={errors.firm} />
        </div>
        <div className="field">
          <label htmlFor="i-website">Website or LinkedIn (optional)</label>
          <input id="i-website" name="website" className="input" type="url" inputMode="url" maxLength={200} defaultValue={v("website")} {...invalidProps("website", errors.website)} />
          <FieldError id="website" message={errors.website} />
        </div>
      </div>

      <div className="field">
        <label htmlFor="i-based">Where are you based?</label>
        <select id="i-based" name="basedIn" className="input" defaultValue={v("basedIn")} {...invalidProps("basedIn", errors.basedIn)}>
          <option value="" disabled>Choose a country</option>
          {BASED_IN.map((c) => (
            <option key={c.code} value={c.code}>{c.name}</option>
          ))}
        </select>
        <FieldError id="basedIn" message={errors.basedIn} />
      </div>

      <fieldset className="field">
        <legend>Sectors you invest in</legend>
        <div className="opts opts-3">
          {SECTORS.map((s) => (
            <label key={s} className="opt">
              <input type="checkbox" name="sectors" value={s} defaultChecked={has("sectors", s)} /> {s}
            </label>
          ))}
        </div>
        <FieldError id="sectors" message={errors.sectors} />
      </fieldset>

      <fieldset className="field">
        <legend>Stages you invest in (optional)</legend>
        <div className="opts">
          {STAGES.map((s) => (
            <label key={s.code} className="opt">
              <input type="checkbox" name="stages" value={s.code} defaultChecked={has("stages", s.code)} /> {s.label}
            </label>
          ))}
        </div>
        <FieldError id="stages" message={errors.stages} />
      </fieldset>

      <fieldset className="field">
        <legend>Countries you invest in (optional)</legend>
        <div className="opts opts-3">
          {COUNTRIES.map((c) => (
            <label key={c.code} className="opt">
              <input type="checkbox" name="countries" value={c.code} defaultChecked={has("countries", c.code)} /> {c.name}
            </label>
          ))}
        </div>
        <FieldError id="countries" message={errors.countries} />
      </fieldset>

      <div className="field">
        <label htmlFor="i-cheque">Typical cheque size</label>
        <select id="i-cheque" name="chequeSize" className="input" defaultValue={v("chequeSize")} {...invalidProps("chequeSize", errors.chequeSize)}>
          <option value="" disabled>Choose a size</option>
          {CHEQUE_SIZES.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
        <FieldError id="chequeSize" message={errors.chequeSize} />
      </div>

      <div className="field">
        <label htmlFor="i-thesis">What you look for (optional)</label>
        <textarea id="i-thesis" name="thesis" className="input" rows={4} maxLength={600} defaultValue={v("thesis")} aria-describedby="i-thesis-hint" {...invalidProps("thesis", errors.thesis)} />
        <p id="i-thesis-hint" className="hint">Founders see your name, investor type and firm when you ask for an introduction. They do not see this.</p>
        <FieldError id="thesis" message={errors.thesis} />
      </div>

      <div>
        <label className="check">
          <input type="checkbox" name="confirmedStatement" {...invalidProps("confirmedStatement", errors.confirmedStatement)} />
          <span>
            The investor type I chose describes me. I will not misrepresent my investor type, investment capacity, regulatory status
            or affiliation, as the <a href="/terms#terms-investor" target="_blank" rel="noopener">investor terms</a> require.
          </span>
        </label>
        <FieldError id="confirmedStatement" message={errors.confirmedStatement} />
      </div>
    </>
  );
}
