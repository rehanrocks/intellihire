"""A small in-memory rate limiter (US-1.4, NFR-03).

Brute-force protection: an attacker who can try passwords thousands of times
per minute will eventually guess one. We cap how many times one client IP may
hit sensitive endpoints inside a time window.

This implementation keeps counters in the Python process, which is fine for
one server. With several API instances you would move the counters to Redis
so all instances share them. The interface would stay the same.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, Request

from app.core.config import Settings, get_settings
from app.core.exceptions import TooManyRequests


class RateLimiter:
    def __init__(self, max_requests: int, window_seconds: int):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        """Sliding window: keep the timestamps of recent hits per key."""
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits[key]
            # Drop hits that fell out of the window.
            while hits and now - hits[0] > self.window_seconds:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            return True

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


_limiters: dict[str, RateLimiter] = {}


def get_limiter(scope: str, settings: Settings) -> RateLimiter:
    if scope not in _limiters:
        _limiters[scope] = RateLimiter(settings.rate_limit_auth_requests, settings.rate_limit_auth_window_seconds)
    return _limiters[scope]


def rate_limit(scope: str):
    """FastAPI dependency factory: `Depends(rate_limit("login"))`."""

    def dependency(request: Request, settings: Settings = Depends(get_settings)) -> None:
        if not settings.rate_limit_enabled:
            return
        client_ip = request.client.host if request.client else "unknown"
        if not get_limiter(scope, settings).allow(f"{scope}:{client_ip}"):
            raise TooManyRequests()

    return dependency
