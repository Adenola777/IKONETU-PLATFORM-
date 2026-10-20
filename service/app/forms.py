"""The rules for the forms of the founder, investor and staff pages.

Ported from apps/web/lib/forms.ts and the onboarding part of lib/account.ts. Each rule
matches a check in the database, so a form reports a problem before the database refuses
the row. Each field keeps the first message its zod schema would have given.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

from .product import SECTORS, STAGES
from .score_engine import RUBRIC_V3
from .validate import Errors, is_web_address, js_len, js_trim
from .waitlist import COUNTRY_CODES, PRIVACY_VERSION

STAGE_CODES = tuple(s["code"] for s in STAGES)
# The signals a founder can add evidence for today. Those that need a provider IkonetU does not
# have yet are left out.
SIGNAL_CODES = tuple(s.code for s in RUBRIC_V3.signals if s.offered)
SELF_DECLARED = frozenset(s.code for s in RUBRIC_V3.signals if s.how == "self")


@dataclass
class Parsed:
    ok: bool
    data: dict = field(default_factory=dict)
    errors: dict = field(default_factory=dict)


def _done(errors: Errors, data: dict) -> Parsed:
    return Parsed(ok=False, errors=dict(errors)) if errors else Parsed(ok=True, data=data)


def _text(errors: Errors, key: str, value, min_len: int | None = None, min_msg: str = "",
          max_len: int | None = None, max_msg: str = "") -> str:
    v = js_trim(value if isinstance(value, str) else "")
    if min_len is not None and js_len(v) < min_len:
        errors.add(key, min_msg)
    if max_len is not None and js_len(v) > max_len:
        errors.add(key, max_msg)
    return v


def _optional(errors: Errors, key: str, value, max_len: int, message: str) -> str | None:
    v = _text(errors, key, value, max_len=max_len, max_msg=message)
    return v or None


def _web(errors: Errors, key: str, value, max_len: int, too_long: str, message: str) -> str | None:
    """A web address. A bare domain gets https:// added."""
    v = js_trim(value if isinstance(value, str) else "")
    if js_len(v) > max_len:
        errors.add(key, too_long)
        return v
    if v == "":
        return None
    if not re.match(r"https?://", v, re.IGNORECASE):
        v = f"https://{v}"
    if not is_web_address(v):
        errors.add(key, message)
    return v


# ---------------------------------------------------------------- onboarding (lib/account.ts)
ADULT = "You must be 18 or older to join."

# The consents a founder gives before any data is processed (PRD A-4, SRD SEC-D4). The
# profile is needed to run the account, so it is required. The others are optional, and
# each answer is recorded, including a no. Consents for registry lookups and bank
# statements return when those checks exist; the database still accepts them.
OPTIONAL_CONSENTS = (
    {"code": "evidence_processing", "label": "Check the evidence I submit. An IkonetU reviewer compares it with its source"},
    {"code": "notifications", "label": "Send me notifications about my evidence and introductions. IkonetU does not send them yet"},
)


