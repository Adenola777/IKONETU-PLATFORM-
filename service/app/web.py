"""Rendering pages, one-time messages and redirects."""

from __future__ import annotations

import base64
import json
import pathlib
import re
from dataclasses import dataclass
from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import activity, discovery, forms, investor, jsfmt, product, staff
from .captions import cues_from_transcript
from .config import settings
from .icons import icon, logo, mark
from .venture_profile import list_text, profile_areas

HERE = pathlib.Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(HERE / "templates"))


def meter_sentence(areas: list[dict]) -> str:
    """The readiness check's sentence as it follows "Readiness check:"."""
    text = product.readiness_text(areas)
    if text.startswith("S"):
        return "s" + text[1:]
    return "no" + text[2:] if text.startswith("No") else text


def lower_first(text: str) -> str:
    return text[:1].lower() + text[1:]


def bare_url(address: str) -> str:
    """A web address without its http:// or https://, as the profile shows it."""
    return re.sub(r"^https?://", "", address)


templates.env.globals.update(
    icon=icon, logo=logo, mark=mark, settings=settings, meter_sentence=meter_sentence, lower_first=lower_first,
    STATUS=product.STATUS, LEVEL=product.LEVEL, AREAS=product.AREAS, AREA_WHY=product.AREA_WHY,
    SECTORS=product.SECTORS, STAGES=product.STAGES, COUNTRIES=product.COUNTRIES,
    area_cells=product.area_cells, area_label=product.area_label, date_text=product.date_text,
    day_month=product.day_month, initials=product.initials,
    activity_text=product.activity_text, clock_text=product.clock_text, is_recent=product.is_recent,
    stage_label=product.stage_label, country_name=product.country_name, level_of=product.level_of,
    momentum=product.momentum, evidence_added_text=product.evidence_added_text, bare_url=bare_url,
    ago_text=activity.ago_text,
    cues=cues_from_transcript, PITCH_TYPES=forms.PITCH_TYPES, EVIDENCE_FILE_TYPES=forms.EVIDENCE_FILE_TYPES,
    OPTIONAL_CONSENTS=forms.OPTIONAL_CONSENTS, profile_areas=profile_areas, list_text=list_text,
    INVESTOR_TYPE_NAME=product.INVESTOR_TYPE_NAME, CHEQUE_SIZES=product.CHEQUE_SIZES, BASED_IN=investor.BASED_IN,
    INVESTOR_TYPE_OPTIONS=investor.INVESTOR_TYPE_OPTIONS, FILTER_GROUPS=discovery.FILTER_GROUPS,
    ACTIVITY_OPTIONS=discovery.ACTIVITY_OPTIONS, ROLE_NAME=staff.ROLE_NAME, ACCOUNT_STATUS_NAME=staff.ACCOUNT_STATUS_NAME,
    ACTION_GROUPS=staff.ACTION_GROUPS, action_text=staff.action_text, REVIEW_LANES=forms.REVIEW_LANES,
    signal_label=forms.signal_label, when_text=jsfmt.when_text, month_long=jsfmt.month_long,
    based_in_name=lambda code: next((c["name"] for c in investor.BASED_IN if c["code"] == code), code),
)
templates.env.trim_blocks = True
templates.env.lstrip_blocks = True

FLASH_COOKIE = "ik_flash"
SITE_NAME = "IkonetU"
HOME_TITLE = "IkonetU | Connecting student founders to investors"
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
    ctx = {
        "request": request, "meta": meta or Meta(), "flash": flash, "site_url": settings.site_url,
        "states": form_states(flash), **(context or {}),
    }
    response = templates.TemplateResponse(request, template, ctx, status_code=status_code)
    response.headers["Cache-Control"] = "private, no-cache, no-store, max-age=0, must-revalidate"
    if flash:
        response.delete_cookie(FLASH_COOKIE, path="/")
    return response


def form_states(flash: dict[str, str]) -> dict[str, dict]:
    """The reply each form on a page shows. A form that saved names itself in the one-time message."""
    if not flash.get("form") or not flash.get("message"):
        return {}
    return {flash["form"]: {"status": flash.get("status", "sent"), "message": flash["message"]}}


def sent(location: str, form: str, message: str) -> RedirectResponse:
    """Back to the page after a form saved, with its confirmation shown once."""
    return redirect(location, {"form": form, "status": "sent", "message": message})


def failed(form: str, message: str, errors: dict | None = None, values: dict | None = None) -> dict[str, dict]:
    """The page's form states after a form was refused, to render the page again with it."""
    return {form: {"status": "error", "message": message, "errors": errors or {}, "values": values or {}}}


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


templates.env.globals.update(one=one, many=many)
templates.env.filters.update(stage_label_of=product.stage_label, country_name_of=product.country_name)
