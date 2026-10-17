"""Logging for the server.

Each event is one line of JSON on standard output, so the host's log search can
filter on its fields: the time, the level, the event name and a few codes.
Fields carry ids and error codes only, never a name, an email address or
anything a person typed.

An error is also sent to Sentry. Sentry starts only when SENTRY_DSN is set
(see start_sentry), and until then sending to it does nothing. Sentry must be
named in the privacy policy before SENTRY_DSN is set.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any

from .config import Settings

Fields = dict[str, str | int | float | bool | None]

_sentry: Any = None


def _line(level: str, event: str, fields: Fields) -> str:
    now = datetime.now(timezone.utc)
    stamp = now.strftime("%Y-%m-%dT%H:%M:%S.") + f"{now.microsecond // 1000:03d}Z"
    return json.dumps({"time": stamp, "level": level, "event": event, **fields}, separators=(",", ":"))


def log_info(event: str, fields: Fields | None = None) -> None:
    print(_line("info", event, fields or {}), file=sys.stdout, flush=True)


def log_warn(event: str, fields: Fields | None = None) -> None:
    print(_line("warn", event, fields or {}), file=sys.stderr, flush=True)


def log_error(event: str, fields: Fields | None = None, error: BaseException | None = None) -> None:
    print(_line("error", event, fields or {}), file=sys.stderr, flush=True)
    if _sentry is None:
        return
    with _sentry.new_scope() as scope:
        scope.set_tag("event", event)
        scope.set_context("fields", dict(fields or {}))
        if error is not None:
            _sentry.capture_exception(error)
        else:
            _sentry.capture_message(event, level="error")


def scrub(event: dict, _hint: dict | None = None) -> dict:
    """Keeps only what explains the error.

    A check on 15 October 2026 against a stand-in for Sentry found that the
    event still carried the whole request: the sign-in cookies with the access
    and refresh tokens, every header and the text of the form. So the request
    is cut down to its method and its path, the user is dropped, and no
    breadcrumbs are kept.
    """
    request = event.get("request")
    if request:
        event["request"] = {"method": request.get("method"), "url": (request.get("url") or "").split("?")[0]}
    event.pop("user", None)
    event.pop("breadcrumbs", None)
    return event


def start_sentry(s: Settings) -> bool:
    """Starts Sentry on the server only, and only when SENTRY_DSN is set."""
    global _sentry
    if not s.sentry_dsn:
        return False
    import sentry_sdk

    sentry_sdk.init(
        dsn=s.sentry_dsn,
        environment=s.sentry_environment,
        send_default_pii=False,
        traces_sample_rate=0,
        max_breadcrumbs=0,
        before_send=scrub,
    )
    _sentry = sentry_sdk
    return True
