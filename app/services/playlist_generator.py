from app.config import get_settings
from app.models import Channel, User


class PlaylistGenerator:
    """Service for generating M3U8 playlists."""

    def generate(self, user: User, channels: list[Channel]) -> str:
        """
        Generate M3U8 playlist content for a user.

        Format:
        #EXTM3U
        #EXTINF:-1 tvg-name="NAME" tvg-id="ID" catchup-days="N" group-title="GROUP" tvg-logo="LOGO",DISPLAY_NAME
        http://BASE_URL/STREAM_NAME/video.m3u8?token=USER_TOKEN
        """
        lines = ["#EXTM3U"]

        settings = get_settings()
        base_url = settings.flussonic_url.rstrip("/")

        for channel in channels:
            # Build EXTINF attributes
            attrs = []

            # tvg-name (EPG name)
            tvg_name = channel.tvg_name or channel.display_name or channel.stream_name
            attrs.append(f'tvg-name="{self._escape(tvg_name)}"')

            # tvg-id (EPG ID)
            if channel.tvg_id:
                attrs.append(f'tvg-id="{self._escape(channel.tvg_id)}"')

            # catchup-days (DVR)
            if channel.catchup_days:
                attrs.append(f'catchup-days="{channel.catchup_days}"')

            # group-title (comma-delimited groups by sort_order/name)
            if channel.groups:
                ordered_groups = sorted(
                    (grp for grp in channel.groups if grp.name),
                    key=lambda grp: (grp.sort_order, grp.name.lower()),
                )
                if ordered_groups:
                    group_title = ",".join(self._escape(grp.name) for grp in ordered_groups)
                    attrs.append(f'group-title="{group_title}"')

            # tvg-logo (base64 or URL)
            if channel.tvg_logo:
                attrs.append(f'tvg-logo="{channel.tvg_logo}"')

            # Display name for the channel
            display_name = channel.display_name or channel.tvg_name or channel.stream_name

            # Build EXTINF line
            extinf = f'#EXTINF:-1 {" ".join(attrs)},{display_name}'
            lines.append(extinf)

            # Build stream URL with token
            stream_url = f"{base_url}/{channel.stream_name}/video.m3u8?token={user.token}"
            lines.append(stream_url)

        return "\n".join(lines) + "\n"

    def get_filename(self, user: User) -> str:
        """
        Generate playlist filename for a user.

        Format: {last_name}_{first_name}_{agreement_number}.m3u8
        """
        # Sanitize names for filename
        last_name = self._sanitize_filename(user.last_name)
        first_name = self._sanitize_filename(user.first_name)
        agreement = self._sanitize_filename(user.agreement_number)

        return f"{last_name}_{first_name}_{agreement}.m3u8"

    def _escape(self, value: str) -> str:
        """Escape special characters in attribute values."""
        return value.replace('"', '\\"')

    def _sanitize_filename(self, value: str) -> str:
        """Sanitize string for use in filename."""
        # Replace common problematic characters
        sanitized = value.replace(" ", "_")
        sanitized = "".join(c for c in sanitized if c.isalnum() or c in "_-")
        return sanitized
