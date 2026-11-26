# RuTV Middleware

IPTV middleware for Flussonic and Nimble stream providers.

## Features

- Sync channels from Flussonic and Nimble (read-only cache)
- Organize channels into groups, packages, and tariffs
- Manage users with subscription-based channel access
- Manage Proxy Portal permissions and device limits from the user form
- Generate personalized M3U/M3U8 playlists with authentication tokens
- Track account sync status and retry failed Auth Service updates from the admin UI

## Technology Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.0, Pydantic 2.0
- **Database**: PostgreSQL 15+
- **Frontend**: React, Vite, TypeScript, Tailwind CSS, Radix UI

## Quick Start with Docker

1. Clone the repository:
```bash
git clone https://github.com/AntonSheinin/rutv-middleware.git
cd rutv-middleware
```

2. Create a `.env` file from the example:
```bash
cp .env.example .env
```

3. Edit `.env` with your configuration:
```env
SECRET_KEY=your-secure-secret-key
FLUSSONIC_URL=http://your-flussonic-server:8080
FLUSSONIC_USERNAME=admin
FLUSSONIC_PASSWORD=your-flussonic-password
AUTH_SERVICE_URL=http://your-auth-service:8090
AUTH_SERVICE_API_KEY=your-auth-service-api-key
EPG_SERVICE_URL=http://your-epg-service:8000
RUTV_SITE_URL=https://rutv.co.il
RUTV_STATS_TOKEN=your-rutv-stats-token
```

Add Nimble variables only when Nimble support should be enabled in that environment. Nimble sync and dashboard use WMSPanel API credentials plus the Nimble playback URL.

```env
WMSPANEL_API_URL=https://api.wmspanel.com
WMSPANEL_CLIENT_ID=your-wmspanel-client-id
WMSPANEL_API_KEY=your-wmspanel-api-key
WMSPANEL_SERVER_ID=your-nimble-server-id
NIMBLE_PLAYBACK_URL=http://your-nimble-server:8081
```

4. Start PostgreSQL and run database migrations.
```bash
docker compose up -d --wait postgres
docker compose run --rm --no-deps --build -T rutv-middleware alembic upgrade head
```

5. Start the application services.
```bash
docker compose up -d
```

6. Create an admin user.
```bash
docker compose exec rutv-middleware python scripts/create_admin.py
```

7. Access the application at http://localhost:8080

