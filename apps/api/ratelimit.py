"""Process-local fixed-window rate limiting for abuse-sensitive endpoints.

Counts per actor cookie fingerprint and path per minute. Limits are generous
defaults; the labelled development login is deliberately tighter. This is error
safety for a single demo deployment, not a distributed quota system.
"""
import os
import time
from collections import defaultdict, deque

from apps.api.errors import QUOTA_EXCEEDED, ApiError

WINDOW_SECONDS = 60.0


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def limit_for(self, path: str) -> int:
        if path.endswith('/auth/demo-login'):
            return int(os.getenv('ANCHOR_RATE_LOGIN', '10'))
        return int(os.getenv('ANCHOR_RATE_DEFAULT', '240'))

    def check(self, key: str, path: str) -> None:
        limit = self.limit_for(path)
        now = time.monotonic()
        bucket = self._hits[f'{key}:{path}']
        while bucket and now - bucket[0] > WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= limit:
            retry_after = int(WINDOW_SECONDS - (now - bucket[0])) + 1
            raise ApiError(429, QUOTA_EXCEEDED, 'Too many requests; slow down.',
                           headers={'Retry-After': str(retry_after)})
        bucket.append(now)
