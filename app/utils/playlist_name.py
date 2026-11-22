MAX_PLAYLIST_NAME_LENGTH = 302


def validate_playlist_name(value: str) -> str:
    if not 1 <= len(value) <= MAX_PLAYLIST_NAME_LENGTH:
        raise ValueError("Playlist URL name must contain 1–302 characters")
    if not all(char.isalnum() or char in "_-" for char in value):
        raise ValueError(
            "Playlist URL name may contain only letters, numbers, underscores, and hyphens; omit .m3u8"
        )
    return value


def generate_playlist_name(first_name: str, last_name: str, agreement_number: str) -> str:
    parts = []
    for value in (last_name, first_name, agreement_number):
        value = value.replace(" ", "_")
        parts.append("".join(char for char in value if char.isalnum() or char in "_-"))
    return validate_playlist_name("_".join(parts))
