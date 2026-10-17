"""The IkonetU web app: the website, sign-in and the signed-in pages, served by FastAPI.

Run it with `uvicorn app.main:app` from the service folder.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from .config import settings
from .log import log_error, start_sentry
from .routes import auth, founder, introductions, investor, site, staff, system
from .security import SecurityMiddleware
from .session import ACCESS_COOKIE, REFRESH_COOKIE, SESSION_MAX_AGE, RedirectTo
from .supabase import make_client
from .web import HERE, Meta, render


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_sentry(settings)
    async with httpx.AsyncClient() as http:
        app.state.http = http
        app.state.supabase = make_client(settings, http)
        yield


app = FastAPI(lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)


@app.middleware("http")
async def session_cookies(request: Request, call_next):
    """Stores a new or refreshed session, or clears it, on whatever response the route returned."""
    response = await call_next(request)
    new = getattr(request.state, "set_session", None)
    options = {"path": "/", "httponly": True, "samesite": "lax", "secure": settings.secure_cookies}
    if new is not None:
        response.set_cookie(ACCESS_COOKIE, new.access_token, max_age=SESSION_MAX_AGE, **options)
        response.set_cookie(REFRESH_COOKIE, new.refresh_token, max_age=SESSION_MAX_AGE, **options)
    elif getattr(request.state, "clear_session", False):
        response.delete_cookie(ACCESS_COOKIE, **options)
        response.delete_cookie(REFRESH_COOKIE, **options)
    return response


app.add_middleware(SecurityMiddleware, settings=settings)


@app.exception_handler(RedirectTo)
async def on_redirect(request: Request, exc: RedirectTo):
    # A form is answered with 303 so the browser follows with GET. A page answers 307, as Next.js's redirect() did.
    status = 303 if request.method != "GET" else 307
    return RedirectResponse(exc.location, status_code=status)


@app.exception_handler(StarletteHTTPException)
async def on_http_error(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return render(request, "not_found.html", {}, Meta(title="Page not found", noindex=True), status_code=404)
    return await _plain(exc)


async def _plain(exc: StarletteHTTPException):
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(str(exc.detail), status_code=exc.status_code)


@app.exception_handler(Exception)
async def on_error(request: Request, exc: Exception):
    log_error("request.failed", {"path": request.url.path, "method": request.method}, exc)
    return render(request, "error.html", {}, Meta(title="Something went wrong", noindex=True), status_code=500)


app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")
MEDIA = HERE / "public" / "media"
app.mount("/media", StaticFiles(directory=str(MEDIA)), name="media")


@app.get("/icon.svg", include_in_schema=False)
async def favicon():
    return FileResponse(HERE / "public" / "icon.svg", media_type="image/svg+xml")


app.include_router(system.router)
app.include_router(auth.router)
app.include_router(site.router)
app.include_router(founder.router)
app.include_router(investor.router)
app.include_router(introductions.router)
app.include_router(staff.router)
