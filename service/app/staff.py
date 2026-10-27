"""Names, rules and wording for the staff pages. Ported from apps/web/lib/admin.ts.

The database functions of migration 20261017000001 check every change again, so these rules only
let a form report a problem before the database refuses it.
"""

from __future__ import annotations

import re

from .forms import Parsed
from .validate import Errors, js_len, js_trim

ROLE_NAME = {"founder": "Founder", "investor": "Investor", "mentor": "Mentor", "reviewer": "Reviewer", "admin": "Admin"}
ACCOUNT_STATUS_NAME = {"active": "Active", "pending": "Waiting for approval", "suspended": "Suspended"}

# The roles an admin can give, in the order the form lists them.
GIVABLE_ROLES = ("founder", "investor", "reviewer", "admin")


def roles_for(current: str, venture: bool, investor_profile: bool) -> list[str]:
    """The roles a person can move to. A founder role needs a venture and an investor role an investor profile."""
    return [r for r in GIVABLE_ROLES
            if r != current and (r != "founder" or venture) and (r != "investor" or investor_profile)]


# What each audit log action means, in a sentence fragment that follows the person's name.
ACTION_TEXT = {
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
    "register.add": "added entries to the investor register",
    "register.import": "loaded the founder register, the introductions and the pitch videos from the admin design",
    "register.founder_delete": "deleted a founder record",
    "register.link": "linked a register entry to an investor account",
    "register.unlink": "unlinked a register entry from an investor account",
    "account.remove_signup": "removed a sign-up that had chosen no role",
    "introduction.status": "changed the status of an introduction",
    "video.approve": "approved a pitch video",
    "video.reject": "rejected a pitch video",
    "video.reopen": "returned a pitch video to review",
    "report.resolve": "resolved a report",
    "settings.pitch": "changed the pitch rules",
    "settings.introductions": "changed the introduction rules",
    "settings.mode": "changed the platform mode",
}

ID = re.compile(r"[0-9a-f-]{36}")


def action_text(action: str) -> str:
    return ACTION_TEXT.get(action, action)


def entity_href(entity: str, entity_id: str | None) -> str | None:
    """The page that shows the record an audit log entry is about, if there is one."""
    if not entity_id or not ID.fullmatch(entity_id):
        return None
    return {"profiles": f"/admin/people/{entity_id}", "ventures": f"/admin/founders/{entity_id}",
            "evidence": f"/admin/evidence/{entity_id}"}.get(entity)


FIELD_NAME = {
    "status": "Status", "role": "Role", "lane": "Checked by", "published_at": "Published to investors", "hidden_at": "Hold",
    "public_note": "Note for investors", "pitch_types": "File types", "pitch_max_mb": "Largest file, MB",
    "pitch_max_seconds": "Longest pitch, seconds", "introductions_on": "Introduction requests",
    "introductions_per_day": "Requests per investor per day", "mode": "Mode", "maintenance_message": "Maintenance message",
}
# The status of a record other than an account, in the words of the page that shows it.
STATUS_BY_ENTITY = {
    "register_introductions": {"pending": "Pending", "accepted": "Accepted", "declined": "Declined", "withdrawn": "Withdrawn"},
    "pitch_video_files": {"pending": "Pending review", "approved": "Approved", "rejected": "Rejected"},
    "reports": {"open": "Open", "resolved": "Resolved"},
}
VIDEO_TYPE_NAME = {"video/mp4": "MP4", "video/webm": "WebM", "video/quicktime": "MOV"}
EVIDENCE_STATUS_NAME = {
    "submitted": "Waiting for review", "checking": "Waiting for review", "needs_review": "Waiting for review",
    "approved": "Approved", "rejected": "Rejected", "needs_more": "More asked for", "expired": "Expired",
}
LANE_NAME = {"human": "an IkonetU reviewer", "government": "a government record", "source": "another outside source"}


def _js_string(v) -> str:
    """String(v) of a JSON value, as JavaScript writes it."""
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    if isinstance(v, (dict, list)):
        return "[object Object]" if isinstance(v, dict) else ",".join("" if x is None else _js_string(x) for x in v)
    return str(v)


def _value_text(key: str, v, entity: str | None = None) -> str:
    empty = v is None or v == ""
    if key == "published_at":
        return "no" if empty else "yes"
    if key == "hidden_at":
        return "off" if empty else "on"
    if key == "introductions_on" and isinstance(v, bool):
        return "on" if v else "off"
    if empty:
        return "none"
    if key == "pitch_types" and isinstance(v, list):
        return ", ".join(VIDEO_TYPE_NAME.get(x, str(x)) for x in v)
    if key == "status" and entity in STATUS_BY_ENTITY and v in STATUS_BY_ENTITY[entity]:
        return STATUS_BY_ENTITY[entity][v]
    if key == "mode" and v in ("live", "maintenance"):
        return v.capitalize()
    if isinstance(v, str):
        if key == "role" and v in ROLE_NAME:
            return ROLE_NAME[v]
        if key == "status" and v in ACCOUNT_STATUS_NAME:
            return ACCOUNT_STATUS_NAME[v]
        if key == "status" and v in EVIDENCE_STATUS_NAME:
            return EVIDENCE_STATUS_NAME[v]
        if key == "lane" and v in LANE_NAME:
            return LANE_NAME[v]
    return _js_string(v)


