"""Rendering pages, one-time messages and redirects."""

from __future__ import annotations

import base64
import json
import pathlib
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from .config import settings
from .icons import icon, logo

HERE = pathlib.Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(HERE / "templates"))
templates.env.globals.update(icon=icon, logo=logo, settings=settings)
templates.env.trim_blocks = True
templates.env.lstrip_blocks = True

FLASH_COOKIE = "ik_flash"
SITE_NAME = "IkonetU"
HOME_TITLE = "IkonetU | Connecting early-stage founders to investors"
HOME_DESCRIPTION = (
    "Upload a one-minute pitch, build a verifiable venture profile, and connect with investors looking for real progress."
)


@dataclass
class Meta:
    """What a page carries in its head, as Next.js's metadata did."""

    title: str | None = None
    description: str = HOME_DESCRIPTION
    canonical: str | None = None
    noindex: bool = False
    absolute_title: bool = False

    @property
    def full_title(self) -> str:
        if not self.title:
            return HOME_TITLE
        return self.title if self.absolute_title else f"{self.title} | {SITE_NAME}"


def render(
    request: Request,
    template: str,
    context: dict[str, Any] | None = None,
    meta: Meta | None = None,
    status_code: int = 200,
) -> HTMLResponse:
    flash = read_flash(request)
    ctx = {"request": request, "meta": meta or Meta(), "flash": flash, "site_url": settings.site_url, **(context or {})}
    response = templates.TemplateResponse(request, template, ctx, status_code=status_code)
    response.headers["Cache-Control"] = "private, no-cache, no-store, max-age=0, must-revalidate"
    if flash:
        response.delete_cookie(FLASH_COOKIE, path="/")
    return response


def redirect(location: str, flash: dict[str, str] | None = None) -> RedirectResponse:
    """A 303 redirect, which a browser follows with GET after a form is sent."""
    response = RedirectResponse(location, status_code=303)
    if flash:
        set_flash(response, flash)
    return response


def set_flash(response, flash: dict[str, str]) -> None:
    """A message for the next page only, such as "Your pitch is saved."."""
    value = base64.urlsafe_b64encode(json.dumps(flash).encode()).decode().rstrip("=")
    response.set_cookie(
        FLASH_COOKIE, value, max_age=60, path="/", httponly=True, samesite="lax", secure=settings.secure_cookies,
    )


def read_flash(request: Request) -> dict[str, str]:
    raw = request.cookies.get(FLASH_COOKIE)
    if not raw:
        return {}
    try:
        data = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))
    except ValueError:
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


async def form_data(request: Request) -> dict[str, str | list[str]]:
    """Everything the person typed or ticked. A field sent more than once becomes a list."""
    form = await request.form()
    out: dict[str, str | list[str]] = {}
    for key in form.keys():
        values = [v for v in form.getlist(key) if isinstance(v, str)]
        if not values:
            continue
        out[key] = values if len(values) > 1 else values[0]
    return out


def one(values: dict, key: str) -> str:
    v = values.get(key, "")
    return (v[0] if v else "") if isinstance(v, list) else (v or "")


def many(values: dict, key: str) -> list[str]:
    v = values.get(key)
    if isinstance(v, list):
        return v
    return [v] if v else []
