class PlaylistServiceError(Exception):
    """Base exception for playlist service."""

    status_code: int = 500

    def __init__(self, message: str, code: str = "INTERNAL_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(PlaylistServiceError):
    """Resource not found."""

    status_code = 404

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="NOT_FOUND")


class ValidationError(PlaylistServiceError):
    """Validation error."""

    status_code = 422

    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message, code="VALIDATION_ERROR")


class DuplicateEntryError(PlaylistServiceError):
    """Duplicate entry error."""

    status_code = 409

    def __init__(self, message: str = "Duplicate entry") -> None:
        super().__init__(message, code="DUPLICATE_ENTRY")


class UnauthorizedError(PlaylistServiceError):
    """Unauthorized access or invalid credentials."""

    status_code = 401

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, code="UNAUTHORIZED")


class FlussonicError(PlaylistServiceError):
    """Flussonic API error."""

    status_code = 502

    def __init__(self, message: str = "Flussonic API error") -> None:
        super().__init__(message, code="FLUSSONIC_ERROR")


class AuthServiceError(PlaylistServiceError):
    """Auth Service API error."""

    status_code = 502

    def __init__(self, message: str = "Auth Service error") -> None:
        super().__init__(message, code="AUTH_SERVICE_ERROR")


class EpgServiceError(PlaylistServiceError):
    """EPG Service API error."""

    status_code = 502

    def __init__(self, message: str = "EPG Service error") -> None:
        super().__init__(message, code="EPG_SERVICE_ERROR")
