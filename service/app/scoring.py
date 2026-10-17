"""The score engine as the pages use it: a founder's next steps, and recording a venture's score.

Ported from apps/web/lib/next-steps.ts and lib/scoring.ts.
"""

from __future__ import annotations

from .guards import with_retry
from .log import log_error, log_warn
from .score_engine import RUBRIC_V2, EvidenceItem, calculate_score, next_best_actions
from .supabase import Database

WAITING = {"submitted", "checking", "needs_review"}
EVIDENCE_COLUMNS = "id, signal_code, status, lane, expires_at, item_count, months, revenue_usd, stage"


def _items(rows: list[dict]) -> list[EvidenceItem]:
    return [
        EvidenceItem(
            id=r["id"], signal_code=r["signal_code"], status=r["status"], lane=r["lane"], expires_at=r.get("expires_at"),
            item_count=r.get("item_count"), months=r.get("months"),
            revenue_usd=None if r.get("revenue_usd") is None else float(r["revenue_usd"]), stage=r.get("stage"),
        )
        for r in rows
        if r.get("lane")
    ]


def next_steps(evidence: list[dict], limit: int = 3) -> list:
    """The founder's next three steps: the evidence the score engine says would add most next,
    leaving out anything already waiting for a reviewer."""
    waiting = {e["signal_code"] for e in evidence if e["status"] in WAITING}
    result = calculate_score(_items(evidence), RUBRIC_V2)
    actions = next_best_actions(result, RUBRIC_V2, len(RUBRIC_V2.signals))
    return [a for a in actions if a.code not in waiting][:limit]


async def record_venture_score(db: Database, venture_id: str, cause: str | None, sleep=None) -> bool:
    """Recomputes a venture's score from its evidence and records it through record_score(), as staff.

    record_score() is safe to repeat: the same total only refreshes the current row and writes
    no second history row. So a failed attempt is tried again, three times in all, and a score
    that still fails stays on the staff list of scores to update (ventures_with_stale_scores)
    until someone recomputes it.
    """
    async def step():
        rows = await db.table("evidence").eq("venture_id", venture_id).select(EVIDENCE_COLUMNS)
        if not rows.ok:
            return False, rows.error.code or rows.error.message
        score = calculate_score(_items(rows.data or []), RUBRIC_V2)
        recorded = await db.rpc("record_score", {
            "p_venture": venture_id, "p_total": score.total, "p_league": score.league,
            "p_categories": [c.as_record() for c in score.categories], "p_rubric": score.rubric_version,
            "p_cause": cause,
        })
        if not recorded.ok:
            return False, recorded.error.code or recorded.error.message
        return True, score.total

    kwargs = {"sleep": sleep} if sleep else {}
    result = await with_retry(step, **kwargs)
    if not result.ok:
        log_error("score.record_failed", {"venture": venture_id, "attempts": result.attempts, "code": result.error})
        return False
    if result.attempts > 1:
        log_warn("score.recorded_after_retry", {"venture": venture_id, "attempts": result.attempts})
    return True
