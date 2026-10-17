import { z } from "zod";
import { firstErrors, type FieldErrors } from "./account";

/**
 * Names, rules and wording for the staff pages. The database functions of
 * migration 20261017000001 check every change again, so these rules only let
 * a form report a problem before the database refuses it.
 */
export type Role = "founder" | "investor" | "mentor" | "reviewer" | "admin";
export type AccountStatus = "active" | "pending" | "suspended";

export const ROLE_NAME: Record<Role, string> = {
  founder: "Founder",
  investor: "Investor",
  mentor: "Mentor",
  reviewer: "Reviewer",
  admin: "Admin",
};

export const ACCOUNT_STATUS_NAME: Record<AccountStatus, string> = {
  active: "Active",
  pending: "Waiting for approval",
  suspended: "Suspended",
};

/** The roles an admin can give, in the order the form lists them. */
export const GIVABLE_ROLES = ["founder", "investor", "reviewer", "admin"] as const;
export type GivableRole = (typeof GIVABLE_ROLES)[number];

/**
 * The roles a person can move to. A founder role needs a venture and an
 * investor role needs an investor profile, as admin_set_role() requires.
 */
export function rolesFor(current: Role, has: { venture: boolean; investorProfile: boolean }): GivableRole[] {
  return GIVABLE_ROLES.filter(
    (r) => r !== current && (r !== "founder" || has.venture) && (r !== "investor" || has.investorProfile),
  );
}

/** What each audit log action means, in a sentence fragment that follows the person's name. */
export const ACTION_TEXT: Record<string, string> = {
  "investor.approve": "approved an investor",
  "investor.decline": "declined or suspended an investor",
  "evidence.approve": "approved evidence",
  "evidence.reject": "rejected evidence",
  "evidence.needs_more": "asked for more evidence",
  "venture.hide": "hid a profile from investors",
  "venture.lift_hold": "lifted the hold on a profile",
  "account.role": "changed a role",
  "account.suspend": "suspended an account",
  "account.reactivate": "made an account active again",
};

/** The filters of the audit log page, by the first part of the action. */
export const ACTION_GROUPS = [
  { code: "investor", label: "Investor approvals" },
  { code: "evidence", label: "Evidence decisions" },
  { code: "venture", label: "Profile holds" },
  { code: "account", label: "Roles and suspensions" },
] as const;

export function actionText(action: string): string {
  return ACTION_TEXT[action] ?? action;
}

/** The page that shows the record an audit log entry is about, if there is one. */
export function entityHref(entity: string, id: string | null): string | null {
  if (!id || !/^[0-9a-f-]{36}$/.test(id)) return null;
  if (entity === "profiles") return `/admin/people/${id}`;
  if (entity === "ventures") return `/admin/founders/${id}`;
  if (entity === "evidence") return `/admin/evidence/${id}`;
  return null;
}

type Json = Record<string, unknown> | null;

const FIELD_NAME: Record<string, string> = {
  status: "Status",
  role: "Role",
  lane: "Checked by",
  published_at: "Published to investors",
  hidden_at: "Hold",
  public_note: "Note for investors",
};

const EVIDENCE_STATUS_NAME: Record<string, string> = {
  submitted: "Waiting for review",
  checking: "Waiting for review",
  needs_review: "Waiting for review",
  approved: "Approved",
  rejected: "Rejected",
  needs_more: "More asked for",
  expired: "Expired",
};

const LANE_NAME: Record<string, string> = {
  human: "an IkonetU reviewer",
  government: "a government record",
  source: "another outside source",
};

function valueText(key: string, v: unknown): string {
  const empty = v === null || v === undefined || v === "";
  if (key === "published_at") return empty ? "no" : "yes";
  if (key === "hidden_at") return empty ? "off" : "on";
  if (empty) return "none";
  if (key === "role" && typeof v === "string" && v in ROLE_NAME) return ROLE_NAME[v as Role];
  if (key === "status" && typeof v === "string" && v in ACCOUNT_STATUS_NAME) return ACCOUNT_STATUS_NAME[v as AccountStatus];
  if (key === "status" && typeof v === "string" && v in EVIDENCE_STATUS_NAME) return EVIDENCE_STATUS_NAME[v] as string;
  if (key === "lane" && typeof v === "string" && v in LANE_NAME) return LANE_NAME[v] as string;
  return String(v);
}

