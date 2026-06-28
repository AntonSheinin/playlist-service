import pytest

from app.models import Channel, Package, StreamSource, Tariff, User, UserStatus
from app.services.auth_sync import AuthSyncService
from app.services.playlist_generator import PlaylistGenerator
from app.services.user_service import UserService


@pytest.mark.asyncio
async def test_resolve_channels_deduplicates_assignments_and_preserves_order(db_session):
    direct = Channel(
        source=StreamSource.FLUSSONIC,
        stream_name="direct",
        channel_number=2,
        sort_order=30,
    )
    shared = Channel(
        source=StreamSource.FLUSSONIC,
        stream_name="shared",
        channel_number=1,
        sort_order=20,
    )
    no_number = Channel(
        source=StreamSource.NIMBLE,
        stream_name="late",
        channel_number=None,
        sort_order=1,
    )
    package = Package(name="Base", channels=[shared, no_number])
    tariff = Tariff(name="Premium", packages=[package])
    user = User(
        first_name="A",
        last_name="B",
        agreement_number="100",
        status=UserStatus.ENABLED,
        max_sessions=1,
        token="token",
        channels=[direct, shared],
        packages=[package],
        tariffs=[tariff],
    )
    db_session.add(user)
    await db_session.flush()

    channels = await UserService(db_session).resolve_channels(user.id)

    assert [channel.stream_name for channel in channels] == ["shared", "direct", "late"]


@pytest.mark.asyncio
async def test_resolve_channels_returns_empty_for_user_without_assignments(db_session):
    user = User(
        first_name="A",
        last_name="B",
        agreement_number="101",
        status=UserStatus.ENABLED,
        max_sessions=1,
        token="token",
    )
    db_session.add(user)
    await db_session.flush()

    assert await UserService(db_session).resolve_channels(user.id) == []


def test_provider_variants_remain_playlist_rows_but_auth_sync_deduplicates_streams(monkeypatch):
    class FakeProvider:
        def build_stream_url(self, stream_name: str, token: str) -> str:
            return f"https://example.test/{stream_name}?token={token}"

    monkeypatch.setattr(
        "app.services.playlist_generator.get_stream_provider",
        lambda source: FakeProvider(),
    )
    user = User(
        first_name="A",
        last_name="B",
        agreement_number="102",
        status=UserStatus.ENABLED,
        max_sessions=1,
        token="token",
    )
    channels = [
        Channel(source=StreamSource.FLUSSONIC, stream_name="same"),
        Channel(source=StreamSource.NIMBLE, stream_name="same"),
    ]

    playlist = PlaylistGenerator().generate(user, channels)
    allowed_streams = AuthSyncService._build_allowed_streams(AuthSyncService.__new__(AuthSyncService), channels)

    assert playlist.count("#EXTINF") == 2
    assert playlist.count("https://example.test/same?token=token") == 2
    assert allowed_streams == ["same"]
