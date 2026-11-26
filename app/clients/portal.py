import json
from typing import Literal

import httpx
from httpx import AsyncClient
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError, model_validator

from app.config import get_settings
from app.exceptions import PortalSyncError, PortalUnavailableError

MAX_PORTAL_BODY_BYTES = 8 * 1024 * 1024


class PortalAccount(BaseModel):
    model_config = ConfigDict(strict=True)

    account_id: int = Field(gt=0, le=9_223_372_036_854_775_807)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    portal_allowed: bool
    max_portal_devices: int = Field(ge=1, le=2_147_483_647)


class PortalSnapshot(PortalAccount):
    playlist_m3u: str | None = Field(repr=False)

    @model_validator(mode="after")
    def check_playlist(self) -> "PortalSnapshot":
        if self.portal_allowed and self.playlist_m3u is None:
            raise ValueError("An enabled Portal account requires a playlist")
        return self


class PortalAccountMetadata(PortalAccount):
    created_at: AwareDatetime
    updated_at: AwareDatetime


def encode_snapshot(snapshot: PortalSnapshot) -> bytes:
    body = json.dumps(snapshot.model_dump(), ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(body) > MAX_PORTAL_BODY_BYTES:
        raise PortalSyncError("Portal snapshot exceeds the 8 MiB request limit")
    return body


class PortalClient:
    async def upsert(self, snapshot: PortalSnapshot) -> PortalAccountMetadata:
        response = await self._request(
            "POST", "/internal/accounts/upsert", {200}, body=encode_snapshot(snapshot)
        )
        metadata = self._metadata(response)
        account_fields = set(PortalAccount.model_fields)
        if metadata.model_dump(include=account_fields) != snapshot.model_dump(include=account_fields):
            raise PortalSyncError("Portal acknowledged different account metadata")
        return metadata

    async def get(self, account_id: int) -> PortalAccountMetadata | None:
        response = await self._request("GET", f"/internal/accounts/{account_id}", {200, 404})
        if response.status_code == 404:
            return None
        metadata = self._metadata(response)
        if metadata.account_id != account_id:
            raise PortalSyncError("Portal returned a different account ID")
        return metadata

    async def delete(self, account_id: int) -> None:
        await self._request("DELETE", f"/internal/accounts/{account_id}", {204})

    async def _request(
        self,
        method: Literal["POST", "GET", "DELETE"],
        path: str,
        expected_statuses: set[int],
        *,
        body: bytes | None = None,
    ) -> httpx.Response:
        settings = get_settings()
        if not settings.portal_configured:
            raise PortalUnavailableError()

        try:
            base_url = httpx.URL(settings.portal_base_url)
            headers = {"X-Internal-Api-Key": settings.portal_api_key.get_secret_value()}
            if body is not None:
                headers["Content-Type"] = "application/json"
            async with AsyncClient(
                base_url=base_url, headers=headers, timeout=settings.portal_timeout, trust_env=base_url.scheme == "https"
            ) as client:
                response = await client.request(method, path, content=body)
        except (httpx.HTTPError, httpx.InvalidURL, UnicodeError):
            raise PortalSyncError("Portal request failed. Retry with the current account data.") from None

        if response.status_code not in expected_statuses:
            raise PortalSyncError(f"Portal returned HTTP {response.status_code}")
        return response

    @staticmethod
    def _metadata(response: httpx.Response) -> PortalAccountMetadata:
        try:
            return PortalAccountMetadata.model_validate_json(response.content)
        except ValidationError:
            raise PortalSyncError("Portal returned invalid account metadata") from None