def change_lines(before: dict | None, after: dict | None, entity: str | None = None) -> list[str]:
    """The fields an audit log entry changed, as "Status: Waiting for approval to Active". The entity names the
    kind of record, because a status means something else on an introduction than on an account.

    The reason, the note and the count of hidden profiles are shown apart, so they are left out here.
    """
    skip = {"reason", "note", "profiles_hidden"}
    keys: list[str] = []
    for k in [*(before or {}), *(after or {})]:
        if k not in keys and k not in skip:
            keys.append(k)
    lines = []
    for k in keys:
        a, b = _value_text(k, (before or {}).get(k), entity), _value_text(k, (after or {}).get(k), entity)
        if a != b:
            lines.append(f"{FIELD_NAME.get(k, k)}: {a} to {b}")
    return lines


def entry_reason(after: dict | None) -> str | None:
    """The reason or note an admin gave, if the entry carries one."""
    r = (after or {}).get("reason")
    if r is None:
        r = (after or {}).get("note")
    return r if isinstance(r, str) and js_trim(r) else None


# ---------------------------------------------------------------- forms
NOT_FOUND = "This record could not be found."
TOO_LONG = "Keep it to 280 characters."


def _id(e: Errors, value: str) -> None:
    if not ID.fullmatch(value):
        e.add("id", NOT_FOUND)


def _required(e: Errors, key: str, value: str, message: str) -> str:
    v = js_trim(value)
    if js_len(v) < 5:
        e.add(key, message)
    if js_len(v) > 280:
        e.add(key, TOO_LONG)
    return v


def _optional(e: Errors, key: str, value: str) -> str | None:
    v = js_trim(value)
    if js_len(v) > 280:
        e.add(key, TOO_LONG)
    return v or None


def _text(form: dict, key: str) -> str:
    v = form.get(key, "")
    if isinstance(v, list):
        v = v[0] if v else ""
    return v if isinstance(v, str) else ""


def _done(e: Errors, data: dict) -> Parsed:
    return Parsed(ok=False, errors=dict(e)) if e else Parsed(ok=True, data=data)


def parse_hold(form: dict) -> Parsed:
    e = Errors()
    _id(e, _text(form, "id"))
    reason = _required(e, "reason", _text(form, "reason"), "Tell the founder why, in at least five characters. The founder reads this.")
    return _done(e, {"id": _text(form, "id"), "reason": reason})


def parse_lift(form: dict) -> Parsed:
    e = Errors()
    _id(e, _text(form, "id"))
    note = _optional(e, "note", _text(form, "note"))
    return _done(e, {"id": _text(form, "id"), "note": note})


def parse_role_change(form: dict) -> Parsed:
    e = Errors()
    _id(e, _text(form, "id"))
    role = _text(form, "role")
    if role not in GIVABLE_ROLES:
        e.add("role", "Choose a role.")
    reason = _optional(e, "reason", _text(form, "reason"))
    return _done(e, {"id": _text(form, "id"), "role": role, "reason": reason})


def parse_status_change(form: dict) -> Parsed:
    status = _text(form, "status")
    if status not in ("active", "suspended"):
        return Parsed(ok=False, errors={"status": "Choose a status."})
    e = Errors()
    _id(e, _text(form, "id"))
    if status == "suspended":
        reason = _required(e, "reason", _text(form, "reason"), "Give a reason for the suspension, in at least five characters.")
    else:
        reason = _optional(e, "reason", _text(form, "reason"))
    return _done(e, {"id": _text(form, "id"), "status": status, "reason": reason})


def refusal_text(message: str) -> str:
    """The message a person sees when the database refuses an admin change, matched on the database's own words."""
    for pattern, text in (
        (r"own (role|status)", "You cannot change your own role or status. Ask another admin."),
        (r"no venture", "This person has no venture, so they cannot be a founder."),
        (r"no investor profile", "This person has no investor profile, so they cannot be an investor."),
        (r"already has that", "Nothing changed, because the account already has that setting."),
        (r"already hidden", "This profile is already hidden."),
        (r"not hidden", "This profile has no hold to lift."),
        (r"only admins", "Only an admin can make this change."),
    ):
        if re.search(pattern, message or ""):
            return text
    return "The change was not saved. Please try again."
