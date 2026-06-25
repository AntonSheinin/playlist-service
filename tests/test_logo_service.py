from pathlib import Path

import pytest

from app.exceptions import ValidationError
from app.services import logo_service


PNG = b"\x89PNG\r\n\x1a\npayload"
JPEG = b"\xff\xd8\xffpayload"
GIF = b"GIF89apayload"
WEBP = b"RIFFxxxxWEBPpayload"


@pytest.mark.parametrize(
    ("content", "expected"),
    [(PNG, "png"), (JPEG, "jpeg"), (GIF, "gif"), (WEBP, "webp")],
)
def test_detect_image_type_accepts_supported_signatures(content, expected):
    assert logo_service.detect_image_type(content) == expected


@pytest.mark.asyncio
async def test_save_logo_bytes_rejects_empty_and_invalid_content():
    with pytest.raises(ValidationError, match="empty"):
        await logo_service.save_logo_bytes(b"")

    with pytest.raises(ValidationError, match="Unsupported image type"):
        await logo_service.save_logo_bytes(b"not-an-image")


@pytest.mark.asyncio
async def test_save_logo_bytes_rejects_oversized_content():
    with pytest.raises(ValidationError, match="exceeds"):
        await logo_service.save_logo_bytes(PNG + b"x" * logo_service.MAX_LOGO_BYTES)


def test_build_logo_filename_preserves_collision_behavior(tmp_path, monkeypatch):
    monkeypatch.setattr(logo_service, "LOGO_DIR", tmp_path)
    (tmp_path / "news.png").write_bytes(PNG)
    (tmp_path / "news-10.png").write_bytes(PNG)

    assert logo_service.build_logo_filename("News", 10, "png") == "news-2.png"


def test_resolve_logo_path_refuses_paths_outside_logo_prefix(tmp_path, monkeypatch):
    monkeypatch.setattr(logo_service, "LOGO_DIR", tmp_path)

    assert logo_service.resolve_logo_path("/not-logos/file.png") is None
    assert logo_service.resolve_logo_path("/media/logos/../secret.png") == tmp_path / "secret.png"
    assert not logo_service.is_safe_logo_path(Path("..") / "secret.png")
