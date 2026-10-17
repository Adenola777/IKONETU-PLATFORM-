"""Everything a founder profile shows. Ported from apps/web/lib/venture-profile.ts.

It is read as the person looking, so the database decides what they may see. A venture
that is not visible to them reads as None, which looks the same as one that does not exist.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from .product import AREAS, RANK, is_shown_status
from .supabase import Database, Storage


async def load_venture_profile(db: Database, storage: Storage, venture_id: str) -> dict | None:
    venture = await db.table("ventures").eq("id", venture_id).maybe_single(
        "id, founder_id, name, sector, stage, country, description, website, ask, published_at"
    )
    if not venture.data:
        return None
    v = venture.data
    since = (datetime.now(timezone.utc) - timedelta(days=91)).strftime("%Y-%m-%dT%H:%M:%S.") + "000Z"
    founder, pitch, evidence, updates, recent = await asyncio.gather(
        db.table("public_profiles").eq("user_id", v["founder_id"]).maybe_single("full_name, city, country, institution, bio"),
        db.table("pitches").eq("venture_id", venture_id).maybe_single("storage_path, transcript, duration_seconds, updated_at"),
        db.rpc("venture_evidence", {"p_venture": venture_id}),
        db.table("venture_updates").eq("venture_id", venture_id).order("created_at", ascending=False).limit(20).select("id, body, created_at"),
        db.table("venture_updates").eq("venture_id", venture_id).gte("created_at", since).limit(500).select("created_at"),
    )
    signed = await storage.signed_url("pitches", pitch.data["storage_path"], 3600) if pitch.data else None
    ev = [
        {
            "id": str(e["id"]), "category": str(e["category"]), "label": str(e["label"]), "summary": e.get("summary"),
            "status": e["shown_status"], "publicNote": e.get("public_note"), "reviewedAt": e.get("reviewed_at"),
            "createdAt": str(e["created_at"]),
        }
        for e in (evidence.data or [])
        if is_shown_status(e.get("shown_status"))
    ]
    upd = updates.data or []
    dates = [d for d in [v.get("published_at"), (pitch.data or {}).get("updated_at"), upd[0]["created_at"] if upd else None,
                         *(e["createdAt"] for e in ev)] if d]
    venture_out = {k: val for k, val in v.items() if k != "founder_id"}
    return {
        "venture": venture_out,
        "founder": founder.data,
        "pitch": {"url": signed, "transcript": pitch.data["transcript"], "duration": float(pitch.data["duration_seconds"])}
        if pitch.data and signed else None,
        "evidence": ev,
        "updates": upd,
        "recentUpdates": [r["created_at"] for r in (recent.data or [])],
        "lastActivity": sorted(dates)[-1] if dates else None,
    }


def profile_areas(evidence: list[dict]) -> list[dict]:
    """Each area that holds evidence, with its best status and count, in rubric order."""
    out = []
    for a in AREAS:
        items = [e for e in evidence if e["category"] == a["code"]]
        if not items:
            continue
        best = items[0]
        for e in items[1:]:
            if RANK[e["status"]] > RANK[best["status"]]:
                best = e
        out.append({"category": a["code"], "status": best["status"], "count": len(items), "items": items, "label": a["label"]})
    return out


def list_text(items: list[str]) -> str:
    """ "a, b and c"."""
    if len(items) <= 1:
        return items[0] if items else ""
    return f"{', '.join(items[:-1])} and {items[-1]}"
