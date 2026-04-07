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

## Implementation Notes

- Flussonic support is pinned to the V3 contract used by the current client implementation
- Legacy Flussonic endpoint fallbacks and old single-provider assumptions are not part of the current design
- The README is the operational setup reference for environment variables and local startup