def parse_onboarding(form: dict, adult_confirmed: bool = False) -> Parsed:
    """Reads the founder onboarding form. The person's ids are added by the caller, from the session."""
    t = lambda k: form.get(k) if isinstance(form.get(k), str) else ""  # noqa: E731
    e = Errors()
    full_name = _text(e, "fullName", t("fullName"), 2, "Enter your full name.", 120, "Your name is too long.")
    country = t("country")
    if country not in COUNTRY_CODES:
        e.add("country", "Choose your country.")
    city = _optional(e, "city", t("city"), 80, "The city name is too long.")
    institution = _optional(e, "institution", t("institution"), 120, "The institution name is too long.")
    graduate = _optional(e, "graduateStatus", t("graduateStatus"), 80, "Keep this to 80 characters.")
    bio = _optional(e, "bio", t("bio"), 600, "Keep your bio to 600 characters.")
    venture_name = _text(e, "ventureName", t("ventureName"), 1, "Enter your venture's name.", 120, "The venture name is too long.")
    sector = t("sector")
    if sector not in SECTORS:
        e.add("sector", "Choose your sector.")
    stage = t("stage")
    if stage not in STAGE_CODES:
        e.add("stage", "Choose your stage.")
    description = _optional(e, "description", t("description"), 280, "Keep the description to 280 characters.")
    ask = _optional(e, "ask", t("ask"), 160, "Keep the ask to 160 characters.")
    if ask is not None and "ask" not in e and js_len(ask) < 5:
        e.add("ask", "Write at least 5 characters, or leave it empty.")
    website = _web(e, "website", t("website"), 200, "Enter a full web address, for example learnloop.ng.", "Enter a full web address, for example learnloop.ng.")
    linkedin = _web(e, "linkedin", t("linkedin"), 200, "Enter a full LinkedIn address.", "Enter a full LinkedIn address.")
    x = _web(e, "x", t("x"), 200, "Enter a full X address.", "Enter a full X address.")
    instagram = _web(e, "instagram", t("instagram"), 200, "Enter a full Instagram address.", "Enter a full Instagram address.")
    if not (adult_confirmed or t("confirmedAdult") == "on"):
        e.add("confirmedAdult", ADULT)
    if t("acceptedPrivacy") != "on":
        e.add("acceptedPrivacy", "Please confirm you have read the privacy policy.")
    if e:
        return Parsed(ok=False, errors=dict(e))
    social = {k: v for k, v in (("linkedin", linkedin), ("x", x), ("instagram", instagram)) if v}
    return Parsed(ok=True, data={
        "profile": {
            "full_name": full_name, "country": country, "city": city, "institution": institution,
            "graduate_status": graduate, "bio": bio, "confirmed_adult": True,
        },
        "consents": [
            {"consent_type": "profile", "granted": True, "policy_version": PRIVACY_VERSION},
            *({"consent_type": c["code"], "granted": t(f"consent_{c['code']}") == "on", "policy_version": PRIVACY_VERSION}
              for c in OPTIONAL_CONSENTS),
        ],
        "venture": {
            "name": venture_name, "sector": sector, "stage": stage, "country": country, "description": description,
            "ask": ask, "website": website, "social_links": social,
        },
    })


# ---------------------------------------------------------------- evidence
EVIDENCE_FILE_TYPES = ("application/pdf", "image/jpeg", "image/png")
EVIDENCE_FILE_MAX = 10 * 1024 * 1024
EVIDENCE_FILES_MAX = 3


def parse_evidence(signal: str, summary: str, link: str, files: list[dict]) -> Parsed:
    """A piece of evidence, or the founder's own statement for a self-declared signal.

    A statement is the sentence alone: it takes no file and no link, because nobody reviews it.
    """
    e = Errors()
    aborted = signal not in SIGNAL_CODES
    if aborted:
        e.add("signal", "Choose what this evidence shows.")
    if not aborted and signal in SELF_DECLARED:
        said = _text(e, "summary", summary, 10, "Write your statement in at least 10 characters.", 280,
                     "Keep the statement to 280 characters.")
        return _done(e, {"signal": signal, "summary": said, "link": None, "files": [], "statement": True})
    summary_v = _text(e, "summary", summary, 10, "Describe the evidence in at least 10 characters.", 280, "Keep the description to 280 characters.")
    link_v = _web(e, "link", link, 300, "That address is too long.", "Enter a full web address, for example kolapay.ng/press.")
    if len(files) > EVIDENCE_FILES_MAX:
        e.add("files", f"Add up to {EVIDENCE_FILES_MAX} files.")
    if not all(f["type"] in EVIDENCE_FILE_TYPES for f in files):
        e.add("files", "Add PDF, JPEG or PNG files only.")
    if not all(0 < f["size"] <= EVIDENCE_FILE_MAX for f in files):
        e.add("files", "Each file must be 10 MB or smaller.")
    # The rule across fields runs only when no field failed outright.
    if not aborted and not files and link_v is None:
        e.add("files", "Add a file or a link, so a reviewer can check it.")
    return _done(e, {"signal": signal, "summary": summary_v, "link": link_v, "files": files, "statement": False})


def signal_options() -> list[dict]:
    """The signals a founder can add evidence for, with their category, label and what to send."""
    return [{"code": s.code, "label": s.label, "category": s.category, "how": s.how, "hint": s.hint}
            for s in RUBRIC_V3.signals if s.offered]


def signal_label(code: str) -> str:
    s = RUBRIC_V3.signal(code)
    return s.label if s else code


def signal_area(code: str) -> str:
    s = RUBRIC_V3.signal(code)
    return s.category if s else ""


