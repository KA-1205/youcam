"""Domain errors raised by lane A services; HTTP mapping belongs to lane C."""
from __future__ import annotations


class StylistError(Exception):
    """Base class carrying a stable error code and the HTTP status lane C maps it to."""

    status = 500

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class NotFoundError(StylistError):
    """Unknown or non-owned resource; never reveals other tenants' contents."""

    status = 404

    def __init__(self, message: str = 'Unknown or non-owned resource.') -> None:
        super().__init__('NOT_FOUND', message)


class StaleSessionError(StylistError):
    """The expected session version does not match current state."""

    status = 409

    def __init__(self, message: str = 'Refresh this session.') -> None:
        super().__init__('STALE_SESSION', message)


class IdempotencyConflict(StylistError):
    """The same idempotency key was reused with a different request body."""

    status = 409

    def __init__(self, message: str = 'Idempotency key was already used with a different '
                                     'request.') -> None:
        super().__init__('IDEMPOTENCY_CONFLICT', message)
