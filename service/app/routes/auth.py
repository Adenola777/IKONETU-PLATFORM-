"""Signing in and out: /signin, /signin/code, /auth/callback and /signout."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ..config import settings
from ..log import log_error, log_warn
from ..session import current_user, forget, remember
from ..signin import (
    CODE_LIFETIME_SECONDS,
    PENDING_COOKIE,
    VERIFIER_COOKIE,
    Pending,
    now_ms,
    parse_code,
    parse_email_sign_in,
    parse_phone_sign_in,
    read_pending,
)
from ..supabase import ApiError, pkce_challenge, pkce_pair
from ..waitlist import COUNTRIES
from ..web import Meta, form_data, one, redirect, render

router = APIRouter()

NOT_OPEN = "Sign-up is not open yet. Please try again soon."
START_AGAIN = "Your code has expired. Please ask for a new one."


def _set_pending(response, pending: Pending) -> None:
    response.set_cookie(
        PENDING_COOKIE, pending.encode(), max_age=CODE_LIFETIME_SECONDS * 2, path="/signin",
        httponly=True, samesite="lax", secure=settings.secure_cookies,
    )


def _set_verifier(response, verifier: str) -> None:
    response.set_cookie(
        # Path / rather than /auth, so the resend at /signin/code/resend can read it and keep it.
        VERIFIER_COOKIE, verifier, max_age=CODE_LIFETIME_SECONDS * 2, path="/",
        httponly=True, samesite="lax", secure=settings.secure_cookies,
    )


def _logged(event: str, error: ApiError) -> None:
    (log_warn if error.status and error.status < 500 else log_error)(event, {"status": error.status, "code": error.code})


def _signin_page(request: Request, values: dict | None = None, errors: dict | None = None, message: str | None = None,
                 method: str | None = None):
    phone_enabled = settings.phone_sign_in
    return render(request, "signin/signin.html", {
        "phone_enabled": phone_enabled,
        "method": method or ("phone" if phone_enabled else "email"),
        "values": values or {},
        "errors": errors or {},
        "message": message,
        "link_error": request.query_params.get("error") == "link",
        "countries": COUNTRIES,
    }, Meta(title="Sign in", noindex=True))


@router.get("/signin")
async def signin_page(request: Request):
    if await current_user(request, request.app.state.supabase):
        return RedirectResponse("/dashboard", status_code=307)
    method = request.query_params.get("method")
    return _signin_page(request, method=method if settings.phone_sign_in and method in ("phone", "email") else None)


@router.post("/signin")
async def send_code(request: Request):
    """Sends a six-digit sign-in code (PRD A-1, A-2).

    Supabase creates the account the first time an address is used, so sign-up
    and sign-in are one step. The reply is the same whether or not the address
    already has an account.
    """
    form = await form_data(request)
    use_phone = one(form, "method") == "phone" and settings.phone_sign_in
    method = "phone" if use_phone else "email"
    values = {k: one(form, k) for k in (("country", "phone") if use_phone else ("email",))}
    adult = one(form, "confirmedAdult") == "on"
    if use_phone:
        address, errors = parse_phone_sign_in(one(form, "country"), one(form, "phone"), adult)
    else:
        address, errors = parse_email_sign_in(one(form, "email"), adult)
    if errors:
        return _signin_page(request, values, dict(errors), "Please check the form.", method)

    supabase = request.app.state.supabase
    if supabase is None:
        return _signin_page(request, values, {}, NOT_OPEN, method)

    # The confirmation is kept on the new account, so onboarding does not ask again.
    data = {"confirmed_adult": True}
    verifier = None
    if use_phone:
        pending = Pending(kind="phone", phone=address, channel="whatsapp", sent_at=now_ms())
        result = await supabase.send_phone_code(address, "whatsapp", data)
    else:
        pending = Pending(kind="email", email=address, sent_at=now_ms())
        # Supabase's default email carries a link, not the code, until the template can
        # be edited. The link returns to /auth/callback, which signs the person in.
        verifier, challenge = pkce_pair()
        result = await supabase.send_email_code(address, data, f"{settings.site_url}/auth/callback", challenge)
    if not result.ok:
        _logged("auth.code_request_failed", result.error)
        message = ("Too many codes were requested. Please wait a few minutes and try again."
                   if result.error.status == 429 else "We could not send your code. Please try again.")
        return _signin_page(request, values, {}, message, method)

    response = redirect("/signin/code")
    _set_pending(response, pending)
    if verifier:
        _set_verifier(response, verifier)
    return response


def _code_page(request: Request, pending: Pending, error: str | None = None, message: str | None = None,
               resend_error: str | None = None):
    return render(request, "signin/code.html", {
        "pending": pending,
        "describe": pending.describe(),
        "seconds_left": max(0, round((pending.expires_at - now_ms()) / 1000)),
        "expires_at": pending.expires_at,
        "error": error,
        "message": message,
        "resend_error": resend_error,
    }, Meta(title="Enter your code", noindex=True))


@router.get("/signin/code")
async def code_page(request: Request):
    pending = read_pending(request.cookies.get(PENDING_COOKIE))
    if pending is None:
        return RedirectResponse("/signin", status_code=307)
    return _code_page(request, pending)


def _expired(request: Request):
    """A code page whose sign-in has run out shows the start-again message and sends nothing."""
    return _code_page(request, Pending(kind="email", email="", sent_at=0), message=START_AGAIN)


@router.post("/signin/code")
async def verify_code(request: Request):
    """Checks the six-digit code. A right code signs the person in and opens the session."""
    pending = read_pending(request.cookies.get(PENDING_COOKIE))
    if pending is None:
        return _expired(request)
    form = await form_data(request)
    code, errors = parse_code(one(form, "code"))
    if errors:
        return _code_page(request, pending, error=errors.get("code"), message="Please check the code.")
    supabase = request.app.state.supabase
    if supabase is None:
        return _code_page(request, pending, message=NOT_OPEN)
    address = pending.email if pending.kind == "email" else pending.phone
    session, error = await supabase.verify_code(pending.kind, address, code)
    if session is None:
        _logged("auth.code_check_failed", error)
        if error.status == 429:
            return _code_page(request, pending, message="Too many attempts. Please wait a few minutes and try again.")
        return _code_page(request, pending, error="Check the code and try again, or ask for a new one.",
                          message="That code is wrong or has expired.")
    remember(request, session)
    response = redirect("/dashboard")
    response.delete_cookie(PENDING_COOKIE, path="/signin")
    return response


@router.post("/signin/code/resend")
async def resend_code(request: Request):
    """Sends a new code. For a phone, the person can switch from WhatsApp to SMS here."""
    pending = read_pending(request.cookies.get(PENDING_COOKIE))
    if pending is None:
        return _expired(request)
    supabase = request.app.state.supabase
    if supabase is None:
        return _code_page(request, pending, resend_error=NOT_OPEN)
    form = await form_data(request)
    new_verifier = None
    if pending.kind == "phone":
        channel = "sms" if one(form, "channel") == "sms" else "whatsapp"
        result = await supabase.send_phone_code(pending.phone, channel, None)
        pending.channel = channel
    else:
        # The verifier already in this browser is kept, so the link in the first email still works.
        verifier = request.cookies.get(VERIFIER_COOKIE)
        if not verifier:
            verifier = new_verifier = pkce_pair()[0]
        result = await supabase.send_email_code(
            pending.email, None, f"{settings.site_url}/auth/callback", pkce_challenge(verifier),
        )
    if not result.ok:
        _logged("auth.code_resend_failed", result.error)
        message = ("Too many codes were requested. Please wait a few minutes and try again."
                   if result.error.status == 429 else "We could not send a new code. Please try again.")
        return _code_page(request, pending, resend_error=message)
    pending.sent_at = now_ms()
    response = redirect("/signin/code", flash={"resent": "We sent a new code."})
    _set_pending(response, pending)
    if new_verifier:
        _set_verifier(response, new_verifier)
    return response


@router.get("/auth/callback")
async def callback(request: Request):
    """The sign-in email links here. The one-time code becomes a session."""
    code = request.query_params.get("code")
    supabase = request.app.state.supabase
    verifier = request.cookies.get(VERIFIER_COOKIE)
    if code and supabase is not None and verifier:
        session, error = await supabase.exchange_code(code, verifier)
        if session is not None:
            remember(request, session)
            response = RedirectResponse("/dashboard", status_code=307)
            response.delete_cookie(VERIFIER_COOKIE, path="/")
            return response
        log_warn("auth.callback_failed", {"status": error.status, "code": error.code})
    elif code:
        log_warn("auth.callback_failed", {"status": None, "code": "no_verifier" if supabase else "not_configured"})
    return RedirectResponse("/signin?error=link", status_code=307)


@router.post("/signout")
async def sign_out(request: Request):
    found = await current_user(request, request.app.state.supabase)
    if found:
        await request.app.state.supabase.sign_out(found[1])
    forget(request)
    return redirect("/")