# ---------------------------------------------------------------- pitch
PITCH_TYPES = ("video/mp4", "video/webm", "video/quicktime")
PITCH_MAX_BYTES = 50 * 1024 * 1024
PITCH_MAX_SECONDS = 90
PITCH_PATH = re.compile(r"[0-9a-f-]{36}/[0-9a-f-]{36}\.(mp4|webm|mov)")
TRANSCRIPT_SHORT = "Type what you say in the pitch, in at least 20 characters."
TRANSCRIPT_LONG = "Keep the transcript to 2,000 characters."


_MISSING = object()


def _received(v) -> str:
    """The type zod names in "Expected string, received number"."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "boolean"
    if isinstance(v, (int, float)):
        return "nan" if v != v else "number"
    if isinstance(v, str):
        return "string"
    if isinstance(v, list):
        return "array"
    return "object" if isinstance(v, dict) else "unknown"


def _wrong_type(body: dict, key: str, kind: str) -> str | None:
    """zod's message for a field that is missing or of another type, or None when the type is right."""
    v = body.get(key, _MISSING)
    if v is _MISSING:
        return "Required"
    got = _received(v)
    return None if got == kind else f"Expected {kind}, received {got}"


def parse_pitch(body: object) -> Parsed:
    """The pitch the browser records after its upload. It arrives as JSON, so each field's type is checked first."""
    if not isinstance(body, dict):
        return Parsed(ok=False, errors={"form": f"Expected object, received {_received(body)}"})
    e = Errors()
    path = body.get("path")
    wrong = _wrong_type(body, "path", "string")
    if wrong or not PITCH_PATH.fullmatch(path):
        e.add("path", wrong or "The upload did not finish. Please try again.")
    if body.get("mimeType") not in PITCH_TYPES:
        e.add("mimeType", "Upload an MP4, WebM or MOV video.")
    size = body.get("size")
    wrong = _wrong_type(body, "size", "number")
    if wrong:
        e.add("size", wrong)
    elif not float(size).is_integer():
        e.add("size", "Expected integer, received float")
    elif size <= 0:
        e.add("size", "Number must be greater than 0")
    elif size > PITCH_MAX_BYTES:
        e.add("size", "The video must be 50 MB or smaller.")
    duration = body.get("duration")
    wrong = _wrong_type(body, "duration", "number")
    if wrong:
        e.add("duration", wrong)
    elif duration <= 0:
        e.add("duration", "We could not read the video's length.")
    elif duration > PITCH_MAX_SECONDS:
        e.add("duration", "Keep the pitch to 90 seconds or less.")
    wrong = _wrong_type(body, "transcript", "string")
    if wrong:
        e.add("transcript", wrong)
        transcript = ""
    else:
        transcript = _text(e, "transcript", body["transcript"], 20, TRANSCRIPT_SHORT, 2000, TRANSCRIPT_LONG)
    if e:
        return Parsed(ok=False, errors=dict(e))
    return Parsed(ok=True, data={"path": path, "mimeType": body["mimeType"], "size": int(size), "duration": float(duration),
                                 "transcript": transcript})


def parse_transcript(value: str) -> Parsed:
    e = Errors()
    transcript = _text(e, "transcript", value, 20, TRANSCRIPT_SHORT, 2000, TRANSCRIPT_LONG)
    return _done(e, {"transcript": transcript})


# ---------------------------------------------------------------- updates, notes and messages
def parse_update(value: str) -> Parsed:
    e = Errors()
    body = _text(e, "body", value, 10, "Write at least 10 characters.", 600, "Keep the update to 600 characters.")
    return _done(e, {"body": body})


def parse_introduction_note(value: str) -> Parsed:
    e = Errors()
    note = _text(e, "note", value, 20, "Say why you want to talk, in at least 20 characters.", 600, "Keep the note to 600 characters.")
    return _done(e, {"note": note})


def parse_message(value: str) -> Parsed:
    e = Errors()
    body = _text(e, "body", value, 1, "Write a message.", 2000, "Keep the message to 2,000 characters.")
    return _done(e, {"body": body})