For remote agent access, see [MCP Server](#mcp-server).

`media/` contains local runtime files and is mounted into the container separately.
Provision it independently on each host, including `media/rutv-logo.png` for the UI
and channel logos under `media/logos/`. Git, Docker builds, and the deployment
workflow exclude this directory; deployments preserve the server's existing media.
`work/`, `tmp/`, and `temp/` are also local-only and excluded from Git and Docker builds.

## First deployment after the rename

Rename the GitHub repository to `AntonSheinin/rutv-middleware` and update local Git
remotes. Verify that the existing **Deploy** workflow can publish to the renamed
GHCR package. Back up the current Compose configuration and record the deployed
image before running the workflow.

The old and new API and MCP containers use the same host ports. For the first
cutover, run the following from `/home/anton/playlist_service` while the old Compose
file is still in place, then dispatch the existing **Deploy** workflow on `main`:

```bash
sudo docker compose stop playlist-service playlist-mcp-server
sudo docker compose rm -f playlist-service playlist-mcp-server
```

Keep the same server directory and Compose project so PostgreSQL continues using
its existing volume. The path `/home/anton/playlist_service` is also used by APK
publishing and device provisioning.

Check monitoring for the new `/health` service value and update standalone
MCP instances to the renamed environment variables before restarting them.
After deployment, verify an existing playlist and an authenticated MCP read.
Compare the PostgreSQL volume, Alembic revision, and record counts with the
pre-deploy snapshot.

## Development Setup

1. Install Python 3.12+ and uv:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

2. Install dependencies:
```bash
uv pip install -e ".[dev]"
```

3. Start PostgreSQL (or use Docker):
```bash
docker run -d --name playlist-postgres \
  -e POSTGRES_USER=playlist \
  -e POSTGRES_PASSWORD=playlist \
  -e POSTGRES_DB=playlist_service \
  -p 5432:5432 \
  postgres:15-alpine
```

4. Create `.env` file and configure database URL:
```bash
cp .env.example .env
# Edit .env with your settings
```

5. Run migrations:
```bash
alembic upgrade head
```

6. Create admin user:
```bash
python scripts/create_admin.py
```

7. Start the development server:
```bash
uvicorn app.main:app --reload
```

Run backend checks from the repository root:

```powershell
.\.venv\Scripts\uv.exe run python -m compileall app scripts tests
.\.venv\Scripts\uv.exe run python -m pytest
```

Run frontend checks from `frontend/`:

```powershell
npm.cmd run lint
npm.cmd run build
```

See the [changelog](CHANGELOG.md) for changes awaiting release.

## Project Structure

```
rutv-middleware/
|-- app/
|   |-- main.py                 # FastAPI application
|   |-- config.py               # Configuration settings
|   |-- dependencies.py         # FastAPI dependencies
|   |-- exceptions.py           # Custom exceptions
|   |-- models.py               # SQLAlchemy models
|   |-- schemas.py              # Pydantic schemas
|   |-- services/               # Business logic
|   |-- routes/                 # API endpoints
|   |-- clients/                # External API clients
|   |-- utils/                  # Utility functions
|   `-- mcp_server.py           # Remote MCP server
|-- frontend/                   # React admin UI
|-- alembic/                    # Database migrations
|-- scripts/                    # Utility scripts
|-- docker-compose.yml          # Docker Compose configuration
|-- Dockerfile                  # Docker image definition
`-- pyproject.toml              # Python project configuration
```

## API Documentation

Once running, API documentation is available at:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## User Portal Permission

`portal_allowed` stores Proxy Portal permission and defaults to `false` for
new users. The admin form has an **Allow portal access** checkbox. Staff can
edit **Max Portal Devices** only while access is allowed. The limit defaults to
`1` for new and existing users and must be a positive integer. Turning access
off preserves the saved limit. Changing the permission or the limit clears
Portal sync confirmation.

Admin user creation and updates accept `portal_allowed` and
`max_portal_devices`. On update, omitted fields keep their saved values.
Explicit `null` for `portal_allowed` returns HTTP 422. The device limit is
included in account detail and save responses.

Sort the admin list with `sort_by=portal_allowed` and `sort_dir=asc` (Denied first)
or `desc` (Allowed first). Equal values are ordered by user ID ascending. Changing
the table sort resets pagination to page 1.

### Account sync

The users table and account details show Auth sync status and show Portal sync
status when Portal is configured. **Synced** means the service acknowledged the
current saved settings. **Not synced** covers changes that have not been acknowledged.

Admin saves attempt Auth sync when a user is created or their effective playback
settings change. An Auth failure leaves the account saved with **Not synced** and
shows a warning. Profile-only edits skip Auth. Staff can retry saved settings with
**Sync Auth**, which calls `POST /api/v1/users/{user_id}/sync-auth`. Account
deletion completes only after Auth confirms token revocation.

Set `PORTAL_BASE_URL` and `PORTAL_API_KEY` together to enable Portal Proxy
integration, or leave both empty. `PORTAL_TIMEOUT` defaults to 15 seconds.
Middleware validates the base URL at startup and sends the key in the
`X-Internal-Api-Key` header. Use HTTPS for Portal connections. When Portal runs on
the Docker host, Compose maps `host.docker.internal` to the host gateway so
middleware can use `http://host.docker.internal:8092`. Compose passes the Portal
key only to middleware.

Account creation, edits to names, Portal settings or individual account
assignments, and confirmed token rotations sync directly to Portal. Shared
catalog edits have no automatic Portal sync. Suspension clears the stored Portal
playlist. Permanent deletion revokes Auth access and then removes the account
from Portal before deleting the local user. If Portal deletion fails, retry the
delete from the admin UI.

**Sync Portal** sends the latest saved snapshot for an enabled or suspended
account through `POST /api/v1/users/{user_id}/sync-portal`. If a Portal call fails
after an account save, the UI reports that the account was saved and sync failed.
The endpoint returns HTTP 503 when Portal is unconfigured.

Before enabling Portal in production, run `uv run python -m scripts.portal_sync --check-size`
from the middleware environment to check generated URLs and the 8 MiB request
size limit. Once configured, run `uv run python -m scripts.portal_sync` to backfill
existing accounts, including suspended accounts and accounts previously marked
synced by the mock. The command can be rerun. Use
`uv run python -m scripts.portal_sync --verify-account ACCOUNT_ID` to compare
stored Portal metadata with the middleware account.

Run `alembic upgrade head` before starting the updated backend. Migration
`008` adds the sync flags and initializes them to false. Migration `009` adds
the device limit and clears previous Portal confirmations. To reconcile existing
Auth records and update their flags, run
`uv run python scripts/auth_identity_maintenance.py --full-resync` once Auth
Service is reachable.

## Integration API

CRM and automation clients call the service-to-service API for urgent user support. Configure `INTEGRATION_API_KEY` and send it as `X-API-Key` on requests to `/api/v1/integrations/*`. The API uses `SuccessResponse` for successful calls and the standard error envelope for failures. Mutations identify users by `user_id`. Callers can use the agreement number to look up that ID.

Stage 1 endpoints:

- `GET /api/v1/integrations/users/find?q=...`
- `GET /api/v1/integrations/users/{user_id}`
- `POST /api/v1/integrations/users/{user_id}/enable`
- `POST /api/v1/integrations/users/{user_id}/disable`
- `PUT /api/v1/integrations/users/{user_id}/max-sessions`
- `PUT /api/v1/integrations/users/{user_id}/valid-until`
- `GET /api/v1/integrations/users/{user_id}/sessions`

User search is exact-only in stage 1. It matches agreement number, first name, last name, full name, or reversed full name. It is case-insensitive and trims leading/trailing whitespace, but it does not perform partial or fuzzy matching.

User detail and exact lookup responses include the `portal_allowed` Boolean
described in [User Portal Permission](#user-portal-permission). These compact
responses omit playlist tokens, Auth token IDs, package and channel assignments,
and admin-only metadata. The sessions endpoint returns current active sessions
as a single list without pagination or access history.

Proxy Portal reads and enforces this permission. Account status and validity
are managed separately. Permission and device-limit edits affect only Portal
sync state. This release provides the Portal mock for admin sync.

Examples:

```bash
curl -H "X-API-Key: $INTEGRATION_API_KEY" \
  "http://localhost:8080/api/v1/integrations/users/find?q=12345"
```

```bash
curl -H "X-API-Key: $INTEGRATION_API_KEY" \
  "http://localhost:8080/api/v1/integrations/users/10"
```

```bash
curl -X POST -H "X-API-Key: $INTEGRATION_API_KEY" \
  "http://localhost:8080/api/v1/integrations/users/10/disable"
```

```bash
curl -X PUT -H "X-API-Key: $INTEGRATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"max_sessions":2}' \
  "http://localhost:8080/api/v1/integrations/users/10/max-sessions"
```

```bash
curl -X PUT -H "X-API-Key: $INTEGRATION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"valid_until":"2026-12-31T23:59:59+02:00"}' \
  "http://localhost:8080/api/v1/integrations/users/10/valid-until"
```

```bash
curl -H "X-API-Key: $INTEGRATION_API_KEY" \
  "http://localhost:8080/api/v1/integrations/users/10/sessions"
```

Integration writes that affect playback access require Auth Service confirmation
before returning success. If sync fails, the endpoint rolls back the playback
change and returns an error. The admin UI shows the unconfirmed Auth status so
staff can retry from saved settings.

## MCP Server

The MCP server is a separate process for agent clients such as a Telegram bot. It serves the Streamable HTTP transport at `/mcp`. Every tool calls the Integration API over HTTP, which owns database access and business logic.

Standalone MCP process environment:

```env
RUTV_MIDDLEWARE_API_URL=http://localhost:8080
RUTV_MIDDLEWARE_API_KEY=your-integration-api-key
MCP_HOST=0.0.0.0
MCP_PORT=8091
MCP_AUTH_TOKEN=your-mcp-bearer-token
```

For Docker Compose, set `MCP_AUTH_TOKEN` and `INTEGRATION_API_KEY` in `.env`.
Compose passes `INTEGRATION_API_KEY` to the MCP container as `RUTV_MIDDLEWARE_API_KEY`.
The default Compose endpoint is `http://localhost:8091/mcp`.

Run it with:

```bash
python -m app.mcp_server
```

To start the MCP service with Docker Compose:

```bash
docker-compose up -d rutv-middleware-mcp
```

The MCP endpoint is:

```text
http://<MCP_HOST>:<MCP_PORT>/mcp
```

Remote MCP clients must send:

```text
Authorization: Bearer <MCP_AUTH_TOKEN>
```

Available tools:

- `find_user`
- `get_user`
- `enable_user`
- `disable_user`
- `set_user_max_sessions`
- `set_user_valid_until`
- `get_user_active_sessions`

## Key Workflows

### Channel Identity

A channel is identified by `(source, stream_name)`. The supported `source` values
are `flussonic` and `nimble`. When both providers have the same `stream_name`,
each provider has a separate assignable channel row. Package, tariff, and user
assignments refer to `channel.id`. Auth Service receives plain stream names in
`allowed_streams`, deduplicated by `stream_name` across providers.

The admin UI and API expose `source`. It appears in channel lists and details,
lookups, nested channels in package and user details, and resolved user channels.
Provider clients handle API calls, response parsing, health checks, and playback
URL construction. The Flussonic client uses the V3 API, and the Nimble client
uses the configured WMSPanel API.

### Channel Sync

The dashboard triggers `POST /api/v1/channels/sync` with either
`?source=flussonic` or `?source=nimble`. Each request syncs one provider. It
upserts channels by `(source, stream_name)` and marks missing channels from that
provider as orphaned.

| Refreshed from the provider | Preserved from the admin UI |
|----------|-------------|
| `tvg_name`, `display_name`, `catchup_days`, `sync_status`, `last_seen_at` | `tvg_id`, `tvg_logo`, `channel_number`, group assignments, package assignments |

### Dashboard

The dashboard shows aggregate stats and cards for Flussonic, Nimble, Auth, EPG,
and RUTV. Configured provider cards show health and provider stats. An
unavailable provider reports `down`. An unconfigured provider reports
`Not configured`, and the dashboard disables its sync action.

Provider stats are available at `GET /api/v1/dashboard/flussonic` and
`GET /api/v1/dashboard/nimble`.

### Playlist Generation

When an admin creates a user, the service generates a unique token and
registers it with Auth Service. The in-process `PlaylistService` resolves the
user's channel assignments for public delivery, admin downloads, and previews.
It builds each row's playback URL using that row's provider and embeds the user
token. If both provider variants are assigned, both appear in the playlist.

### Playlist URL Names

Each user has a saved `playlist_name`, initialized from the existing sanitized
`{last_name}_{first_name}_{agreement_number}` format. Personal-detail changes no
longer change this name. In user details, edit **Playlist URL name** and use the
existing Save action. The application adds `.m3u8` to URLs and download filenames.

Names must contain 1–302 characters, each satisfying Python `str.isalnum()` or
being an underscore or hyphen. Spaces, extensions, and path separators are
rejected, without trimming or rewriting input. Case is preserved. Uniqueness and
public lookup use PostgreSQL `lower()`, replacing the former Python `casefold()`
matching. Renaming immediately replaces the URL: update configured players;
the previous name returns 404 unless subsequently assigned to another user.
A name-only edit preserves the token and playback permissions and skips Auth sync.

The edit form submits only changed fields. Leaving a validity date unchanged
preserves its exact saved timestamp, including its time of day and fractional
seconds. Only changing or clearing that date updates the corresponding validity
boundary. After a successful save, the displayed playlist URL uses the returned
saved name immediately, even if a background refresh fails. Unsaved or rejected
edits leave the saved URL in place.

Admin user details include `playlist_name`. On `PATCH /api/v1/users/{user_id}`,
omission preserves the name; null or invalid input returns 422, and a conflicting
name returns 409. Generated names also must be unique: creation fails with 409
on collision rather than inventing a suffix. Integration API responses and MCP
tools remain unchanged.

Migration `007` adds the required column and a unique index on
`lower(playlist_name)`, preserving existing generated filenames exactly. Use a
maintenance window: stop application writers, run `uv run alembic upgrade head`,
deploy the matching application, verify playlist delivery, and resume traffic.
The migration reports conflicting user IDs/names and rolls back on PostgreSQL;
resolve reported conflicts deliberately before retrying. Do not run the old
application against the migrated schema: it does not populate the required field.
Reverting to the old application after renames breaks custom URLs; downgrading
the schema discards saved names. Take a database backup before deployment.

Optional PostgreSQL tests use a disposable server and create/drop isolated schemas:

```powershell
$env:PLAYLIST_TEST_POSTGRES_URL = 'postgresql+asyncpg://postgres@127.0.0.1:55439/postgres'
.\.venv\Scripts\uv.exe run python -m pytest tests/test_playlist_postgres.py
```

## Environment Variables

Each stream provider can be configured independently.

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SECRET_KEY` | Secret key for sessions | Required |
| `INTEGRATION_API_KEY` | API key accepted by `/api/v1/integrations/*` via `X-API-Key` | Optional unless Integration API is used |
| `FLUSSONIC_URL` | Flussonic API base URL | Optional |
| `FLUSSONIC_USERNAME` | Flussonic API username | Optional |
| `FLUSSONIC_PASSWORD` | Flussonic API password | Optional |
| `FLUSSONIC_TIMEOUT` | Flussonic API request timeout in seconds | `60` |
| `FLUSSONIC_PAGE_LIMIT` | Flussonic API items per page | `500` |
| `WMSPANEL_API_URL` | WMSPanel API base URL | Optional |
| `WMSPANEL_CLIENT_ID` | WMSPanel API client ID | Optional |
| `WMSPANEL_API_KEY` | WMSPanel API key | Optional |
| `WMSPANEL_SERVER_ID` | WMSPanel server ID for the Nimble instance | Optional |
| `NIMBLE_TIMEOUT` | WMSPanel API request timeout in seconds | `30` |
| `NIMBLE_PLAYBACK_URL` | Nimble playback base URL | Optional |
| `NIMBLE_APPLICATION` | Nimble application name used for playback/stat filtering | `live` |
| `NIMBLE_PLAYLIST_PATH` | Playlist path appended to the Nimble stream URL | `playlist.m3u8` |
| `NIMBLE_TOKEN_QUERY_PARAM` | Query parameter for the Nimble playback token | `token` |
| `AUTH_SERVICE_URL` | Auth Service base URL | Required |
| `AUTH_SERVICE_API_KEY` | Auth Service API key | Required |
| `PORTAL_BASE_URL` | RuTV Portal Proxy base URL, with HTTP allowed on `host.docker.internal` | Unset |
| `PORTAL_API_KEY` | Secret sent in the `X-Internal-Api-Key` header | Unset |
| `PORTAL_TIMEOUT` | Portal request timeout in seconds | `15` |
| `EPG_SERVICE_URL` | EPG Service base URL | Required |
| `RUTV_SITE_URL` | RUTV site base URL | Required |
| `RUTV_STATS_TOKEN` | RUTV stats token sent in `X-Stats-Token` | Required |
| `BASE_URL` | Public RuTV Middleware base URL, including port when needed | Required |
| `RUTV_MIDDLEWARE_API_URL` | RuTV Middleware base URL used by the MCP server | http://127.0.0.1:8080 |
| `RUTV_MIDDLEWARE_API_KEY` | Integration API key used by the MCP server outside Docker Compose | Defaults to `${INTEGRATION_API_KEY}` in Compose |
| `MCP_HOST` | MCP server bind address | 127.0.0.1 |
| `MCP_PORT` | MCP server port | 8091 |
| `MCP_AUTH_TOKEN` | Bearer token required by remote MCP clients | Required for MCP |

## License

MIT
