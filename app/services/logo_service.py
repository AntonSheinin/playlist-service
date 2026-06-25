import re
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx
from fastapi import UploadFile

from app.exceptions import ValidationError

BASE_DIR = Path(__file__).resolve().parents[2]
LOGO_DIR = BASE_DIR / "media" / "logos"
MAX_LOGO_BYTES = 2 * 1024 * 1024
LOGO_URL_PREFIX = "/media/logos/"

_IMAGE_SIGNATURES: list[tuple[bytes, str]] = [
    (b"\x89PNG\r\n\x1a\n", "png"),
    (b"\xff\xd8\xff", "jpeg"),
    (b"GIF87a", "gif"),
    (b"GIF89a", "gif"),
]


def detect_image_type(data: bytes) -> str | None:
    for signature, image_type in _IMAGE_SIGNATURES:
        if data[: len(signature)] == signature:
            return image_type
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def sanitize_logo_basename(value: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip())
    return base.strip("._-").lower()


def build_logo_filename(
    stream_name: str | None,
    channel_id: int | None,
    extension: str,
) -> str:
    base = sanitize_logo_basename(stream_name or "")
    if not base:
        return f"{uuid4().hex}.{extension}"

    candidate = f"{base}.{extension}"
    if not (LOGO_DIR / candidate).exists():
        return candidate

    if channel_id is not None:
        candidate = f"{base}-{channel_id}.{extension}"
        if not (LOGO_DIR / candidate).exists():
            return candidate

    counter = 2
    while True:
        candidate = f"{base}-{counter}.{extension}"
        if not (LOGO_DIR / candidate).exists():
            return candidate
        counter += 1


def resolve_logo_path(logo_url: str | None) -> Path | None:
    if not logo_url:
        return None
    path = urlparse(logo_url).path or ""
    if not path.startswith(LOGO_URL_PREFIX):
        return None
    filename = Path(path).name
    if not filename:
        return None
    return LOGO_DIR / filename


def is_safe_logo_path(path: Path) -> bool:
    try:
        return path.resolve().is_relative_to(LOGO_DIR.resolve())
    except OSError:
        return False


async def save_logo_bytes(
    content: bytes,
    stream_name: str | None = None,
    channel_id: int | None = None,
) -> str:
    if not content:
        raise ValidationError("Uploaded file is empty")
    if len(content) > MAX_LOGO_BYTES:
        raise ValidationError("Logo exceeds 2MB limit")

    image_type = detect_image_type(content)
    if image_type is None:
        raise ValidationError("Unsupported image type")

    extension = "jpg" if image_type == "jpeg" else image_type
    LOGO_DIR.mkdir(parents=True, exist_ok=True)
    filename = build_logo_filename(stream_name, channel_id, extension)
    logo_path = LOGO_DIR / filename
    logo_path.write_bytes(content)

    return f"{LOGO_URL_PREFIX}{filename}"


async def save_logo_file(
    upload: UploadFile,
    stream_name: str | None = None,
    channel_id: int | None = None,
) -> str:
    if upload.content_type and not upload.content_type.startswith("image/"):
        raise ValidationError("Only image uploads are allowed")

    content = await upload.read(MAX_LOGO_BYTES + 1)
    await upload.close()

    return await save_logo_bytes(content, stream_name=stream_name, channel_id=channel_id)


async def save_logo_url(
    url: str,
    stream_name: str | None = None,
    channel_id: int | None = None,
) -> str:
    if not url:
        raise ValidationError("Logo URL is required")

    timeout = httpx.Timeout(10.0, connect=5.0)
    async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
        async with client.stream("GET", url) as response:
            if response.status_code >= 400:
                raise ValidationError("Failed to download logo")

            content_type = response.headers.get("Content-Type", "")
            if content_type and not content_type.startswith("image/"):
                raise ValidationError("Logo URL must point to an image")

            data = bytearray()
            async for chunk in response.aiter_bytes():
                data.extend(chunk)
                if len(data) > MAX_LOGO_BYTES:
                    raise ValidationError("Logo exceeds 2MB limit")

    return await save_logo_bytes(bytes(data), stream_name=stream_name, channel_id=channel_id)
