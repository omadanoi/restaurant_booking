"""Domain exception hierarchy.

Services raise these instead of `fastapi.HTTPException` so that business
logic stays transport-agnostic and unit-testable without a running app.
A single global handler (registered in `app.main`) maps each type to an
HTTP status code.
"""


class AppError(Exception):
    """Base class for all domain-level errors."""

    status_code: int = 500
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None) -> None:
        if detail is not None:
            self.detail = detail
        super().__init__(self.detail)


class NotFoundError(AppError):
    status_code = 404
    detail = "The requested resource was not found."


class ValidationError(AppError):
    status_code = 422
    detail = "Invalid request data."


class AuthenticationError(AppError):
    status_code = 401
    detail = "Authentication failed."


class PermissionDeniedError(AppError):
    status_code = 403
    detail = "You do not have permission to perform this action."


class ConflictError(AppError):
    status_code = 409
    detail = "The request could not be completed due to a conflict."


class OverlappingReservationError(ConflictError):
    detail = "The selected table is already reserved for an overlapping time window."
