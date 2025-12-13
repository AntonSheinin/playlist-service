import httpx
from pydantic import BaseModel

from app.config import get_settings
from app.exceptions import FlussonicError


class FlussonicStream(BaseModel):
    """Represents a stream from Flussonic API."""

    name: str  # stream_name (unique identifier)
    title: str | None = None  # display_name
    dvr: int | None = None  # catchup_days
    static: bool = True


class FlussonicClient:
    """Client for Flussonic Media Server API."""

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = settings.flussonic_url.rstrip("/")
        self.username = settings.flussonic_username
        self.password = settings.flussonic_password

    async def get_streams(self) -> list[FlussonicStream]:
        """
        Fetch all streams from Flussonic.

        Tries multiple API endpoints for compatibility with different Flussonic versions:
        1. /streamer/api/v3/streams (newer versions)
        2. /flussonic/api/media (older versions)
        """
        async with httpx.AsyncClient(timeout=30.0) as client:
            auth = httpx.BasicAuth(self.username, self.password)

            # Try API v3 first
            try:
                response = await client.get(
                    f"{self.base_url}/streamer/api/v3/streams",
                    auth=auth,
                )
                if response.status_code == 200:
                    return self._parse_v3_response(response.json())
            except httpx.RequestError:
                pass

            # Try older API
            try:
                response = await client.get(
                    f"{self.base_url}/flussonic/api/media",
                    auth=auth,
                )
                if response.status_code == 200:
                    return self._parse_legacy_response(response.json())
            except httpx.RequestError:
                pass

            # Try erlyvideo API (even older)
            try:
                response = await client.get(
                    f"{self.base_url}/erlyvideo/api/streams",
                    auth=auth,
                )
                if response.status_code == 200:
                    return self._parse_legacy_response(response.json())
            except httpx.RequestError as e:
                raise FlussonicError(f"Failed to connect to Flussonic: {e}") from e

            raise FlussonicError(
                f"Failed to fetch streams from Flussonic. Status: {response.status_code}"
            )

    def _parse_v3_response(self, data: dict | list) -> list[FlussonicStream]:
        """Parse response from Flussonic API v3."""
        streams = []

        # Handle different response formats
        if isinstance(data, dict):
            # Could be {"streams": [...]} or direct stream objects
            if "streams" in data:
                items = data["streams"]
            elif "items" in data:
                items = data["items"]
            else:
                # Direct object mapping {name: stream_config}
                items = [{"name": k, **v} for k, v in data.items() if isinstance(v, dict)]
        else:
            items = data

        for item in items:
            if isinstance(item, dict):
                stream = FlussonicStream(
                    name=item.get("name", item.get("stream_name", "")),
                    title=item.get("title", item.get("display_name")),
                    dvr=self._extract_dvr_days(item),
                    static=item.get("static", True),
                )
                if stream.name:
                    streams.append(stream)

        return streams

    def _parse_legacy_response(self, data: dict | list) -> list[FlussonicStream]:
        """Parse response from legacy Flussonic API."""
        streams = []

        if isinstance(data, dict):
            # Handle {name: config} format
            for name, config in data.items():
                if isinstance(config, dict):
                    stream = FlussonicStream(
                        name=name,
                        title=config.get("title", config.get("display_name")),
                        dvr=self._extract_dvr_days(config),
                        static=config.get("static", True),
                    )
                    streams.append(stream)
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict):
                    stream = FlussonicStream(
                        name=item.get("name", ""),
                        title=item.get("title"),
                        dvr=self._extract_dvr_days(item),
                        static=item.get("static", True),
                    )
                    if stream.name:
                        streams.append(stream)

        return streams

    def _extract_dvr_days(self, item: dict) -> int | None:
        """Extract DVR days from various possible field names."""
        # Try different field names used across Flussonic versions
        for field in ["dvr", "dvr_days", "catchup_days", "archive_depth"]:
            if field in item:
                value = item[field]
                if isinstance(value, int):
                    return value
                if isinstance(value, dict) and "depth" in value:
                    # Format: {"dvr": {"depth": 14}}
                    depth = value["depth"]
                    if isinstance(depth, int):
                        # Convert minutes to days if needed
                        if depth > 365:  # Likely in minutes
                            return depth // (24 * 60)
                        return depth
        return None

    def get_stream_url(self, stream_name: str) -> str:
        """Get the base URL for a stream."""
        return f"{self.base_url}/{stream_name}"
