"""Runs the Next.js app's form rules and the Python ones on the same input and compares the results.

This check exists only while both apps exist. It bundles apps/web/lib/forms.ts and the
onboarding rules of lib/account.ts with the esbuild that the web app installs, runs them under
Node, and is skipped once the Next.js app is removed. Each case compares whether the form
passed, the first error of each field, and the rows that would be saved.
"""

from __future__ import annotations

import json
import pathlib
import random
import shutil
import subprocess
import tempfile

import pytest

from app.forms import (
    parse_decision,
    parse_evidence,
    parse_introduction_note,
    parse_message,
    parse_onboarding,
    parse_pitch,
    parse_transcript,
    parse_update,
    parse_venture,
)
from app.discovery import filter_count, match_text, parse_filters, query_string, rpc_args
from app.investor import parse_investor_edit, parse_investor_signup
from app.score_engine import RUBRIC_V2

ROOT = pathlib.Path(__file__).resolve().parents[2]
LIB = ROOT / "apps" / "web" / "lib"
ESBUILD = next(iter(sorted((ROOT / "node_modules" / ".pnpm").glob("esbuild@*/node_modules/esbuild/bin/esbuild"))), None) \
    if (ROOT / "node_modules" / ".pnpm").exists() else None

pytestmark = pytest.mark.skipif(
    not (LIB / "forms.ts").exists() or ESBUILD is None or shutil.which("node") is None,
    reason="the Next.js form rules, their esbuild or Node is not here",
)

ENTRY = f"""
export {{ parseEvidence, parsePitch, parseTranscript, parseUpdate, parseIntroductionNote, parseMessage, parseVenture,
  parseDecision }} from {json.dumps(str(LIB / "forms.ts"))};
export {{ parseOnboarding }} from {json.dumps(str(LIB / "account.ts"))};
export {{ parseInvestorSignUp, parseInvestorEdit }} from {json.dumps(str(LIB / "investor-profile.ts"))};
export {{ parseFilters, rpcArgs, queryString, matchText, filterCount }} from {json.dumps(str(LIB / "discovery.ts"))};
"""

RUNNER = """
import { readFileSync } from "node:fs";
import * as f from "./forms.mjs";
const form = (fields) => { const d = new FormData(); for (const [k, v] of Object.entries(fields)) for (const x of [].concat(v)) d.append(k, x); return d; };
const cases = JSON.parse(readFileSync(0, "utf8"));
const out = cases.map(([kind, input, extra]) => {
  switch (kind) {
    case "onboarding": { const r = f.parseOnboarding(form(input), extra); return r.ok ? { ok: true, data: r.rows } : r; }
    case "decision": return f.parseDecision(form(input));
    case "evidence": return f.parseEvidence(input);
    case "pitch": return f.parsePitch(input);
    case "transcript": return f.parseTranscript(input);
    case "update": return f.parseUpdate(input);
    case "note": return f.parseIntroductionNote(input);
    case "message": return f.parseMessage(input);
    case "venture": return f.parseVenture(input);
    case "investor_signup": { const r = f.parseInvestorSignUp(form(input), extra); return r.ok ? { ok: true, data: { profile: r.profile, investor: r.investor, consents: r.consents } } : r; }
    case "investor_edit": { const r = f.parseInvestorEdit(form(input)); return r.ok ? { ok: true, data: { profile: r.profile, investor: r.investor } } : r; }
    case "filters": {
      const x = f.parseFilters(input);
      return { ok: true, data: { filters: x, rpc: f.rpcArgs(x), query: f.queryString(x), next: f.queryString(x, x.page + 1), count: f.filterCount(x),
        text: [f.matchText(x.page, false), f.matchText(x.page, true)] } };
    }
  }
});
process.stdout.write(JSON.stringify(out));
"""

SPACE = [" ", "\t", "\n", " ", " ", "﻿", "　"]
WEB = [
    "", "kolapay.ng", "https://kolapay.ng", "HTTPS://Example.COM/Path", "http://kolapay.ng/press?a=1#b",
    "javascript:alert(1)", "ftp://files.example.com", "not a site", "localhost", "http://localhost:3000",
    "https://exa mple.com", "https://kolapay.ng/a b", "https://a.b:99999", "https://a.b:", "https://a.b:80",
    "https://[::1]", "https://1.2.3.4", "https://user@kolapay.ng", "//kolapay.ng", "https://.ng", "https://kolapay.",
    "https://ünï.com", "https://exa_mple.com", "https://a..b", "kolapay.ng/press", "www.kolapay.ng",
    "https://kolapay.ng/" + "x" * 290, "x" * 301, "https://instagram.com/learnloop", "mailto:a@b.ng",
    "https://a|b.ng", "https://a%41.ng", "https://a^b.ng", "http:/kolapay.ng", "https:kolapay.ng",
]
TEXT = ["", "Hi", "x" * 9, "x" * 10, "x" * 19, "x" * 20, "Twelve months of bank statements.", "x" * 280,
        "x" * 281, "x" * 600, "x" * 601, "x" * 2000, "x" * 2001, "é" * 25, "😀" * 141, "😀" * 140, "a\nb\nc",
        "We signed our third market association this week."]
