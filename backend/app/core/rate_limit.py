from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from typing import Deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import JSONResponse, Response

from app.core.config import settings
from app.core.security import decode_access_token


@dataclass(frozen=True)
class RateLimitRule:
    window_seconds: int
    max_requests: int


class PublicEndpointRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Minimal in-memory rate limiter for public marketplace endpoints.

    - Scope: only GET /api/v1/doctors and GET /api/v1/tenants
    - Key: client IP (X-Forwarded-For first hop if present, else request.client.host)

    Notes / trade-offs:
    - This is intentionally simple and **process-local**. In multi-worker deployments (e.g. gunicorn
      with multiple workers, or multiple instances behind a load balancer), limits are enforced per
      worker/instance and will not be globally consistent.
    - We read `X-Forwarded-For` because most PaaS providers/proxies sit in front of the app. Only
      trust it if your deployment ensures it is set/overwritten by the proxy (not client-controlled).
    """

    def __init__(self, app, *, rule: RateLimitRule) -> None:
        super().__init__(app)
        self._rule = rule
        self._hits: dict[str, Deque[float]] = {}

    def _client_ip(self, request: Request) -> str:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            # First hop is the original client IP (when set by a trusted proxy).
            return xff.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    def _is_public_marketplace_endpoint(self, request: Request) -> bool:
        if request.method != "GET":
            return False
        path = request.url.path
        return path in ("/api/v1/doctors", "/api/v1/tenants")

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if not self._is_public_marketplace_endpoint(request):
            return await call_next(request)

        ip = self._client_ip(request)
        now = time.time()
        window_start = now - self._rule.window_seconds

        q = self._hits.get(ip)
        if q is None:
            q = deque()
            self._hits[ip] = q

        # Sliding-window enforcement: we keep timestamps within the active window only.
        while q and q[0] < window_start:
            q.popleft()

        limit = self._rule.max_requests
        if len(q) >= self._rule.max_requests:
            retry_after = int(q[0] + self._rule.window_seconds - now) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(max(1, retry_after)),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        q.append(now)
        remaining = max(0, limit - len(q))
        response = await call_next(request)
        # These headers are useful for debugging and for clients that want to back off gracefully.
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


# Per-user (JWT sub) rate limits for sensitive write endpoints (prefix match).
_WRITE_APPOINTMENTS_RULE = RateLimitRule(window_seconds=60, max_requests=30)
_WRITE_BILLS_RULE = RateLimitRule(window_seconds=60, max_requests=10)
_WRITE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


class AuthenticatedWritePostRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limit mutating /appointments and /bills routes per authenticated user (JWT sub).
    Unauthenticated requests fall back to client IP for the same limits.

    Why per-user:
    - For authenticated endpoints, IP-based limits can punish NATed users (hospitals, offices).
      Using the JWT subject makes limits fairer per user, while still providing an IP fallback.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self._hits: dict[str, Deque[float]] = {}

    def _client_ip(self, request: Request) -> str:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    def _user_id_from_auth_header(self, request: Request) -> str | None:
        auth = request.headers.get("authorization")
        if not auth or not auth.lower().startswith("bearer "):
            return None
        parts = auth.split(None, 1)
        if len(parts) < 2:
            return None
        # We only use the token to extract a stable bucket key. Authorization decisions still happen
        # in the actual route dependencies (e.g. get_current_active_user).
        payload = decode_access_token(parts[1])
        if not payload or payload.get("type") != "access":
            return None
        sub = payload.get("sub")
        return str(sub) if isinstance(sub, str) else None

    def _route_rule(self, request: Request) -> RateLimitRule | None:
        if request.method not in _WRITE_METHODS:
            return None
        path = request.url.path or "/"
        if path.startswith("/api/v1/appointments"):
            return _WRITE_APPOINTMENTS_RULE
        if path.startswith("/api/v1/bills"):
            return _WRITE_BILLS_RULE
        return None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        rule = self._route_rule(request)
        if rule is None:
            return await call_next(request)

        uid = self._user_id_from_auth_header(request)
        bucket_key = f"user:{uid}" if uid else f"ip:{self._client_ip(request)}"
        now = time.time()
        window_start = now - rule.window_seconds

        q = self._hits.get(bucket_key)
        if q is None:
            q = deque()
            self._hits[bucket_key] = q

        while q and q[0] < window_start:
            q.popleft()

        limit = rule.max_requests
        if len(q) >= limit:
            retry_after = int(q[0] + rule.window_seconds - now) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={
                    "Retry-After": str(max(1, retry_after)),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        q.append(now)
        remaining = max(0, limit - len(q))
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response


class IntegrityScanGetRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Expensive admin integrity scan: throttle GET /api/v1/admin/integrity-scan per JWT user or IP.
    """

    def __init__(self, app) -> None:
        super().__init__(app)
        self._hits: dict[str, Deque[float]] = {}

    def _client_ip(self, request: Request) -> str:
        xff = request.headers.get("x-forwarded-for")
        if xff:
            return xff.split(",")[0].strip()
        if request.client and request.client.host:
            return request.client.host
        return "unknown"

    def _user_id_from_auth_header(self, request: Request) -> str | None:
        auth = request.headers.get("authorization")
        if not auth or not auth.lower().startswith("bearer "):
            return None
        parts = auth.split(None, 1)
        if len(parts) < 2:
            return None
        payload = decode_access_token(parts[1])
        if not payload or payload.get("type") != "access":
            return None
        sub = payload.get("sub")
        return str(sub) if isinstance(sub, str) else None

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path or "/"
        if request.method != "GET" or path != "/api/v1/admin/integrity-scan":
            return await call_next(request)

        limit_val = max(1, int(settings.INTEGRITY_SCAN_RATE_LIMIT_PER_MINUTE))
        rule = RateLimitRule(window_seconds=60, max_requests=limit_val)

        uid = self._user_id_from_auth_header(request)
        bucket_key = f"integrity-scan:user:{uid}" if uid else f"integrity-scan:ip:{self._client_ip(request)}"
        now = time.time()
        window_start = now - rule.window_seconds

        q = self._hits.get(bucket_key)
        if q is None:
            q = deque()
            self._hits[bucket_key] = q

        while q and q[0] < window_start:
            q.popleft()

        limit = rule.max_requests
        if len(q) >= limit:
            retry_after = int(q[0] + rule.window_seconds - now) + 1
            return JSONResponse(
                status_code=429,
                content={"detail": "Integrity scan rate limit exceeded"},
                headers={
                    "Retry-After": str(max(1, retry_after)),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                },
            )

        q.append(now)
        remaining = max(0, limit - len(q))
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
