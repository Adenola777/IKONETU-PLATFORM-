"""A fake Supabase for the route tests, built on httpx's MockTransport.

It answers the calls the app makes with canned replies and records each
request, so a test can check what the app sent. Nothing leaves the machine.
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass, field
from typing import Callable

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.supabase import Supabase

URL = "https://example.supabase.co"
KEY = "sb_publishable_test"


def jwt(exp_in: int = 3600, sub: str = "u-1") -> str:
    """An unsigned token with the claims the app reads to time a refresh."""
    def part(d: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).decode().rstrip("=")
    return f"{part({'alg': 'none'})}.{part({'sub': sub, 'exp': int(time.time()) + exp_in})}.sig"


@dataclass
class FakeSupabase:
    routes: dict[tuple[str, str], Callable[[httpx.Request], httpx.Response]] = field(default_factory=dict)
    requests: list[httpx.Request] = field(default_factory=list)

    def on(self, method: str, path: str, reply: Callable[[httpx.Request], httpx.Response] | httpx.Response):
        self.routes[(method, path)] = reply if callable(reply) else (lambda _r, res=reply: res)

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        reply = self.routes.get((request.method, request.url.path))
        if reply is None:
            return httpx.Response(404, json={"message": f"no fake for {request.method} {request.url.path}"})
        return reply(request)

    def sent(self, method: str, path: str) -> list[httpx.Request]:
        return [r for r in self.requests if r.method == method and r.url.path == path]


@pytest.fixture
def fake():
    return FakeSupabase()


@pytest.fixture
def client(fake):
    with TestClient(app, follow_redirects=False) as c:
        http = httpx.AsyncClient(transport=httpx.MockTransport(fake.handler))
        app.state.supabase = Supabase(url=URL, key=KEY, http=http, service_role_key="service-test")
        yield c
