"use client";

import { useActionState } from "react";
import { FieldError, FormStatus, invalidProps } from "@/components/app/ui";
import { ROLE_NAME, type GivableRole } from "@/lib/admin";
import { IDLE_STATE, one } from "@/lib/app-state";
import { setRole, setStatus } from "./actions";

/** Changes the person's role to one of the roles their account can hold. */
export function RoleForm({ id, roles, founderNow }: { id: string; roles: GivableRole[]; founderNow: boolean }) {
  const [state, action, pending] = useActionState(setRole, IDLE_STATE);
  const errors = state.status === "error" ? state.errors : {};
  const values = state.status === "error" ? (state.values ?? {}) : {};
  return (
    <form className="form" action={action} noValidate>
      <FormStatus state={state} />
      <input type="hidden" name="id" value={id} />
      <div className="field">
        <label htmlFor="r-role">New role</label>
        <select id="r-role" name="role" className="input" defaultValue={one(values, "role")} {...invalidProps("role", errors.role)}>
          <option value="">Choose a role</option>
          {roles.map((r) => <option key={r} value={r}>{ROLE_NAME[r]}</option>)}
        </select>
        <FieldError id="role" message={errors.role} />
        {founderNow && (
          <p className="hint">A founder who becomes a reviewer or an admin is taken out of investors&apos; view, so IkonetU staff have no profile in discovery.</p>
        )}
      </div>
      <div className="field">
        <label htmlFor="r-reason">Reason, for the audit log (optional)</label>
        <textarea id="r-reason" name="reason" className="input" rows={2} maxLength={280} defaultValue={one(values, "reason")}
          {...invalidProps("reason", errors.reason)} />
        <FieldError id="reason" message={errors.reason} />
      </div>
      <div className="row">
        <button type="submit" className="btn btn-n" disabled={pending}>{pending ? "Changing the role" : "Change the role"}</button>
      </div>
    </form>
  );
}

/** Suspends an active account with a reason, or makes a suspended one active again. */
export function StatusForm({ id, suspend, founder }: { id: string; suspend: boolean; founder: boolean }) {
  const [state, action, pending] = useActionState(setStatus, IDLE_STATE);
  const errors = state.status === "error" ? state.errors : {};
  const values = state.status === "error" ? (state.values ?? {}) : {};
  return (
    <form className="form" action={action} noValidate>
      <FormStatus state={state} />
      <input type="hidden" name="id" value={id} />
      <input type="hidden" name="status" value={suspend ? "suspended" : "active"} />
      <div className="field">
        <label htmlFor="s-reason">{suspend ? "Why are you suspending this account?" : "Reason, for the audit log (optional)"}</label>
        <textarea id="s-reason" name="reason" className="input" rows={2} maxLength={280} required={suspend} defaultValue={one(values, "reason")}
          aria-describedby={suspend ? "s-reason-hint" : undefined} {...invalidProps("reason", errors.reason)} />
        {suspend && (
          <p id="s-reason-hint" className="hint">
            The reason goes to the audit log. No email is sent{founder ? ", and the founder's profile leaves investors' view at once" : ""}.
          </p>
        )}
        <FieldError id="reason" message={errors.reason} />
      </div>
      <div className="row">
        <button type="submit" className={suspend ? "btn danger" : "btn btn-n"} disabled={pending}>
          {pending ? "Saving" : suspend ? "Suspend the account" : "Make the account active again"}
        </button>
      </div>
    </form>
  );
}
