"""The score engine as the pages use it: a founder's score and next steps, and recording a venture's score."""

from __future__ import annotations

from .guards import with_retry
from .log import log_error, log_warn
from .score_engine import RUBRIC_V3, EvidenceItem, ScoreResult, calculate_score, next_best_actions
from .supabase import Database

WAITING = {"submitted", "checking", "needs_review"}
EVIDENCE_COLUMNS = "id, signal_code, status, lane, expires_at"


def _items(rows: list[dict]) -> list[EvidenceItem]:
    return [
        EvidenceItem(id=r["id"], signal_code=r["signal_code"], status=r["status"], lane=r["lane"], expires_at=r.get("expires_at"))
        for r in rows
        if r.get("lane")
    ]


def venture_score(evidence: list[dict]) -> ScoreResult:
    """The score the evidence earns now, calculated the same way record_venture_score records it."""
    return calculate_score(_items(evidence), RUBRIC_V3)


def next_steps(evidence: list[dict], limit: int = 3) -> list:
    """The founder's next steps: the evidence the score engine says would add most next, leaving out
    anything already waiting for a reviewer."""
    waiting = {e["signal_code"] for e in evidence if e["status"] in WAITING}
    return next_best_actions(venture_score(evidence), RUBRIC_V3, limit, leave_out=waiting)


async def record_venture_score(db: Database, venture_id: str, cause: str | None, sleep=None) -> bool:
    """Recomputes a venture's score from its evidence and records it through record_score().

    `db` is staff signed in, or the server's own service role after a founder's statement.
    record_score() is safe to repeat: the same total only refreshes the current row and the
    month's record, and writes no second history row. So a failed attempt is tried again, three
    times in all, and a score that still fails stays on the staff list of scores to update
    (ventures_with_stale_scores) until someone recomputes it.
    """
    async def step():
        rows = await db.table("evidence").eq("venture_id", venture_id).select(EVIDENCE_COLUMNS)
        if not rows.ok:
            return False, rows.error.code or "read_failed"
        score = venture_score(rows.data or [])
        recorded = await db.rpc("record_score", {
            "p_venture": venture_id, "p_total": score.total, "p_league": score.league,
            "p_categories": [c.as_record() for c in score.categories], "p_rubric": score.rubric_version,
            "p_cause": cause, "p_tiers": score.tier_mix(),
        })
        if not recorded.ok:
            return False, recorded.error.code or "record_failed"
        return True, score.total

    kwargs = {"sleep": sleep} if sleep else {}
    result = await with_retry(step, **kwargs)
    if not result.ok:
        log_error("score.record_failed", {"venture": venture_id, "attempts": result.attempts, "code": result.error})
        return False
    if result.attempts > 1:
        log_warn("score.recorded_after_retry", {"venture": venture_id, "attempts": result.attempts})
    return True
