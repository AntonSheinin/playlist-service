# Playlist Service Specification

## Summary

Playlist Service is an admin application for managing IPTV channel catalogs, channel assignments, user access, and generated playlists across multiple stream providers.

The current implementation supports two explicit providers:

- `flussonic`
- `nimble`

The application layer is provider-agnostic. Provider-specific API calls, parsing, health checks, and playback URL construction are isolated in infrastructure clients.

## Core Domain Rules

- A channel is identified by the composite key `(source, stream_name)`.
- `source` is part of channel identity and is exposed in admin APIs and UI.
- Provider variants are separate assignable channels. If the same `stream_name` exists in Flussonic and Nimble, they are two distinct channel rows.
- Package, tariff, and user assignments continue to reference concrete `channel.id` rows.
- Auth synchronization remains logical-stream-based:
  - Auth Service still receives plain `stream_name` values in `allowed_streams`
  - duplicate provider variants are deduplicated by `stream_name` before sync
- Playlist generation remains row-based:
  - if both provider variants are assigned, both entries appear in the playlist

## Channel Sync

Sync is provider-scoped.

- Endpoint: `POST /api/v1/channels/sync?source=flussonic|nimble`
- There is no combined sync-all mode
- Sync upserts by `(source, stream_name)`
- Orphaning applies only within the synced provider
- Provider-managed fields are refreshed from the selected provider
- UI-managed fields are preserved

Provider-managed fields:

- `tvg_name`
- `display_name`
- `catchup_days`
- `sync_status`
- `last_seen_at`

UI-managed fields:

- `tvg_id`
- `tvg_logo`
- `channel_number`
- group assignments
- package assignments

## Playlist Generation

Playlists are generated from resolved user channels.

- The playlist structure and token embedding behavior remain unchanged
- Each channel row uses its own provider to build the playback URL
- Public playlist routes and preview routes remain unchanged

## Dashboard Behavior

The dashboard contains:

- aggregate global stats
- a Flussonic provider card
- a Nimble provider card
- Auth, EPG, and RUTV cards

Provider cards behave as follows:

- configured provider: show health and provider stats
- unavailable provider: show `down`
- provider not configured in the current environment: show `Not configured`

## API Notes

Channel-facing payloads include `source` in:

- channel list/detail
- lookup responses
- package detail nested channels
- user detail nested channels
- resolved user channels

Dashboard provider endpoints:

- `GET /api/v1/dashboard/flussonic`
- `GET /api/v1/dashboard/nimble`

## Integration API

The Integration API is a service-to-service contract for CRM, automation, and agent adapters. It is separate from the browser admin API.

- Base path: `/api/v1/integrations`
- Authentication: `X-API-Key: <INTEGRATION_API_KEY>`
- Response envelopes continue to use `SuccessResponse` and the existing error envelope
- Stage 1 scope is urgent user support only
- Mutating actions use stable `user_id`; agreement number is searchable data, not the mutation identity

Stage 1 endpoints:

- `GET /api/v1/integrations/users/find?q=...`
- `GET /api/v1/integrations/users/{user_id}`
- `POST /api/v1/integrations/users/{user_id}/enable`
- `POST /api/v1/integrations/users/{user_id}/disable`
- `PUT /api/v1/integrations/users/{user_id}/max-sessions`
- `PUT /api/v1/integrations/users/{user_id}/valid-until`
- `GET /api/v1/integrations/users/{user_id}/sessions`

User lookup is exact-only in stage 1:

- exact `agreement_number`
- exact `first_name`
- exact `last_name`
- exact full name as `first_name last_name`
- exact reversed full name as `last_name first_name`

Matching is case-insensitive and trims leading/trailing whitespace. It is intentionally not partial or fuzzy.

Integration user responses are compact and intentionally exclude playlist tokens, Auth token IDs, package/channel relationship details, and admin-only metadata.

Auth-relevant Integration API writes are strict:

- enable user
- disable user
- set `max_sessions`
- set `valid_until`

These writes must sync Auth Service before returning success. If Auth Service sync fails, the local database change must roll back and the endpoint must return an error.

Active sessions are returned as the current active-session list only. Stage 1 does not include historical access logs or pagination for this endpoint.

## MCP Server

The MCP server is a separate remote HTTP process and is not part of the FastAPI admin application.

- Entry point: `python -m app.mcp_server`
- Docker Compose service: `playlist-mcp-server`
- MCP transport: Streamable HTTP at `/mcp`
- MCP authentication: `Authorization: Bearer <MCP_AUTH_TOKEN>`
- Playlist Service authentication: MCP server calls the Integration API with `X-API-Key: <PLAYLIST_SERVICE_API_KEY>`. Docker Compose derives this from `INTEGRATION_API_KEY`.
- MCP tools must call Integration API endpoints over HTTP and must not access SQLAlchemy models, sessions, or services directly

Stage 1 tools:

- `find_user`
- `get_user`
- `enable_user`
- `disable_user`
- `set_user_max_sessions`
- `set_user_valid_until`
- `get_user_active_sessions`

## Configuration

Provider configuration is optional per provider.

Flussonic settings:

- `FLUSSONIC_URL`
- `FLUSSONIC_USERNAME`
- `FLUSSONIC_PASSWORD`
- `FLUSSONIC_TIMEOUT`
- `FLUSSONIC_PAGE_LIMIT`

Nimble settings:

- `WMSPANEL_API_URL`
- `WMSPANEL_CLIENT_ID`
- `WMSPANEL_API_KEY`
- `WMSPANEL_SERVER_ID`
- `NIMBLE_TIMEOUT`
- `NIMBLE_PLAYBACK_URL`
- `NIMBLE_APPLICATION`
- `NIMBLE_PLAYLIST_PATH`
- `NIMBLE_TOKEN_QUERY_PARAM`

If a provider is not configured, its dashboard card reports `Not configured` and its sync action is disabled in the UI.

Integration API settings:

- `INTEGRATION_API_KEY`

MCP server settings:

- `PLAYLIST_SERVICE_API_URL`
- `PLAYLIST_SERVICE_API_KEY` outside Docker Compose; Compose sets it from `INTEGRATION_API_KEY`
- `MCP_HOST`
- `MCP_PORT`
- `MCP_AUTH_TOKEN`

## Implementation Notes

- Flussonic support is pinned to the V3 contract used by the current client implementation
- Legacy Flussonic endpoint fallbacks and old single-provider assumptions are not part of the current design
- Integration API writes use strict Auth Sync while admin UI behavior keeps the existing recovery-tolerant sync behavior unless explicitly changed
- The MCP server is an adapter over the Integration API, not a second backend implementation
- The README is the operational setup reference for environment variables and local startup
