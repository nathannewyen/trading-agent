"""Simple in-process rate limiting middleware for the trading research API.

Limits each client IP to MAX_REQUESTS_PER_MINUTE requests per minute using
a sliding window implemented with a deque.  Requests that exceed the limit
receive a 429 Too Many Requests response instead of hitting the Anthropic API.
"""

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

MAX_REQUESTS_PER_MINUTE = 10
WINDOW_SECONDS = 60


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_rpm: int = MAX_REQUESTS_PER_MINUTE):
        super().__init__(app)
        self._max_rpm = max_rpm
        self._windows: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        if request.url.path == "/health":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        now = time.monotonic()
        window = self._windows[client_ip]

        # Evict timestamps outside the sliding window
        while window and now - window[0] > WINDOW_SECONDS:
            window.popleft()

        if len(window) >= self._max_rpm:
            retry_after = int(WINDOW_SECONDS - (now - window[0])) + 1
            return JSONResponse(
                status_code=429,
                content={"error": "Rate limit exceeded", "retry_after_seconds": retry_after},
                headers={"Retry-After": str(retry_after)},
            )

        window.append(now)
        return await call_next(request)
