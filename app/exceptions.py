class PlaylistServiceError(Exception):
    """Base exception for playlist service."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


class NotFoundError(PlaylistServiceError):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="NOT_FOUND")


class ValidationError(PlaylistServiceError):
    """Validation error."""

    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message, code="VALIDATION_ERROR")


class DuplicateEntryError(PlaylistServiceError):
    """Duplicate entry error."""

    def __init__(self, message: str = "Duplicate entry") -> None:
        super().__init__(message, code="DUPLICATE_ENTRY")


class UnauthorizedError(PlaylistServiceError):
    """Unauthorized access."""

    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, code="UNAUTHORIZED")


class InvalidCredentialsError(PlaylistServiceError):
    """Invalid credentials."""

    def __init__(self, message: str = "Invalid credentials") -> None:
        super().__init__(message, code="INVALID_CREDENTIALS")


class ChannelNotOrphanedError(PlaylistServiceError):
    """Cannot delete non-orphaned channel."""

    def __init__(self, message: str = "Can only delete orphaned channels") -> None:
        super().__init__(message, code="CHANNEL_NOT_ORPHANED")


class FlussonicError(PlaylistServiceError):
    """Flussonic API error."""

    def __init__(self, message: str = "Flussonic API error") -> None:
        super().__init__(message, code="FLUSSONIC_ERROR")


class AuthServiceError(PlaylistServiceError):
    """Auth Service API error."""

    def __init__(self, message: str = "Auth Service error") -> None:
        super().__init__(message, code="AUTH_SERVICE_ERROR")
