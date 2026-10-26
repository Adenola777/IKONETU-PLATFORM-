"""Introductions: the founder's list and answers, and the conversation an accepted request opens.

Ported from apps/web/app/dashboard/introductions, apps/web/app/introductions and their actions.
Only the founder and the investor of an introduction can read it. Anyone else gets 404, as for a
conversation that does not exist.
"""

from __future__ import annotations

import asyncio
import re
import uuid
from urllib.parse import quote

from fastapi import APIRouter, Request
from starlette.exceptions import HTTPException

from ..forms import parse_message
from ..guards import is_repeat, request_key
from ..log import log_error
from ..product import INVESTOR_TYPE_NAME, date_text
from ..session import require_founder, require_viewer
from ..web import Meta, failed, form_data, one, redirect, render

router = APIRouter()

ID = re.compile(r"[0-9a-f-]{36}")


def _meta(title: str) -> Meta:
    return Meta(title=title, noindex=True)


FOUNDER_TABS = ("requests", "chats", "closed")


async def _latest(v, intro_id: str) -> dict:
    """The newest message of one conversation and how many it holds. Row level security lets only its two people read them."""
    newest, total = await asyncio.gather(
        v.db.table("introduction_messages").eq("introduction_id", intro_id).order("created_at", ascending=False).limit(1)
        .select("sender_id, body, created_at"),
        v.db.table("introduction_messages").eq("introduction_id", intro_id).select("id", count=True, head=True),
    )
    rows = newest.data or []
    return {"latest": rows[0] if rows else None, "count": total.count or 0}


@router.get("/dashboard/introductions")
async def founder_introductions(request: Request):
    v, _ = await require_founder(request)
    result = await v.db.table("introductions").eq("founder_id", v.id).order("created_at", ascending=False).limit(200) \
        .select("id, note, status, investor_name, investor_type, investor_firm, created_at, decided_at")
    rows = result.data or []
    pending = [r for r in rows if r["status"] == "pending"]
    opened = sorted((r for r in rows if r["status"] == "accepted"), key=lambda r: r.get("decided_at") or "", reverse=True)
    closed = [r for r in rows if r["status"] in ("declined", "withdrawn")]
    for r, extra in zip(opened, await asyncio.gather(*(_latest(v, r["id"]) for r in opened))):
        r.update(extra)
    tab = request.query_params.get("tab", "")
    if tab not in FOUNDER_TABS:
        # A request waiting for an answer comes first. With none, the conversations do.
        tab = "requests" if pending or not opened else "chats"
    return render(request, "introductions/founder.html", {
        "pending": pending, "open": opened, "closed": closed, "tab": tab, "me": v.id,
    }, _meta("Introductions"))


@router.post("/dashboard/introductions/answer")
async def answer_introduction(request: Request):
    """The founder accepts or declines. An accepted request opens the conversation."""
    values = await form_data(request)
    v, _ = await require_founder(request)
    intro = one(values, "id")
    answer = "accepted" if one(values, "answer") == "accepted" else "declined"
    if not ID.fullmatch(intro):
        return redirect("/dashboard/introductions")
    result = await v.db.table("introductions").eq("id", intro).update({"status": answer})
    if not result.ok:
        log_error("introduction.answer_failed", {"introduction": intro, "code": result.error.code})
        return redirect("/dashboard/introductions")
    return redirect(f"/introductions/{intro}" if answer == "accepted" else "/dashboard/introductions")


def report_link(intro_id: str) -> str:
    """A report goes by email to the address the trust and safety page gives, until IkonetU has its own sender.

    The query is written as URLSearchParams writes it, with spaces as %20 rather than +.
    """
    def enc(text: str) -> str:
        return quote(text, safe="*-._")
    subject = f"Report about conversation {intro_id}"
    body = f"Conversation reference: {intro_id}\n\nWhat happened:\n"
    return f"mailto:info@ikonetu.com?subject={enc(subject)}&body={enc(body)}"


