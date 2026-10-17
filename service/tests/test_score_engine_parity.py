"""Runs the TypeScript score engine and the Python one on the same evidence and compares every field.

This check exists only while both engines exist. It bundles
packages/score-engine/src/index.ts with the esbuild that the web app installs,
runs it under Node, and is skipped once the TypeScript engine is removed.
"""

from __future__ import annotations

import json
import pathlib
import random
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from app.score_engine import LANES, EVIDENCE_STATUSES, PRODUCT_STAGES, RUBRIC_V2, EvidenceItem, calculate_score, next_best_actions

ROOT = pathlib.Path(__file__).resolve().parents[2]
TS_ENGINE = ROOT / "packages" / "score-engine" / "src" / "index.ts"
ESBUILD = next(iter(sorted((ROOT / "node_modules" / ".pnpm").glob("esbuild@*/node_modules/esbuild/bin/esbuild"))), None) \
    if (ROOT / "node_modules" / ".pnpm").exists() else None

pytestmark = pytest.mark.skipif(
    not TS_ENGINE.exists() or ESBUILD is None or shutil.which("node") is None,
    reason="the TypeScript engine, its esbuild or Node is not here",
)

RUNNER = """
import { readFileSync } from "node:fs";
import { calculateScore, nextBestActions, RUBRIC_V2 } from "./engine.mjs";
const cases = JSON.parse(readFileSync(0, "utf8"));
const out = cases.map((c) => {
  const score = calculateScore({ evidence: c.evidence, rubric: RUBRIC_V2, now: new Date(c.now) });
  return { score, actions: nextBestActions(score, RUBRIC_V2, RUBRIC_V2.signals.length) };
});
process.stdout.write(JSON.stringify(out));
"""

NOW = datetime(2026, 10, 17, 9, 30, tzinfo=timezone.utc)


def _expiry(rng: random.Random) -> str | None:
    pick = rng.randrange(9)
    if pick < 4:
        return None
    if pick == 4:
        return "not a date"
    if pick == 5:
        return NOW.strftime("%Y-%m-%dT%H:%M:%SZ")  # exactly now, which no longer counts
    shift = timedelta(days=rng.randint(-400, 400), seconds=rng.randint(-5, 5))
    when = NOW + shift
    if pick == 6:
        return when.strftime("%Y-%m-%d")
    if pick == 7:
        return when.astimezone(timezone(timedelta(hours=1))).isoformat()
    return when.isoformat()


def _case(rng: random.Random, n: int) -> list[dict]:
    codes = [s.code for s in RUBRIC_V2.signals] + ["unknown_signal"]
    items = []
    for i in range(n):
        items.append({
            "id": f"e{i}",
            "signalCode": rng.choice(codes),
            "status": rng.choice(EVIDENCE_STATUSES + ("approved",) * 6),
            "lane": rng.choice(LANES),
            "expiresAt": _expiry(rng),
            "itemCount": rng.choice([None, 0, 1, 2, 3, 5, 8, 20, 100, -2]),
            "months": rng.choice([None, 0, 1, 3, 6, 9, 12, 30, 100]),
            "revenueUsd": rng.choice([None, 0, 99.99, 100, 4_250, 4_250.5, 18_000, 50_000, 1_000_000]),
            "stage": rng.choice((None,) + PRODUCT_STAGES),
        })
    return items


def _strong_case(rng: random.Random) -> list[dict]:
    """A profile with approved evidence for most signals, so totals reach Investable and Elite."""
    items = []
    for i, s in enumerate(RUBRIC_V2.signals):
        if s.code != "company_registration" and rng.random() < 0.15:
            continue
        items.append({
            "id": f"s{i}",
            "signalCode": s.code,
            "status": "approved",
            "lane": rng.choice(("government", "source", "human_confirmed", "ai", "human")),
            "expiresAt": None,
            "itemCount": rng.choice([None, 3, 8, 100]),
            "months": rng.choice([6, 12, 100]),
            "revenueUsd": rng.choice([18_000, 1_000_000]),
            "stage": rng.choice(PRODUCT_STAGES),
        })
    return items


def _python(evidence: list[dict]) -> dict:
    items = [
        EvidenceItem(
            id=e["id"], signal_code=e["signalCode"], status=e["status"], lane=e["lane"], expires_at=e["expiresAt"],
            item_count=e["itemCount"], months=e["months"], revenue_usd=e["revenueUsd"], stage=e["stage"],
        )
        for e in evidence
    ]
    r = calculate_score(items, RUBRIC_V2, NOW)
    actions = next_best_actions(r, RUBRIC_V2, len(RUBRIC_V2.signals))
    return {
        "score": {
            "rubricVersion": r.rubric_version,
            "total": r.total,
            "league": r.league,
            "isRegistered": r.is_registered,
            "unregisteredCapApplied": r.unregistered_cap_applied,
            "categories": [
                {"category": c.category, "uncapped": c.uncapped, "cap": c.cap, "earned": c.earned} for c in r.categories
            ],
            "signals": [
                {"code": s.code, "category": s.category, "weighted": s.weighted, "capped": s.capped,
                 "maxPoints": s.max_points, "evidenceIds": s.evidence_ids}
                for s in r.signals
            ],
        },
        "actions": [
            {"code": a.code, "label": a.label, "category": a.category, "estimatedGain": a.estimated_gain} for a in actions
        ],
    }


def _typescript(cases: list[list[dict]]) -> list[dict]:
    # The TypeScript engine treats a missing optional field as undefined, so None fields are left out.
    payload = [{"now": NOW.isoformat(), "evidence": [{k: v for k, v in e.items() if v is not None} for e in c]} for c in cases]
    with tempfile.TemporaryDirectory() as tmp:
        bundle = pathlib.Path(tmp) / "engine.mjs"
        subprocess.run(
            [str(ESBUILD), str(TS_ENGINE), "--bundle", "--format=esm", "--platform=node", f"--outfile={bundle}"],
            check=True, capture_output=True,
        )
        (pathlib.Path(tmp) / "run.mjs").write_text(RUNNER)
        done = subprocess.run(
            ["node", "run.mjs"], cwd=tmp, input=json.dumps(payload), capture_output=True, text=True, check=True,
        )
    return json.loads(done.stdout)


def test_both_engines_agree_on_2000_generated_profiles():
    rng = random.Random(20261017)
    cases = [_case(rng, rng.randint(0, 30)) for _ in range(1500)] + [_strong_case(rng) for _ in range(500)]
    ts = _typescript(cases)
    differences = []
    for i, (c, expected) in enumerate(zip(cases, ts, strict=True)):
        got = _python(c)
        if got != expected:
            differences.append(i)
    assert not differences, f"{len(differences)} profiles differ, the first is case {differences[0]}"
    # The generated profiles reach every league, so the comparison covers the whole range.
    leagues = {t["score"]["league"] for t in ts}
    assert leagues == {"EARLY", "RISING", "INVESTABLE", "ELITE"}, leagues