NAMES = ["", "A", "Kemi Bello", "  Amara Okafor ", "x" * 120, "x" * 121, "Ọlá Adébáyọ̀"]


def _pad(rng: random.Random, value: str) -> str:
    if rng.random() < 0.3:
        return rng.choice(SPACE) + value + rng.choice(SPACE)
    return value


VALID_ONBOARDING = {
    "fullName": "Amara Okafor", "country": "NG", "city": "Lagos", "institution": "", "graduateStatus": "", "bio": "",
    "ventureName": "LearnLoop", "sector": "Edtech", "stage": "mvp", "description": "", "ask": "", "website": "learnloop.ng",
    "linkedin": "", "x": "", "instagram": "", "confirmedAdult": "on", "acceptedPrivacy": "on",
}


def _onboarding(rng: random.Random) -> list:
    if rng.random() < 0.35:
        # A valid form with one answer changed, so both answers are reached.
        other = _onboarding_fields(rng)
        key = rng.choice(list(other))
        return ["onboarding", {**VALID_ONBOARDING, key: other[key]}, rng.random() < 0.5]
    return ["onboarding", _onboarding_fields(rng), rng.random() < 0.5]


def _onboarding_fields(rng: random.Random) -> dict:
    fields = {
        "fullName": _pad(rng, rng.choice(NAMES)),
        "country": rng.choice(["NG", "GH", "KE", "ZA", "", "ng"]),
        "city": _pad(rng, rng.choice(["", "Lagos", "x" * 80, "x" * 81])),
        "institution": rng.choice(["", "UNILAG", "x" * 121]),
        "graduateStatus": rng.choice(["", "Final-year student", "x" * 81]),
        "bio": rng.choice(["", "I build payments.", "x" * 601]),
        "ventureName": _pad(rng, rng.choice(NAMES[:6])),
        "sector": rng.choice(["Fintech", "Edtech", "Payments", "", "fintech"]),
        "stage": rng.choice(["idea", "mvp", "revenue", "scaling", "unicorn", ""]),
        "description": rng.choice(["", "Card payments for market traders.", "x" * 281]),
        "ask": _pad(rng, rng.choice(["", "Yes", "Funds", "$150,000 to reach 5,000 paying merchants", "x" * 161])),
        "website": _pad(rng, rng.choice(WEB)),
        "linkedin": rng.choice(WEB),
        "x": rng.choice(WEB),
        "instagram": rng.choice(WEB),
    }
    fields = {k: v for k, v in fields.items() if rng.random() > 0.05}
    for box in ("confirmedAdult", "acceptedPrivacy", "consent_evidence_processing", "consent_notifications"):
        if rng.random() < 0.8:
            fields[box] = rng.choice(["on", "on", "on", "yes"])
    if rng.random() < 0.1:
        fields["role"] = "admin"
    return fields


def _evidence(rng: random.Random) -> list:
    codes = [s.code for s in RUBRIC_V2.signals] + ["", "made_up"]
    files = [
        {"name": "a.pdf", "type": rng.choice(["application/pdf", "image/png", "image/jpeg", "text/html", ""]),
         "size": rng.choice([1, 2_000_000, 10 * 1024 * 1024, 10 * 1024 * 1024 + 1, 0])}
        for _ in range(rng.choice([0, 0, 1, 1, 2, 3, 4]))
    ]
    return ["evidence", {"signal": rng.choice(codes), "summary": _pad(rng, rng.choice(TEXT)),
                         "link": _pad(rng, rng.choice(WEB)), "files": files}]