def thread_items(intro: dict, messages: list[dict], me: str) -> list[dict]:
    """The conversation in the order it happened: the request's note, the acceptance, then the messages.

    A day marker goes before the first item of each day, with the day read in UTC as date_text reads it.
    """
    items = [{"kind": "note", "at": intro["created_at"], "mine": intro["investor_id"] == me, "body": intro["note"]}]
    if intro["status"] == "accepted" and intro.get("decided_at"):
        items.append({"kind": "accepted", "at": intro["decided_at"], "mine": intro["founder_id"] == me})
    items += [{"kind": "msg", "at": m["created_at"], "mine": m["sender_id"] == me, "body": m["body"]} for m in messages]
    out, last = [], None
    for item in items:
        day = date_text(item["at"])
        if day != last:
            out.append({"kind": "day", "body": day})
            last = day
        out.append(item)
    return out


async def _conversation(request: Request, intro_id: str, states: dict | None = None):
    if not ID.fullmatch(intro_id):
        raise HTTPException(404)
    v = await require_viewer(request)
    found = await v.db.table("introductions").eq("id", intro_id).maybe_single(
        "id, venture_id, founder_id, investor_id, note, status, investor_name, investor_type, investor_firm, venture_name, "
        "founder_name, created_at, decided_at"
    )
    i = found.data
    if not i or v.id not in (i["founder_id"], i["investor_id"]):
        raise HTTPException(404)
    i_am_founder = i["founder_id"] == v.id
    if not i_am_founder and (v.profile is None or v.profile.status != "active"):
        raise HTTPException(404)
    mine = "founder_id" if i_am_founder else "investor_id"
    messages, threads = await asyncio.gather(
        v.db.table("introduction_messages").eq("introduction_id", intro_id).order("created_at").limit(500)
        .select("id, sender_id, body, created_at"),
        # The person's other open conversations, listed beside this one on a wide screen.
        v.db.table("introductions").eq(mine, v.id).eq("status", "accepted").order("decided_at", ascending=False).limit(100)
        .select("id, investor_name, investor_type, investor_firm, founder_name, venture_name, decided_at"),
    )
    firm = f", {i['investor_firm']}" if i.get("investor_firm") else ""
    investor_line = f"{i['investor_name']}, {INVESTOR_TYPE_NAME.get(i['investor_type'], i['investor_type'])}{firm}"

    def who(sender: str) -> str:
        if sender == v.id:
            return "You"
        return i["founder_name"] if sender == i["founder_id"] else i["investor_name"]

    context = {
        "i": i, "i_am_founder": i_am_founder, "messages": messages.data or [], "me": v.id, "who": who,
        "investor_line": investor_line, "report": report_link(i["id"]), "new_key": str(uuid.uuid4()),
        "thread": thread_items(i, messages.data or [], v.id), "threads": threads.data or [],
    }
    if states:
        context["states"] = states
    return render(request, "introductions/conversation.html", context, _meta("Conversation"))


@router.get("/introductions/{intro_id}")
async def conversation(request: Request, intro_id: str):
    return await _conversation(request, intro_id)


@router.post("/introductions/{intro_id}/message")
async def send_message(request: Request, intro_id: str):
    """A message in an accepted introduction, from either of the two people involved."""
    raw = await form_data(request)
    values = {k: one(raw, k) for k in raw if k != "requestKey"}
    v = await require_viewer(request)
    intro = values.get("introduction", "")
    if not ID.fullmatch(intro):
        return await _conversation(request, intro_id, failed("message", "This conversation could not be found."))
    parsed = parse_message(values.get("body", ""))
    if not parsed.ok:
        return await _conversation(request, intro_id, failed("message", "Please check your message.", parsed.errors, values))
    result = await v.db.table("introduction_messages").insert({
        "introduction_id": intro, "sender_id": v.id, "body": parsed.data["body"], "request_key": request_key(one(raw, "requestKey")),
    })
    if not result.ok and not is_repeat(result.error):
        log_error("message.send_failed", {"introduction": intro, "code": result.error.code})
        return await _conversation(request, intro_id,
                                   failed("message", "We could not send your message. Please try again.", values=values))
    return redirect(f"/introductions/{intro}")
