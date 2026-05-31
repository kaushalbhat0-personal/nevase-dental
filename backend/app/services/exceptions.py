class ServiceError(Exception):
    """Base error for service-layer failures."""

    status_code: int = 400
    detail: str = "Service error"

    def __init__(self, detail: str | None = None) -> None:
        self.detail = detail or self.detail
        super().__init__(self.detail)


class ValidationError(ServiceError):
    status_code = 400
    detail = "Invalid input"


class ConflictError(ServiceError):
    status_code = 400
    detail = "Conflict"


class NotFoundError(ServiceError):
    status_code = 404
    detail = "Resource not found"


class AuthenticationError(ServiceError):
    status_code = 401
    detail = "Could not validate credentials"


class ForbiddenError(ServiceError):
    status_code = 403
    detail = "Forbidden"


class StaleStateError(ServiceError):
    """Optimistic-lock style conflict (e.g. verification already processed by another reviewer)."""

    status_code = 409
    detail = "Resource state changed; refresh and retry"