def _pitch(rng: random.Random) -> list:
    body = {
        "path": rng.choice([
            "77777777-7777-7777-7777-777777777777/0b6c2f4e-1111-4222-8333-944455556666.mp4",
            "77777777-7777-7777-7777-777777777777/0b6c2f4e-1111-4222-8333-944455556666.mov",
            "77777777-7777-7777-7777-777777777777/0b6c2f4e-1111-4222-8333-944455556666.avi",
            "../../etc/passwd", "",
        ]),
        "mimeType": rng.choice(["video/mp4", "video/webm", "video/quicktime", "video/x-msvideo"]),
        "size": rng.choice([1, 12_000_000, 50 * 1024 * 1024, 50 * 1024 * 1024 + 1, 0, -5, 1.5]),
        "duration": rng.choice([58.2, 90, 90.01, 0, -1, 0.1, 30]),
        "transcript": _pad(rng, rng.choice(TEXT)),
    }
    return ["pitch", {k: v for k, v in body.items() if rng.random() > 0.05}]


def _decision(rng: random.Random) -> list:
    fields = {
        "decision": rng.choice(["approve", "approve", "reject", "needs_more", "delete", ""]),
        "lane": rng.choice(["human", "government", "source", "ai", ""]),
        "publicNote": _pad(rng, rng.choice(["", "Hi", "Compared with bank statements", "x" * 281])),
        "reason": _pad(rng, rng.choice(["", "No", "Add the last three months.", "x" * 601])),
        "itemCount": rng.choice(["", "3", "3.5", "-1", "1001", "1,000", "twelve", " 7 ", "1e2", "0x10", "Infinity", "1_000",
                                   "0b101", "0o17", "-0x10", "0x", "١٢", "12", ",", "1e400", "0xFFFFFFFFFFFFFFFFFFFFF"]),
        "months": rng.choice(["", "12", "601", "12.0", "abc", ".5", "+6", "6.", "1e1", "+Infinity", "-0"]),
        "revenueUsd": rng.choice(["", "18,000", "18000.75", "-3", "1e13", "lots", "5.", "Infinity"]),
        "stage": rng.choice(["", "idea", "revenue", "unicorn"]),
    }
    return ["decision", {k: v for k, v in fields.items() if rng.random() > 0.1}]


def _venture(rng: random.Random) -> list:
    v = {
        "name": _pad(rng, rng.choice(NAMES)),
        "sector": rng.choice(["Fintech", "Health", "Payments", ""]),
        "stage": rng.choice(["idea", "scaling", "nope"]),
        "description": rng.choice(["", "What it does.", "x" * 281]),
        "website": _pad(rng, rng.choice(WEB)),
    }
    if rng.random() < 0.7:
        v["ask"] = _pad(rng, rng.choice(["", "Yes", "Funds", "$150,000 to reach 5,000 paying merchants", "x" * 161, "   "]))
    return ["venture", v]


def _investor(rng: random.Random) -> list:
    pick = lambda options: rng.choice(options)  # noqa: E731
    fields = {
        "fullName": _pad(rng, pick(NAMES)),
        "basedIn": pick(["NG", "GH", "KE", "other", "", "ZA"]),
        "investorType": pick(["individual", "angel", "fund", "fund", "", "vc"]),
        "firm": _pad(rng, pick(["", "", "Savannah Seed", "x" * 121])),
        "website": pick(WEB),
        "sectors": pick([[], ["Fintech"], ["Fintech", "Health"], ["Fintech", "Fintech"], ["Crypto"], ["Fintech", "Crypto", "Fintech"], "Edtech"]),
        "stages": pick([[], ["idea"], ["idea", "idea"], ["seed"], ["mvp", "revenue", "scaling"]]),
        "countries": pick([[], ["NG"], ["NG", "KE"], ["ZA"], ["GH", "GH"]]),
        "chequeSize": pick(["Under $25,000", "Prefer not to say", "", "A lot", "$25,000 to $100,000"]),
        "thesis": pick(["", "Payments in Lagos.", "x" * 601]),
    }
    if rng.random() < 0.3:
        fields = {**fields, "fullName": "Ife Adeyemi", "basedIn": "NG", "investorType": rng.choice(["angel", "fund"]),
                  "website": "", "sectors": ["Fintech"], "chequeSize": "Prefer not to say", "thesis": "",
                  "firm": rng.choice(["", "Savannah Seed"]), "stages": [], "countries": []}
    fields = {k: v for k, v in fields.items() if rng.random() > 0.05}
    for box in ("confirmedStatement", "confirmedAdult", "acceptedPrivacy", "notifications"):
        if rng.random() < 0.8:
            fields[box] = "on"
    if rng.random() < 0.5:
        return ["investor_signup", fields, rng.random() < 0.5]
    return ["investor_edit", fields]


