"""Domain errors raised by lane A services; HTTP mapping belongs to lane C."""
from __future__ import annotations


class RecommendationError(Exception):
    """Base class carrying a stable error code and the HTTP status lane C maps it to."""

    status = 500

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class NotFoundError(RecommendationError):
    """Unknown or non-owned resource; never reveals other tenants' contents."""

    status = 404

    def __init__(self, message: str = 'Unknown or non-owned resource.') -> None:
        super().__init__('NOT_FOUND', message)


class StaleSessionError(RecommendationError):
    """A version or cursor no longer matches current state."""

    status = 409

    def __init__(self, message: str = 'State moved; retry with a fresh read.') -> None:
        super().__init__('STALE_VERSION', message)
