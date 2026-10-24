"""The signed-in person, read from the session cookies and confirmed with Supabase.

The Next.js app kept the Supabase session in cookies that the browser's
JavaScript could read, because supabase-js in the browser needed them. Here
the server makes every Supabase call, so the two tokens sit in HTTP-only
cookies that page scripts cannot read. The pitch upload, the one call the
browser makes to Supabase itself, asks the server for the access token just
before it starts (routes/founder.py).
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Literal

from fastapi import Request

from .supabase import Database, Session, Storage, Supabase

ACCESS_COOKIE = "ik_access"
REFRESH_COOKIE = "ik_refresh"
# @supabase/ssr kept its session cookies for 400 days, the longest a browser allows.
SESSION_MAX_AGE = 400 * 24 * 60 * 60
# A token this close to its expiry is refreshed before it is used.
REFRESH_MARGIN_SECONDS = 60

Role = Literal["founder", "investor", "mentor", "reviewer", "admin"]
Status = Literal["active", "pending", "suspended"]


@dataclass
class Profile:
    role: Role
    status: Status
    full_name: str


@dataclass
class Viewer:
    user: dict
    access_token: str
    db: Database
    storage: Storage
    profile: Profile | None

    @property
    def id(self) -> str:
        return self.user["id"]

    @property
    def email(self) -> str | None:
        return self.user.get("email")


class RedirectTo(Exception):
    """Ends the request with a redirect, as Next.js's redirect() did."""

    def __init__(self, location: str):
        super().__init__(location)
        self.location = location


def token_expiry(access_token: str) -> int | None:
    """The `exp` claim of a JWT, read without checking the signature, only to time a refresh."""
    try:
        payload = access_token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        return int(json.loads(base64.urlsafe_b64decode(payload))["exp"])
    except (IndexError, KeyError, ValueError, TypeError):
        return None


def remember(request: Request, session: Session) -> None:
    """Asks the response to store a new or refreshed session (see main.session_cookies)."""
    request.state.set_session = session


def forget(request: Request) -> None:
    request.state.clear_session = True


async def current_user(request: Request, supabase: Supabase | None) -> tuple[dict, str] | None:
    """The confirmed Supabase user and a valid access token, refreshing the session when it has expired."""
    cached = getattr(request.state, "user", None)
    if cached is not None:
        return cached or None
    request.state.user = False
    if supabase is None:
        return None
    access = request.cookies.get(ACCESS_COOKIE)
    refresh = request.cookies.get(REFRESH_COOKIE)
    if not access and not refresh:
        return None

    async def renew() -> str | None:
        if not refresh:
            return None
        session, _ = await supabase.refresh(refresh)
        if session is None:
            forget(request)
            return None
        remember(request, session)
        return session.access_token

    expiry = token_expiry(access) if access else None
    if not access or (expiry is not None and expiry - REFRESH_MARGIN_SECONDS <= time.time()):
        access = await renew()
        if not access:
            return None
    user, error = await supabase.get_user(access)
    if user is None and error is not None and error.status in (401, 403):
        access = await renew()
        if not access:
            return None
        user, error = await supabase.get_user(access)
    if user is None:
        if error is not None and error.status in (401, 403):
            forget(request)
        return None
    request.state.user = (user, access)
    return user, access


async def viewer(request: Request) -> Viewer | None:
    """The signed-in person and their profile, read as that person, or None."""
    cached = getattr(request.state, "viewer", None)
    if cached is not None:
        return cached or None
    supabase: Supabase | None = request.app.state.supabase
    found = await current_user(request, supabase)
    if found is None:
        request.state.viewer = False
        return None
    user, access = found
    db = supabase.as_user(access)
    row = await db.table("profiles").eq("user_id", user["id"]).maybe_single("role, status, full_name")
    profile = Profile(**row.data) if row.ok and row.data else None
    v = Viewer(user=user, access_token=access, db=db, storage=supabase.storage_as(access), profile=profile)
    request.state.viewer = v
    return v


def home_for(profile: Profile | None) -> str:
    """Where a person belongs after signing in."""
    if profile is None:
        return "/onboarding"
    if profile.role == "investor":
        return "/investor" if profile.status == "active" else "/investor/pending"
    # Only investors wait for approval, so any other account that is not active is suspended.
    if profile.status != "active":
        return "/suspended"
    if profile.role in ("reviewer", "admin"):
        return "/admin"
    if profile.role == "founder":
        return "/dashboard"
    # No pages exist for mentors yet, so they go to the website rather than round a loop.
    return "/"


async def require_viewer(request: Request) -> Viewer:
    """Sends anyone who is not signed in to the sign-in page."""
    v = await viewer(request)
    if v is None:
        raise RedirectTo("/signin")
    return v


VENTURE_COLUMNS = "id, name, sector, stage, country, description, website, ask, published_at, hidden_at, hidden_reason"


async def require_founder(request: Request) -> tuple[Viewer, dict]:
    """For founder pages. Anyone else, and a suspended founder, goes to their own home."""
    v = await require_viewer(request)
    if v.profile is None or v.profile.role != "founder" or v.profile.status != "active":
        raise RedirectTo(home_for(v.profile))
    venture = await (
        v.db.table("ventures").eq("founder_id", v.id).order("created_at").limit(1).maybe_single(VENTURE_COLUMNS)
    )
    if not venture.data:
        raise RedirectTo("/onboarding/founder")
    return v, venture.data


async def require_investor(request: Request) -> Viewer:
    """For investor pages. A pending or declined investor goes to the waiting page."""
    v = await require_viewer(request)
    if v.profile is None or v.profile.role != "investor":
        raise RedirectTo(home_for(v.profile))
    if v.profile.status != "active":
        raise RedirectTo("/investor/pending")
    return v


async def require_staff(request: Request, admin: bool = False) -> Viewer:
    """For staff pages. `admin` limits the page to admins. Someone signed out goes to the admin sign-in."""
    v = await viewer(request)
    if v is None:
        raise RedirectTo("/admin/signin")
    p = v.profile
    ok = p is not None and p.status == "active" and (p.role == "admin" or (not admin and p.role == "reviewer"))
    if not ok:
        raise RedirectTo(home_for(p))
    return v
