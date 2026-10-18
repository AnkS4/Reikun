"""
Tiny in-memory, per-client rate limiter for the public API.

Why: `/explain*` spends Groq quota (the daily cap is shared by every visitor)
and `/search` burns CPU on embedding — on a public Cloud Run URL one script can
exhaust either. State is per process, so with N instances the effective limit
is N times that — fine as an abuse brake, not as a billing guarantee.

Client identity: behind a reverse proxy the socket peer is the proxy, so the
real client comes from `X-Forwarded-For`. Each proxy *appends* the address it
saw, so the only trustworthy entry is the one added by our own proxy — counted
from the right (`trusted_hops`). Entries further left are client-supplied and
spoofable, so they are ignored.
"""

from __future__ import annotations

import math
import threading
import time
from collections import deque
from collections.abc import Callable

from fastapi import HTTPException, Request


class SlidingWindowLimiter:
    """At most `limit` hits per `window_s` seconds for each key."""

    def __init__(
        self,
        limit: int,
        window_s: float = 60.0,
        *,
        max_keys: int = 10_000,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.limit = limit
        self.window_s = window_s
        self.max_keys = max_keys
        self._clock = clock
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str) -> float:
        """Record a request. Returns 0.0 if allowed, else seconds until a slot frees up."""
        now = self._clock()
        cutoff = now - self.window_s
        with self._lock:
            q = self._hits.setdefault(key, deque())
            while q and q[0] <= cutoff:
                q.popleft()
            if len(q) >= self.limit:
                return max(q[0] + self.window_s - now, 0.001)
            q.append(now)
            if len(self._hits) > self.max_keys:
                self._prune(cutoff)
            return 0.0

    def _prune(self, cutoff: float) -> None:
        """Drop idle clients so a crawl from many IPs can't grow memory without bound."""
        for k in [k for k, q in self._hits.items() if not q or q[-1] <= cutoff]:
            del self._hits[k]


def client_ip(request: Request, trusted_hops: int = 1) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff and trusted_hops > 0:
        parts = [p.strip() for p in xff.split(",") if p.strip()]
        if len(parts) >= trusted_hops:
            return parts[-trusted_hops]
        if parts:
            return parts[0]
    return request.client.host if request.client else "unknown"


def rate_limited(per_minute: int, trusted_hops: int = 1) -> Callable[..., object]:
    """FastAPI dependency factory: 429 + Retry-After once a client exceeds `per_minute`.
    `per_minute <= 0` disables the limit."""
    if per_minute <= 0:

        async def _unlimited() -> None:
            return None

        return _unlimited

    limiter = SlidingWindowLimiter(per_minute)

    async def _check(request: Request) -> None:
        wait = limiter.hit(client_ip(request, trusted_hops))
        if wait:
            raise HTTPException(
                429,
                "Too many requests — please wait a few seconds and try again.",
                headers={"Retry-After": str(math.ceil(wait))},
            )

    return _check
