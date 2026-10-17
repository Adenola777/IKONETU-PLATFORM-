"""Settings read from the environment.

The variable names are the ones the Next.js app used, NEXT_PUBLIC_ prefix
included, so the values already entered on Render keep working. In this app
nothing is built into browser code: the server reads every value when it
starts, and a change needs a restart rather than a new build.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Settings:
    supabase_url: str | None
    supabase_key: str | None
    service_role_key: str | None
    site_url: str
    phone_sign_in: bool
    trusted_proxy_hops: str | None
    client_ip_header: str | None
    sentry_dsn: str | None
    sentry_environment: str
    production: bool

    @property
    def supabase_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_key)

    @property
    def supabase_origin(self) -> str:
        """The Supabase address without a path, for the Content-Security-Policy."""
        if not self.supabase_url:
            return ""
        parts = urlsplit(self.supabase_url)
        return f"{parts.scheme}://{parts.netloc}" if parts.scheme and parts.netloc else ""

    @property
    def secure_cookies(self) -> bool:
        return self.site_url.startswith("https://")


def _blank_to_none(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def load_settings(env: dict[str, str] | None = None) -> Settings:
    e = os.environ if env is None else env
    url = _blank_to_none(e.get("NEXT_PUBLIC_SUPABASE_URL"))
    return Settings(
        supabase_url=url.rstrip("/") if url else None,
        supabase_key=_blank_to_none(e.get("NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY")),
        service_role_key=_blank_to_none(e.get("SUPABASE_SERVICE_ROLE_KEY")),
        site_url=(e.get("NEXT_PUBLIC_SITE_URL") or "http://localhost:3000").rstrip("/"),
        phone_sign_in=e.get("NEXT_PUBLIC_PHONE_SIGN_IN") == "on",
        trusted_proxy_hops=e.get("TRUSTED_PROXY_HOPS"),
        client_ip_header=_blank_to_none(e.get("CLIENT_IP_HEADER")),
        sentry_dsn=_blank_to_none(e.get("SENTRY_DSN")),
        sentry_environment=e.get("SENTRY_ENVIRONMENT") or "production",
        production=e.get("APP_ENV", "production") == "production",
    )


settings = load_settings()