# ---------------------------------------------------------------- venture details
def parse_venture(name: str, sector: str, stage: str, description: str, website: str, ask: str | None = None) -> Parsed:
    e = Errors()
    name_v = _text(e, "name", name, 1, "Enter your venture's name.", 120, "The venture name is too long.")
    if sector not in SECTORS:
        e.add("sector", "Choose your sector.")
    if stage not in STAGE_CODES:
        e.add("stage", "Choose your stage.")
    description_v = _optional(e, "description", description, 280, "Keep the description to 280 characters.")
    website_v = _web(e, "website", website, 300, "That address is too long.", "Enter a full web address, for example kolapay.ng.")
    ask_v = None
    if ask is not None:
        ask_v = _optional(e, "ask", ask, 160, "Keep the ask to 160 characters.")
        if ask_v is not None and "ask" not in e and js_len(ask_v) < 5:
            e.add("ask", "Write at least 5 characters, or leave it empty.")
    return _done(e, {"name": name_v, "sector": sector, "stage": stage, "description": description_v,
                     "website": website_v, "ask": ask_v})


# ---------------------------------------------------------------- staff decisions
REVIEW_LANES = (
    {"code": "human", "name": "Platform reviewed", "hint": "You compared it with its source, such as a statement, a document or a live product."},
    {"code": "government", "name": "Third-party evidence: a government record", "hint": "A government registry or authority holds a matching record, and you found it there yourself or the registry confirmed it."},
    {"code": "source", "name": "Third-party evidence: another outside source", "hint": "An outside source backs it, such as a bank, a customer or a publisher."},
)


_JS_DECIMAL = re.compile(r"[+-]?(?:[0-9]+\.?[0-9]*|\.[0-9]+)(?:[eE][+-]?[0-9]+)?")
_JS_PREFIXED = {"0x": (16, re.compile(r"[0-9a-fA-F]+")), "0o": (8, re.compile(r"[0-7]+")), "0b": (2, re.compile(r"[01]+"))}


def js_number(text: str) -> float:
    """Number() of a string, as JavaScript converts it: "" is 0, 0x10 is 16, and anything else it cannot read is NaN."""
    t = js_trim(text)
    if t == "":
        return 0.0
    if t in ("Infinity", "+Infinity", "-Infinity"):
        return -math.inf if t[0] == "-" else math.inf
    prefixed = _JS_PREFIXED.get(t[:2].lower())
    if prefixed:
        base, digits = prefixed
        if not digits.fullmatch(t[2:]):
            return math.nan
        try:
            return float(int(t[2:], base))
        except OverflowError:
            return math.inf
    return float(t) if _JS_DECIMAL.fullmatch(t) else math.nan


def parse_decision(form: dict) -> Parsed:
    def text(k):
        v = form.get(k, "")
        return js_trim(v if isinstance(v, str) else "")

    decision = text("decision")
    if decision not in ("approve", "reject", "needs_more"):
        return Parsed(ok=False, errors={"decision": "Choose a decision."})
    e = Errors()
    if decision == "approve":
        lane = text("lane")
        if lane not in ("human", "government", "source"):
            e.add("lane", "Choose how you checked it.")
        note = _text(e, "publicNote", text("publicNote"), 5, "Say what you compared, in a sentence investors will read.",
                     280, "Keep the note to 280 characters.")
        values: dict = {"decision": decision, "lane": lane, "publicNote": note}
        for key, low, high, message, whole in (("itemCount", 0, 1000, "Enter a whole number.", True),
                                               ("months", 0, 600, "Enter a whole number.", True),
                                               ("revenueUsd", 0, 1e12, "Enter an amount in US dollars.", False)):
            raw = text(key)
            if raw == "":
                values[key] = None
                continue
            # The Next.js app read an amount as Number() of the text with its commas removed.
            n = js_number(raw.replace(",", ""))
            if math.isnan(n):
                e.add(key, message)
                continue
            if whole and not float(n).is_integer():
                e.add(key, "Enter a whole number.")
            if n < low:
                e.add(key, f"Number must be greater than or equal to {low}")
            if n > high:
                e.add(key, f"Number must be less than or equal to {int(high) if float(high).is_integer() else high}")
            values[key] = int(n) if whole and float(n).is_integer() else n
        stage = text("stage")
        if stage and stage not in STAGE_CODES:
            e.add("stage", "Invalid enum value. Expected 'idea' | 'mvp' | 'revenue' | 'scaling', received '%s'" % stage)
        values["stage"] = stage or None
        return _done(e, values)
    reason = _text(e, "reason", text("reason"), 5, "Give the founder a reason, in a sentence.", 600, "Keep the reason to 600 characters.")
    return _done(e, {"decision": decision, "reason": reason})
