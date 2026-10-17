"""Security headers on every response, and the check that a form was sent from this site.

SRD SEC-W2 asks for the headers. The policy is the Next.js app's with one
change: scripts may only come from this site. Next.js needed inline scripts to
start React in the browser, so its policy allowed 'unsafe-inline' for scripts.
This app's pages carry no inline script.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse

from .config import Settings


def content_security_policy(s: Settings) -> str:
    # The pitch videos are uploaded from the browser to Supabase Storage and played
    # from it through signed links, so the Supabase address is allowed for both.
    supabase = s.supabase_origin
    return "; ".join([
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "font-src 'self'",
        "img-src 'self' data:",
        # blob: lets a founder watch the video they chose before it uploads.
        f"media-src 'self' blob: {supabase}".strip(),
        f"connect-src 'self' {supabase}".strip(),
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "form-action 'self'",
    ])


def security_headers(s: Settings) -> dict[str, str]:
    return {
        "Content-Security-Policy": content_security_policy(s),
        "Strict-Transport-Security": "max-age=63072000; includeSubDomains; preload",
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
    }


UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}
# The waitlist endpoint is a JSON API that other sites may call, as before.
ORIGIN_EXEMPT = ("/api/",)


def same_origin(request: Request) -> bool:
    """True unless a browser says the request came from another site.

    Next.js refused a server action whose Origin header named a different host
    from the one the request was sent to. This check does the same for every
    form. A request without an Origin header passes, as it did in Next.js; the
    session cookies are SameSite=Lax, so a browser does not attach them to a
    form another site sends.
    """
    origin = request.headers.get("origin")
    if not origin:
        return True
    if origin == "null":
        return False
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    return urlsplit(origin).netloc.lower() == host.split(",")[0].strip().lower()


class SecurityMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, settings: Settings):
        super().__init__(app)
        self.headers = security_headers(settings)

    async def dispatch(self, request: Request, call_next):
        if request.method in UNSAFE and not request.url.path.startswith(ORIGIN_EXEMPT) and not same_origin(request):
            response = PlainTextResponse("This form must be sent from the IkonetU site.", status_code=403)
        else:
            response = await call_next(request)
        for k, v in self.headers.items():
            response.headers.setdefault(k, v)
        return response
