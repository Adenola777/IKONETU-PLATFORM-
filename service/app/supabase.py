"""The calls this app makes to Supabase: Auth, the REST API (PostgREST) and Storage.

The Next.js app used supabase-js. Each request here repeats what supabase-js
2.117.2 sends, read from its own source in node_modules on 17 October 2026:
the `apikey` header always carries the publishable key, and `Authorization`
carries the signed-in person's access token, or the key itself for a visitor,
so row level security decides what each call may read and write.

Every call has a time limit. Without one, a Supabase outage left each request
waiting for as long as the runtime allows. An upload to storage gets two
minutes, because an evidence file of 10 MB on a slow link takes time to send,
and everything else gets 15 seconds.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

import httpx

from .config import Settings

QUICK_SECONDS = 15.0
UPLOAD_SECONDS = 120.0
_RESERVED = re.compile(r"[,()]")


@dataclass
class ApiError:
    """An error from Supabase, or from the network on the way to it."""

    status: int | None
    code: str | None
    message: str
    details: str | None = None

    @classmethod
    def network(cls, exc: Exception) -> "ApiError":
        return cls(status=None, code="network", message=type(exc).__name__)


@dataclass
class Result:
    data: Any = None
    error: ApiError | None = None
    count: int | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


@dataclass
class Session:
    access_token: str
    refresh_token: str
    expires_at: int | None
    user: dict


def _error_from(response: httpx.Response) -> ApiError:
    try:
        body = response.json()
    except ValueError:
        return ApiError(status=response.status_code, code=None, message=response.text[:200])
    if not isinstance(body, dict):
        return ApiError(status=response.status_code, code=None, message=str(body)[:200])
    # PostgREST answers {code, message, details, hint}; Auth answers {code, error_code, msg};
    # Storage answers {statusCode, error, message}.
    code = body.get("error_code") or body.get("code") or body.get("error")
    message = body.get("message") or body.get("msg") or body.get("error_description") or body.get("error") or ""
    return ApiError(
        status=response.status_code,
        code=str(code) if code is not None else None,
        message=str(message),
        details=body.get("details"),
    )


def _session_from(body: dict) -> Session | None:
    if not isinstance(body, dict) or not body.get("access_token"):
        return None
    return Session(
        access_token=body["access_token"],
        refresh_token=body.get("refresh_token", ""),
        expires_at=body.get("expires_at"),
        user=body.get("user") or {},
    )


def pkce_pair() -> tuple[str, str]:
    """A PKCE code verifier and its S256 challenge, made as supabase-js makes them.

    supabase-js joins 56 random 32-bit numbers written in hex, and the challenge
    is the URL-safe base64 of the verifier's SHA-256 without padding.
    """
    verifier = "".join(f"{secrets.randbits(32):08x}"[-2:] for _ in range(56))
    return verifier, pkce_challenge(verifier)


def pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


class Query:
    """Builds one PostgREST request, as postgrest-js does for the calls this app makes."""

    def __init__(self, db: "Database", table: str):
        self._db = db
        self._table = table
        self._params: list[tuple[str, str]] = []
        self._prefer: list[str] = []
        self._order: list[str] = []

    # ---------------------------------------------------------------- filters
    def _filter(self, column: str, expression: str) -> "Query":
        self._params.append((column, expression))
        return self

    def eq(self, column: str, value: Any) -> "Query":
        return self._filter(column, f"eq.{_text(value)}")

    def neq(self, column: str, value: Any) -> "Query":
        return self._filter(column, f"neq.{_text(value)}")

    def gt(self, column: str, value: Any) -> "Query":
        return self._filter(column, f"gt.{_text(value)}")

    def gte(self, column: str, value: Any) -> "Query":
        return self._filter(column, f"gte.{_text(value)}")

    def lt(self, column: str, value: Any) -> "Query":
        return self._filter(column, f"lt.{_text(value)}")

    def lte(self, column: str, value: Any) -> "Query":
        return self._filter(column, f"lte.{_text(value)}")

    def is_(self, column: str, value: None | bool) -> "Query":
        return self._filter(column, f"is.{'null' if value is None else str(value).lower()}")

    def not_is(self, column: str, value: None | bool) -> "Query":
        return self._filter(column, f"not.is.{'null' if value is None else str(value).lower()}")

    def in_(self, column: str, values: list[Any]) -> "Query":
        seen: list[str] = []
        for v in values:
            t = _text(v)
            t = f'"{t}"' if isinstance(v, str) and _RESERVED.search(v) else t
            if t not in seen:
                seen.append(t)
        return self._filter(column, f"in.({','.join(seen)})")

    def ilike(self, column: str, pattern: str) -> "Query":
        return self._filter(column, f"ilike.{pattern}")

    def or_(self, expression: str) -> "Query":
        self._params.append(("or", f"({expression})"))
        return self

    def order(self, column: str, ascending: bool = True, nulls_first: bool | None = None) -> "Query":
        part = f"{column}.{'asc' if ascending else 'desc'}"
        if nulls_first is not None:
            part += ".nullsfirst" if nulls_first else ".nullslast"
        self._order.append(part)
        return self

    def limit(self, count: int) -> "Query":
        self._params.append(("limit", str(count)))
        return self

    def range(self, start: int, end: int) -> "Query":
        self._params.append(("offset", str(start)))
        self._params.append(("limit", str(end - start + 1)))
        return self

    # ---------------------------------------------------------------- requests
    def _query(self) -> list[tuple[str, str]]:
        params = list(self._params)
        if self._order:
            params.append(("order", ",".join(self._order)))
        return params

    async def select(self, columns: str = "*", count: bool = False, head: bool = False) -> Result:
        params = [("select", _clean_columns(columns)), *self._query()]
        prefer = ["count=exact"] if count else []
        return await self._db.send("HEAD" if head else "GET", self._table, params=params, prefer=prefer)

    async def maybe_single(self, columns: str = "*") -> Result:
        """One row or None. More than one row is the same error postgrest-js gives."""
        r = await self.select(columns)
        if not r.ok:
            return r
        rows = r.data or []
        if len(rows) > 1:
            return Result(error=ApiError(406, "PGRST116", "JSON object requested, multiple (or no) rows returned"))
        return Result(data=rows[0] if rows else None)

    async def insert(self, values: dict | list[dict], returning: str | None = None) -> Result:
        params = []
        if isinstance(values, list):
            columns: list[str] = []
            for row in values:
                for k in row:
                    if k not in columns:
                        columns.append(k)
            if columns:
                params.append(("columns", ",".join(f'"{c}"' for c in columns)))
        prefer = []
        if returning is not None:
            params.append(("select", _clean_columns(returning)))
            prefer.append("return=representation")
        return await self._db.send("POST", self._table, params=params, body=values, prefer=prefer)

    async def update(self, values: dict, count: bool = False, returning: str | None = None) -> Result:
        params = self._query()
        prefer = ["count=exact"] if count else []
        if returning is not None:
            params.append(("select", _clean_columns(returning)))
            prefer.append("return=representation")
        return await self._db.send("PATCH", self._table, params=params, body=values, prefer=prefer)

    async def delete(self, count: bool = False) -> Result:
        prefer = ["count=exact"] if count else []
        return await self._db.send("DELETE", self._table, params=self._query(), prefer=prefer)


def _text(value: Any) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _clean_columns(columns: str) -> str:
    """Drops the whitespace outside quotes, as postgrest-js does."""
    out, quoted = [], False
    for c in columns:
        if c.isspace() and not quoted:
            continue
        if c == '"':
            quoted = not quoted
        out.append(c)
    return "".join(out)


class Database:
    """The REST API as one caller: a signed-in person, a visitor, or the service role."""

    def __init__(self, client: "Supabase", bearer: str | None):
        self._client = client
        self._bearer = bearer

    def table(self, name: str) -> Query:
        return Query(self, name)

    async def rpc(self, function: str, args: dict | None = None, timeout: float | None = None) -> Result:
        return await self.send("POST", f"rpc/{function}", body=args or {}, timeout=timeout)

    async def send(
        self,
        method: str,
        path: str,
        params: list[tuple[str, str]] | None = None,
        body: Any = None,
        prefer: list[str] | None = None,
        timeout: float | None = None,
    ) -> Result:
        headers = self._client.headers(self._bearer)
        if prefer:
            headers["Prefer"] = ",".join(prefer)
        if body is not None:
            headers["Content-Type"] = "application/json"
        try:
            response = await self._client.http.request(
                method,
                f"{self._client.url}/rest/v1/{path}",
                params=params,
                content=json.dumps(body) if body is not None else None,
                headers=headers,
                timeout=timeout or QUICK_SECONDS,
            )
        except httpx.HTTPError as exc:
            return Result(error=ApiError.network(exc))
        if response.status_code >= 400:
            return Result(error=_error_from(response))
        count = None
        content_range = response.headers.get("content-range", "")
        if prefer and any(p.startswith("count=") for p in prefer) and "/" in content_range:
            tail = content_range.split("/")[-1]
            count = int(tail) if tail.isdigit() else None
        data = None
        if method != "HEAD" and response.content:
            try:
                data = response.json()
            except ValueError:
                return Result(error=ApiError(response.status_code, None, response.text[:200]))
        return Result(data=data, count=count)


class Storage:
    """Supabase Storage as one caller."""

    def __init__(self, client: "Supabase", bearer: str | None):
        self._client = client
        self._bearer = bearer

    async def upload(self, bucket: str, path: str, content: bytes, content_type: str, filename: str = "blob") -> Result:
        """Uploads a file as supabase-js uploads a File: a multipart form with cacheControl and the file."""
        clean = re.sub(r"/+", "/", path.strip("/"))
        headers = self._client.headers(self._bearer)
        headers["x-upsert"] = "false"
        try:
            response = await self._client.http.post(
                f"{self._client.url}/storage/v1/object/{bucket}/{clean}",
                data={"cacheControl": "3600"},
                files={"": (filename, content, content_type)},
                headers=headers,
                timeout=UPLOAD_SECONDS,
            )
        except httpx.HTTPError as exc:
            return Result(error=ApiError.network(exc))
        if response.status_code >= 400:
            return Result(error=_error_from(response))
        return Result(data={"path": clean})

    async def signed_url(self, bucket: str, path: str, expires_in: int) -> str | None:
        try:
            response = await self._client.http.post(
                f"{self._client.url}/storage/v1/object/sign/{bucket}/{path.lstrip('/')}",
                json={"expiresIn": expires_in},
                headers=self._client.headers(self._bearer),
                timeout=QUICK_SECONDS,
            )
        except httpx.HTTPError:
            return None
        if response.status_code >= 400:
            return None
        signed = response.json().get("signedURL")
        if not signed:
            return None
        # supabase-js passes the joined address through encodeURI.
        return quote(f"{self._client.url}/storage/v1{signed}", safe=":/?#[]@!$&'()*+,;=-._~%")

    async def remove(self, bucket: str, paths: list[str]) -> Result:
        try:
            response = await self._client.http.request(
                "DELETE",
                f"{self._client.url}/storage/v1/object/{bucket}",
                content=json.dumps({"prefixes": paths}),
                headers={**self._client.headers(self._bearer), "Content-Type": "application/json"},
                timeout=QUICK_SECONDS,
            )
        except httpx.HTTPError as exc:
            return Result(error=ApiError.network(exc))
        if response.status_code >= 400:
            return Result(error=_error_from(response))
        return Result(data=response.json() if response.content else [])


@dataclass
class Supabase:
    url: str
    key: str
    http: httpx.AsyncClient
    service_role_key: str | None = None
    extra: dict = field(default_factory=dict)

    def headers(self, bearer: str | None) -> dict[str, str]:
        return {"apikey": self.key, "Authorization": f"Bearer {bearer or self.key}"}

    # ---------------------------------------------------------------- callers
    def as_user(self, access_token: str) -> Database:
        return Database(self, access_token)

    def as_visitor(self) -> Database:
        return Database(self, None)

    def storage_as(self, access_token: str) -> Storage:
        return Storage(self, access_token)

    def as_service(self) -> Database | None:
        """The service role bypasses row level security. Only the waitlist endpoint uses it."""
        if not self.service_role_key:
            return None
        db = Database(Supabase(self.url, self.service_role_key, self.http), self.service_role_key)
        return db

    # ---------------------------------------------------------------- auth
    async def _auth(self, method: str, path: str, body: dict | None = None, bearer: str | None = None,
                    params: dict | None = None) -> Result:
        try:
            response = await self.http.request(
                method, f"{self.url}/auth/v1/{path}", params=params, json=body,
                headers=self.headers(bearer), timeout=QUICK_SECONDS,
            )
        except httpx.HTTPError as exc:
            return Result(error=ApiError.network(exc))
        if response.status_code >= 400:
            return Result(error=_error_from(response))
        return Result(data=response.json() if response.content else None)

    async def send_email_code(self, email: str, data: dict | None, redirect_to: str | None,
                              code_challenge: str | None) -> Result:
        body = {
            "email": email,
            "data": data or {},
            "create_user": True,
            "gotrue_meta_security": {"captcha_token": None},
            "code_challenge": code_challenge,
            "code_challenge_method": "s256" if code_challenge else None,
        }
        return await self._auth("POST", "otp", body, params={"redirect_to": redirect_to} if redirect_to else None)

    async def send_phone_code(self, phone: str, channel: str, data: dict | None) -> Result:
        body = {
            "phone": phone,
            "data": data or {},
            "create_user": True,
            "gotrue_meta_security": {"captcha_token": None},
            "channel": channel,
        }
        return await self._auth("POST", "otp", body)

    async def verify_code(self, kind: str, address: str, code: str) -> tuple[Session | None, ApiError | None]:
        body = {kind: address, "token": code, "type": "email" if kind == "email" else "sms",
                "gotrue_meta_security": {"captcha_token": None}}
        r = await self._auth("POST", "verify", body)
        if not r.ok:
            return None, r.error
        session = _session_from(r.data)
        return (session, None) if session else (None, ApiError(None, "no_session", "verify returned no session"))

    async def exchange_code(self, auth_code: str, code_verifier: str) -> tuple[Session | None, ApiError | None]:
        r = await self._auth("POST", "token", {"auth_code": auth_code, "code_verifier": code_verifier},
                             params={"grant_type": "pkce"})
        if not r.ok:
            return None, r.error
        session = _session_from(r.data)
        return (session, None) if session else (None, ApiError(None, "no_session", "exchange returned no session"))

    async def refresh(self, refresh_token: str) -> tuple[Session | None, ApiError | None]:
        r = await self._auth("POST", "token", {"refresh_token": refresh_token}, params={"grant_type": "refresh_token"})
        if not r.ok:
            return None, r.error
        return _session_from(r.data), None

    async def get_user(self, access_token: str) -> tuple[dict | None, ApiError | None]:
        """Asks Supabase to confirm the token, so a forged or revoked one is refused."""
        r = await self._auth("GET", "user", bearer=access_token)
        if not r.ok:
            return None, r.error
        return r.data, None

    async def sign_out(self, access_token: str) -> None:
        await self._auth("POST", "logout", bearer=access_token, params={"scope": "global"})


def make_client(s: Settings, http: httpx.AsyncClient) -> Supabase | None:
    if not s.supabase_configured:
        return None
    return Supabase(url=s.supabase_url, key=s.supabase_key, http=http, service_role_key=s.service_role_key)
