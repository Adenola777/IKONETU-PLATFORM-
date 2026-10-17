"""The health check, the waitlist endpoint, robots.txt, the site map and the retired interest address."""

from __future__ import annotations

import json

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response

from ..config import settings
from ..guards import Limiter, client_address
from ..log import log_warn
from ..pages import PUBLIC_PAGES
from ..waitlist import parse_waitlist

router = APIRouter()

NO_STORE = {"cache-control": "no-store"}


@router.get("/api/health")
async def health(request: Request):
    """For an uptime monitor.

    It answers 200 when the app is running and the database answers through
    Supabase, and 503 when Supabase cannot be reached within five seconds or is
    not configured. It reads nothing: health() in migration 20261015000004
    returns true. Render's own health check stays on "/", which does not depend
    on Supabase, so a Supabase outage does not make Render restart the app.
    """
    supabase = request.app.state.supabase
    if supabase is None:
        return JSONResponse({"status": "degraded", "supabase": "not_configured"}, status_code=503, headers=NO_STORE)
    result = await supabase.as_visitor().rpc("health", timeout=5.0)
    if not result.ok or result.data is not True:
        code = result.error.code or (result.error.message or "")[:80] if result.error else None
        log_warn("health.supabase_unreachable", {"code": code})
        return JSONResponse({"status": "degraded", "supabase": "unreachable"}, status_code=503, headers=NO_STORE)
    return JSONResponse({"status": "ok", "supabase": "ok"}, headers=NO_STORE)


waitlist_limit = Limiter(5, 10 * 60)
MAX_BODY_BYTES = 4_096
DONE = {"ok": True, "message": "You are on the list. We will tell you when Season 1 opens in your country."}


@router.post("/api/v1/waitlist")
async def waitlist(request: Request):
    address = client_address(request.headers, settings.trusted_proxy_hops, settings.client_ip_header)
    if not waitlist_limit.allow(address):
        return JSONResponse({"ok": False, "message": "Too many attempts. Please try again in a few minutes."}, status_code=429)
    if "application/json" not in (request.headers.get("content-type") or ""):
        return JSONResponse({"ok": False, "message": "Send the form as JSON."}, status_code=415)
    raw = await request.body()
    text = raw.decode("utf-8", errors="replace")
    if len(text) > MAX_BODY_BYTES:
        return JSONResponse({"ok": False, "message": "The form is too large."}, status_code=413)
    try:
        body = json.loads(text)
    except ValueError:
        return JSONResponse({"ok": False, "message": "The form could not be read."}, status_code=400)

    parsed = parse_waitlist(body)
    # A filled honeypot gets the normal success reply, so bots learn nothing.
    if not parsed["ok"] and parsed["bot"]:
        return JSONResponse(DONE, status_code=201)
    if not parsed["ok"]:
        return JSONResponse({"ok": False, "message": "Please check the form.", "errors": parsed["errors"]}, status_code=422)

    supabase = request.app.state.supabase
    db = supabase.as_service() if supabase else None
    if db is None:
        return JSONResponse({"ok": False, "message": "The waitlist is not open yet. Please try again soon."}, status_code=503)
    result = await db.table("waitlist").insert(parsed["row"])
    # A contact that already joined gets the same reply, so the form never reveals who has joined.
    if result.ok or (result.error and result.error.status == 409):
        return JSONResponse(DONE, status_code=201)
    return JSONResponse({"ok": False, "message": "Something went wrong on our side. Please try again."}, status_code=502)


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots():
    """Search engines may read the public pages. The sign-in steps, the signed-in pages and the API stay out."""
    disallow = ["/api/", "/auth/", "/signin", "/onboarding", "/dashboard", "/investor/", "/introductions/", "/admin", "/suspended"]
    lines = ["User-Agent: *", "Allow: /", *[f"Disallow: {d}" for d in disallow], "", f"Sitemap: {settings.site_url}/sitemap.xml", ""]
    return "\n".join(lines)


@router.get("/sitemap.xml")
async def sitemap():
    urls = [settings.site_url if p["path"] == "/" else f"{settings.site_url}{p['path']}" for p in PUBLIC_PAGES.values()]
    body = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    body += [f"<url>\n<loc>{u}</loc>\n</url>" for u in urls]
    body.append("</urlset>")
    return Response("\n".join(body) + "\n", media_type="application/xml")


@router.get("/investor-interest")
async def investor_interest():
    """The investor interest form was retired on 15 October 2026, when investor accounts opened."""
    return RedirectResponse("/for-investors", status_code=308)
