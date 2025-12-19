import secrets

from app.config import get_settings


def generate_token(length: int | None = None) -> str:
    """Generate a secure random token."""
    if length is None:
        length = get_settings().token_length
    return secrets.token_urlsafe(length)
