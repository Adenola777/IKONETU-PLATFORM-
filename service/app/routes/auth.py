"""Signing in and out: /signin, /signin/code, /auth/callback, /admin/signin and /signout."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

from ..config import settings
from ..guards import Limiter, client_address
from ..log import log_error, log_info, log_warn
from ..session import current_user, forget, remember, viewer
from ..signin import (
    CODE_LIFETIME_SECONDS,
    PENDING_COOKIE,
    VERIFIER_COOKIE,
    Pending,
    now_ms,
    parse_admin_sign_in,
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


# ---------------------------------------------------------------- admin sign-in
# Admins sign in with an email address and a password on a page of their own, as the owner chose on
# 24 October 2026. Founders and investors keep the email code at /signin. An admin's account and password are
# made in Supabase by the owner, so no password passes through the app except at sign-in.
ADMIN_REFUSED = "That email address and password do not match an admin account."
ADMIN_TOO_MANY = "Too many attempts. Please wait 15 minutes and try again."
ADMIN_WINDOW_SECONDS = 15 * 60
admin_by_address = Limiter(10, ADMIN_WINDOW_SECONDS)
admin_by_email = Limiter(5, ADMIN_WINDOW_SECONDS)


def _admin_signin_page(request: Request, email: str = "", errors: dict | None = None, message: str | None = None,
                       status_code: int = 200):
    return render(request, "staff/signin.html", {
        "email": email, "errors": errors or {}, "message": message,
        "signed_out": request.query_params.get("done") == "out",
    }, Meta(title="Admin sign-in", noindex=True), status_code=status_code)


@router.get("/admin/signin")
async def admin_signin_page(request: Request):
    v = await viewer(request)
    if v is not None and v.profile is not None and v.profile.role == "admin" and v.profile.status == "active":
        return RedirectResponse("/admin", status_code=307)
    return _admin_signin_page(request)


@router.post("/admin/signin")
async def admin_sign_in(request: Request):
    """Signs an admin in with a password. Any other account is signed out again at once and told only that the
    details do not match, so the page does not say which addresses have accounts."""
    form = await form_data(request)
    email, errors = parse_admin_sign_in(one(form, "email"), one(form, "password"))
    typed = one(form, "email")
    if errors:
        return _admin_signin_page(request, typed, dict(errors), "Please check the form.")
    supabase = request.app.state.supabase
    if supabase is None:
        return _admin_signin_page(request, typed, message=NOT_OPEN)
    address = client_address(request.headers, settings.trusted_proxy_hops, settings.client_ip_header)
    if not (admin_by_address.allow(address) and admin_by_email.allow(email)):
        log_warn("admin.signin_limited", {})
        return _admin_signin_page(request, typed, message=ADMIN_TOO_MANY, status_code=429)
    session, error = await supabase.sign_in_with_password(email, one(form, "password"))
    if session is None:
        if error.status == 429:
            log_warn("admin.signin_limited", {"status": 429})
            return _admin_signin_page(request, typed, message=ADMIN_TOO_MANY, status_code=429)
        if error.status and error.status < 500:
            log_info("admin.signin_refused", {"status": error.status, "code": error.code})
            return _admin_signin_page(request, typed, message=ADMIN_REFUSED)
        _logged("admin.signin_failed", error)
        return _admin_signin_page(request, typed, message="We could not sign you in. Please try again.")
    row = await supabase.as_user(session.access_token).table("profiles").eq("user_id", session.user.get("id", "")) \
        .maybe_single("role, status")
    profile = row.data if row.ok else None
    if not profile or profile.get("role") != "admin" or profile.get("status") != "active":
        await supabase.sign_out(session.access_token)
        log_warn("admin.signin_not_admin", {"profile": bool(profile)})
        return _admin_signin_page(request, typed, message=ADMIN_REFUSED)
    remember(request, session)
    log_info("admin.signed_in", {})
    return redirect("/admin")


@router.post("/signout")
async def sign_out(request: Request):
    """Signs out everywhere. An admin goes back to the admin sign-in, everyone else to the home page."""
    form = await form_data(request)
    found = await current_user(request, request.app.state.supabase)
    if found:
        await request.app.state.supabase.sign_out(found[1])
    forget(request)
    return redirect("/admin/signin?done=out" if one(form, "next") == "/admin/signin" else "/")