/**
 * The fields an audit log entry changed, as "Status: Waiting for approval to
 * Active". The reason, the note and the count of hidden profiles are shown
 * apart, so they are left out here.
 */
export function changeLines(before: Json, after: Json): string[] {
  const skip = new Set(["reason", "note", "profiles_hidden"]);
  const keys = [...new Set([...Object.keys(before ?? {}), ...Object.keys(after ?? {})])].filter((k) => !skip.has(k));
  const lines: string[] = [];
  for (const k of keys) {
    const from = valueText(k, before?.[k]);
    const to = valueText(k, after?.[k]);
    if (from === to) continue;
    lines.push(`${FIELD_NAME[k] ?? k}: ${from} to ${to}`);
  }
  return lines;
}

/** The reason or note an admin gave, if the entry carries one. */
export function entryReason(after: Json): string | null {
  const r = after?.reason ?? after?.note;
  return typeof r === "string" && r.trim() ? r : null;
}

// ---------------------------------------------------------------- forms
type Parsed<T> = { ok: true; data: T } | { ok: false; errors: FieldErrors };

function parse<S extends z.ZodTypeAny>(schema: S, input: unknown): Parsed<z.output<S>> {
  const r = schema.safeParse(input);
  return r.success ? { ok: true, data: r.data } : { ok: false, errors: firstErrors(r.error) };
}

const uuid = z.string().regex(/^[0-9a-f-]{36}$/, "This record could not be found.");
const requiredReason = (message: string) =>
  z.string().trim().min(5, message).max(280, "Keep it to 280 characters.");
const optionalReason = z
  .string()
  .trim()
  .max(280, "Keep it to 280 characters.")
  .transform((v) => (v === "" ? null : v));

const holdSchema = z.object({
  id: uuid,
  reason: requiredReason("Tell the founder why, in at least five characters. The founder reads this."),
});
const liftSchema = z.object({ id: uuid, note: optionalReason });
const roleSchema = z.object({
  id: uuid,
  role: z.enum(GIVABLE_ROLES, { errorMap: () => ({ message: "Choose a role." }) }),
  reason: optionalReason,
});
const statusSchema = z.discriminatedUnion("status", [
  z.object({ id: uuid, status: z.literal("suspended"), reason: requiredReason("Give a reason for the suspension, in at least five characters.") }),
  z.object({ id: uuid, status: z.literal("active"), reason: optionalReason }),
]);

const text = (form: FormData, k: string) => String(form.get(k) ?? "");

export function parseHold(form: FormData) {
  return parse(holdSchema, { id: text(form, "id"), reason: text(form, "reason") });
}

export function parseLift(form: FormData) {
  return parse(liftSchema, { id: text(form, "id"), note: text(form, "note") });
}

export function parseRoleChange(form: FormData) {
  return parse(roleSchema, { id: text(form, "id"), role: text(form, "role"), reason: text(form, "reason") });
}

export function parseStatusChange(form: FormData) {
  const status = text(form, "status");
  if (status !== "active" && status !== "suspended") return { ok: false as const, errors: { status: "Choose a status." } };
  return parse(statusSchema, { id: text(form, "id"), status, reason: text(form, "reason") });
}

/**
 * The message a person sees when the database refuses an admin change. The
 * database's own messages are matched, so a refusal reads as what it is.
 */
export function refusalText(message: string): string {
  if (/own (role|status)/.test(message)) return "You cannot change your own role or status. Ask another admin.";
  if (/no venture/.test(message)) return "This person has no venture, so they cannot be a founder.";
  if (/no investor profile/.test(message)) return "This person has no investor profile, so they cannot be an investor.";
  if (/already has that/.test(message)) return "Nothing changed, because the account already has that setting.";
  if (/already hidden/.test(message)) return "This profile is already hidden.";
  if (/not hidden/.test(message)) return "This profile has no hold to lift.";
  if (/only admins/.test(message)) return "Only an admin can make this change.";
  return "The change was not saved. Please try again.";
}
