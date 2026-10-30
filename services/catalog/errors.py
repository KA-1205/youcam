"""Domain errors raised by lane A services; HTTP mapping belongs to lane C."""
from __future__ import annotations


class CatalogError(Exception):
    """Base class carrying a stable error code and the HTTP status lane C maps it to."""

    status = 500

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class NotFoundError(CatalogError):
    """Unknown or non-owned resource; never reveals other tenants' contents."""

    status = 404

    def __init__(self, message: str = 'Unknown or non-owned resource.') -> None:
        super().__init__('NOT_FOUND', message)


class StaleCatalogError(CatalogError):
    """A cursor, version or snapshot no longer matches the current catalog state."""

    status = 409

    def __init__(self, message: str = 'Catalog state moved; retry with a fresh read.') -> None:
        super().__init__('STALE_VERSION', message)


class InvalidRequestError(CatalogError):
    """Semantically invalid input that the frozen DTO shape cannot express."""

    status = 422

    def __init__(self, message: str, code: str = 'INVALID_REQUEST') -> None:
        super().__init__(code, message)
