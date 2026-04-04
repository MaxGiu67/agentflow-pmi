"""Rate limiting middleware per tenant (US-114).

Simple in-memory rate limiter. For production with multiple workers,
replace with Redis-based rate limiting.
"""

import time
import logging
from collections import defaultdict

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

DEFAULT_RATE_LIMIT = 60  # requests per minute per tenant
EXEMPT_PATHS = {"/api/v1/email/webhook", "/api/v1/health", "/docs", "/openapi.json"}


class TenantRateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limit API calls per tenant (not per IP)."""

    def __init__(self, app, default_limit: int = DEFAULT_RATE_LIMIT):
        super().__init__(app)
        self.default_limit = default_limit
        # tenant_id → list of timestamps
        self._requests: dict[str, list[float]] = defaultdict(list)

    async def dispatch(self, request: Request, call_next):
        # Skip exempt paths
        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        # Skip non-API paths
        if not request.url.path.startswith("/api/"):
            return await call_next(request)

        # Extract tenant_id from JWT (set by auth middleware)
        tenant_id = getattr(request.state, "tenant_id", None) if hasattr(request, "state") else None

        if not tenant_id:
            # No tenant → extract from auth header if possible
            # For now, skip rate limiting for unauthenticated requests
            return await call_next(request)

        tenant_key = str(tenant_id)
        now = time.time()
        window = 60.0  # 1 minute window

        # Clean old entries
        self._requests[tenant_key] = [
            t for t in self._requests[tenant_key] if now - t < window
        ]

        if len(self._requests[tenant_key]) >= self.default_limit:
            retry_after = int(window - (now - self._requests[tenant_key][0]))
            logger.warning("Rate limit exceeded for tenant %s", tenant_key)
            return Response(
                content='{"detail":"Rate limit superato. Riprova tra qualche secondo."}',
                status_code=429,
                headers={
                    "Retry-After": str(max(1, retry_after)),
                    "X-RateLimit-Limit": str(self.default_limit),
                    "X-RateLimit-Remaining": "0",
                    "Content-Type": "application/json",
                },
            )

        self._requests[tenant_key].append(now)

        response = await call_next(request)

        # Add rate limit headers
        remaining = self.default_limit - len(self._requests[tenant_key])
        response.headers["X-RateLimit-Limit"] = str(self.default_limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, remaining))

        return response
