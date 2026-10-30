"""Domain errors mapped to the frozen error envelope codes."""

STALE_VERSION = 'STALE_VERSION'
SCOPE_FORBIDDEN = 'SCOPE_FORBIDDEN'
CONSENT_REQUIRED = 'CONSENT_REQUIRED'
QUOTA_EXCEEDED = 'QUOTA_EXCEEDED'
IDEMPOTENCY_CONFLICT = 'IDEMPOTENCY_CONFLICT'
PROVIDER_UNAVAILABLE = 'PROVIDER_UNAVAILABLE'
UNKNOWN_OUTCOME = 'UNKNOWN_OUTCOME'


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, headers: dict[str, str] | None = None):
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.headers = headers