def _filters(rng: random.Random) -> list:
    values = {
        "sector": ["Fintech", "Health", "Fintech,Health", " Fintech , Agritech ", "Crypto", "", "fintech"],
        "stage": ["idea", "revenue", "unicorn", "idea,idea"],
        "country": ["NG", "KE", "ZA", "NG,GH"],
        "evidence": ["revenue_reviewed", "registry_record", "any_reviewed", "made_up"],
        "activity": ["30", "90", "7", "", "30,90"],
        "page": ["2", "1", "0", "999", "1000", "2.5", "x", "0x3", " 4 ", "", "3,9", "1e2", "-2"],
    }
    params = {}
    for k, options in values.items():
        n = rng.choice([0, 0, 1, 1, 2])
        if n:
            params[k] = [rng.choice(options) for _ in range(n)]
    return ["filters", params]


class _Params(dict):
    def getlist(self, key):
        return list(self.get(key, []))


def _cases() -> list[list]:
    rng = random.Random(20261017)
    cases = []
    for _ in range(400):
        cases += [_onboarding(rng), _evidence(rng), _pitch(rng), _decision(rng), _venture(rng)]
        cases.append(["transcript", {"transcript": _pad(rng, rng.choice(TEXT))}])
        cases.append(["update", {"body": _pad(rng, rng.choice(TEXT))}])
        cases.append(["note", {"note": _pad(rng, rng.choice(TEXT))}])
        cases.append(["message", {"body": _pad(rng, rng.choice(TEXT))}])
        cases.append(_investor(rng))
        cases.append(_filters(rng))
    return cases


def _python(case: list):
    kind, i = case[0], case[1]
    if kind == "onboarding":
        r = parse_onboarding(i, case[2])
    elif kind == "decision":
        r = parse_decision(i)
    elif kind == "evidence":
        r = parse_evidence(i["signal"], i["summary"], i["link"], i["files"])
    elif kind == "pitch":
        r = parse_pitch(i)
    elif kind == "transcript":
        r = parse_transcript(i["transcript"])
    elif kind == "update":
        r = parse_update(i["body"])
    elif kind == "note":
        r = parse_introduction_note(i["note"])
    elif kind == "message":
        r = parse_message(i["body"])
    elif kind == "investor_signup":
        r = parse_investor_signup(i, case[2])
    elif kind == "investor_edit":
        r = parse_investor_edit(i)
    elif kind == "filters":
        x = parse_filters(_Params(i))
        return {"ok": True, "data": {"filters": x, "rpc": rpc_args(x), "query": query_string(x), "next": query_string(x, x["page"] + 1),
                                     "count": filter_count(x), "text": [match_text(x["page"], False), match_text(x["page"], True)]}}
    else:
        r = parse_venture(i["name"], i["sector"], i["stage"], i["description"], i["website"], i.get("ask"))
    return {"ok": True, "data": r.data} if r.ok else {"ok": False, "errors": r.errors}


def _typescript(cases: list[list]) -> list[dict]:
    with tempfile.TemporaryDirectory() as tmp:
        entry = pathlib.Path(tmp) / "entry.ts"
        entry.write_text(ENTRY)
        bundle = pathlib.Path(tmp) / "forms.mjs"
        subprocess.run(
            [str(ESBUILD), str(entry), "--bundle", "--format=esm", "--platform=node", f"--outfile={bundle}"],
            check=True, capture_output=True, cwd=LIB,
        )
        (pathlib.Path(tmp) / "run.mjs").write_text(RUNNER)
        done = subprocess.run(["node", "run.mjs"], cwd=tmp, input=json.dumps(cases), capture_output=True, text=True,
                              check=True)
    return json.loads(done.stdout)


def _same(python: dict, typescript: dict) -> bool:
    if python["ok"] != typescript["ok"]:
        return False
    if not python["ok"]:
        return python["errors"] == typescript["errors"]
    # A pitch's size is a whole number either way; JSON writes 12000000 for both.
    return json.loads(json.dumps(python["data"])) == typescript["data"]


def test_both_apps_read_every_form_the_same_way():
    cases = _cases()
    ts = _typescript(cases)
    differences = [(c, _python(c), t) for c, t in zip(cases, ts, strict=True) if not _same(_python(c), t)]
    shown = "\n".join(f"{c}\n  python:     {p}\n  typescript: {t}" for c, p, t in differences[:5])
    assert not differences, f"{len(differences)} of {len(cases)} cases differ:\n{shown}"
    # The generated cases reach both answers for every form.
    for kind in ("onboarding", "evidence", "pitch", "decision", "venture", "transcript", "update", "note", "message",
                 "investor_signup", "investor_edit"):
        answers = {t["ok"] for c, t in zip(cases, ts, strict=True) if c[0] == kind}
        assert answers == {True, False}, (kind, answers)
