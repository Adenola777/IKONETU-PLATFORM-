"""Small rules shared by the routes: the caller's address, the rate limit, retries and request keys."""

from __future__ import annotations

import asyncio
import re
import time
from dataclasses import dataclass
from typing import Awaitable, Callable, Generic, Mapping, TypeVar

from .supabase import ApiError

T = TypeVar("T")


def client_address(headers: Mapping[str, str], trusted_proxy_hops: str | None, client_ip_header: str | None) -> str:
    """The caller's address, for rate limits.

    Each proxy in front of the app adds the address it received the request from
    to the end of X-Forwarded-For, so only the entries added by trusted proxies
    can be believed. The caller writes whatever it likes at the start of the
    header, and reading the first entry let a caller choose a new address for
    every request (found on 15 October 2026).

    TRUSTED_PROXY_HOPS is the number of proxies in front of the app, and the
    address is read that many entries from the end. It is 1 unless set. How many
    proxies Render puts in front of a web service is unverified; HOSTING.md
    describes the check to run after the first deployment. CLIENT_IP_HEADER,
    when set, names a single header that the edge in front of the app sets
    itself, and it is read instead.

    A request with fewer entries than the trusted hops did not pass through the
    proxies, so its address cannot be believed and it is counted as "unknown".
    """
    named = (client_ip_header or "").strip().lower()
    lower = {k.lower(): v for k, v in headers.items()}
    if named:
        return (lower.get(named) or "").strip() or "unknown"
    try:
        hops = max(1, int(trusted_proxy_hops or "1"))
    except ValueError:
        hops = 1
    entries = [s.strip() for s in (lower.get("x-forwarded-for") or "").split(",") if s.strip()]
    return entries[-hops] if len(entries) >= hops else "unknown"


class Limiter:
    """A small fixed-window limiter kept in memory.

    Each server instance keeps its own count, so this slows down casual abuse
    only. SRD SEC-W4 asks for a limit in front of the app as well, which
    docs/HOSTING.md records as not yet set up.
    """

    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, list[float]] = {}

    def allow(self, key: str, now: float | None = None) -> bool:
        moment = time.monotonic() if now is None else now
        entry = self._hits.get(key)
        if entry is None or entry[1] <= moment:
            if len(self._hits) > 10_000:
                self._hits.clear()
            self._hits[key] = [1, moment + self.window]
            return True
        entry[0] += 1
        return entry[0] <= self.limit


@dataclass
class Attempted(Generic[T]):
    ok: bool
    attempts: int
    value: T | None = None
    error: str = ""


async def with_retry(
    step: Callable[[], Awaitable[tuple[bool, T | str]]],
    attempts: int = 3,
    base_seconds: float = 0.25,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> Attempted[T]:
    """Runs a step again when it fails, waiting 250 ms, then 500 ms, then 1 s by default.

    Use it only for a step that is safe to repeat. The step answers (True, value)
    or (False, error).
    """
    last = ""
    for i in range(1, attempts + 1):
        try:
            ok, out = await step()
            if ok:
                return Attempted(ok=True, attempts=i, value=out)  # type: ignore[arg-type]
            last = str(out)
        except Exception as exc:  # noqa: BLE001 - a failed attempt is retried whatever it raised
            last = str(exc) or type(exc).__name__
        if i < attempts:
            await sleep(base_seconds * 2 ** (i - 1))
    return Attempted(ok=False, attempts=attempts, error=last)


_UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", re.IGNORECASE)


def request_key(value: str | None) -> str | None:
    """The request key a form sends with evidence, an update or a message.

    The form carries a new key each time it is shown, so the same key arriving
    twice means the same submission was sent twice, and the database keeps it
    once (migration 20261015000004). A missing or malformed key counts as none.
    """
    v = (value or "").strip()
    return v.lower() if _UUID.match(v) else None


def is_repeat(error: ApiError | None) -> bool:
    """True when a database error is the request key's unique index refusing a second copy."""
    return bool(error and error.code == "23505" and "request_key" in (error.message or ""))
