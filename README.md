# RuTV Middleware

IPTV middleware for Flussonic and Nimble stream providers.

## Features

- Sync channels from Flussonic and Nimble (read-only cache)
- Organize channels into groups, packages, and tariffs
- Manage users with subscription-based channel access
- Manage Propy portal permissions from the user form and sort users by portal access
- Generate personalized M3U/M3U8 playlists with authentication tokens
- Synchronize user tokens with an external Auth Service

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

4. Start the services:
```bash
docker-compose up -d
```

5. Run database migrations:
```bash
docker-compose exec rutv-middleware alembic upgrade head
```

6. Create an admin user:
```bash
docker-compose exec -it rutv-middleware python scripts/create_admin.py
```

7. Access the application at http://localhost:8080

The Docker Compose stack also starts the remote MCP server at http://localhost:8091/mcp when `MCP_AUTH_TOKEN` and `INTEGRATION_API_KEY` are configured in `.env`. Compose passes `INTEGRATION_API_KEY` to the MCP container as `RUTV_MIDDLEWARE_API_KEY`.

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
.\.venv\Scripts\uv.exe run pytest
```

Run frontend checks from `frontend/`:

```powershell
npm.cmd run lint
npm.cmd run build
```

See the [service specification](rutv-middleware-specification.md) and
[changelog](CHANGELOG.md) for the service contracts and changes awaiting release.

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

`portal_allowed` is a stored Boolean that indicates whether a user is allowed to
connect to the Propy portal. New users default to `false`. The admin create/edit
form includes an **Allow portal access** checkbox, and the users table shows
**Allowed / Denied** in a sortable **Portal allowed** column.

The existing admin endpoints accept the field:

- `POST /api/v1/users`: omission defaults to `false`.
- `PATCH /api/v1/users/{user_id}`: omission preserves the value; `true` grants
  permission and `false` revokes it. Explicit `null` is rejected.
- User list, detail, create, and update responses include the Boolean.

Sort the admin list with `sort_by=portal_allowed` and `sort_dir=asc` (Denied first)
or `desc` (Allowed first). Equal values are ordered by user ID ascending. Changing
the table sort resets pagination to page 1.

Apply Alembic migration `006` before deploying the updated backend and UI. It adds
the non-nullable column, sets all existing users to `false`, and retains a database
default of `false` for future inserts. The downgrade removes the column and its
permission values.

## Integration API

RuTV Middleware exposes a narrow service-to-service API for urgent user support actions. CRM, automation, and other non-agent systems call this API directly. Configure `INTEGRATION_API_KEY` and send it as `X-API-Key` on requests to `/api/v1/integrations/*`.

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
described in [User Portal Permission](#user-portal-permission).

Propy must read and enforce this permission. Account status and validity do not change
the flag; any additional status or expiry checks are Propy's responsibility. Changing
only this flag does not synchronize Auth Service or alter playback access. This change
does not implement Propy connection checks, caching, or session revocation.

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

Integration writes that affect playback access strictly sync the Auth Service before returning success. If Auth Service sync fails, the local database change is rolled back and the endpoint returns an error. Telegram agents should format datetime values for human display.

## MCP Server

The MCP server is a separate remote HTTP process for agent clients, such as a Telegram bot agent. It calls the Integration API and does not access the database directly.

Standalone MCP process environment:

```env
RUTV_MIDDLEWARE_API_URL=http://localhost:8080
RUTV_MIDDLEWARE_API_KEY=your-integration-api-key
MCP_HOST=0.0.0.0
MCP_PORT=8091
MCP_AUTH_TOKEN=your-mcp-bearer-token
```

When using Docker Compose, set only `INTEGRATION_API_KEY`; Compose injects it into the MCP container as `RUTV_MIDDLEWARE_API_KEY`.

Run it with:

```bash
python -m app.mcp_server
```

With Docker Compose, it runs as the `playlist-mcp-server` service:

```bash
docker-compose up -d playlist-mcp-server
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

### Channel Sync
1. Admin triggers sync for Flussonic or Nimble in the dashboard
2. Service fetches channel list from the selected provider API
3. New channels are added, existing channels updated
4. Channels missing from that provider are marked as "orphaned"

### Playlist Generation
1. Admin creates a user with tariffs/packages/channels
2. Service generates a unique token
3. Service registers the token with Auth Service
4. Admin downloads the playlist file
5. Playlist contains all resolved channels with embedded token

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
Tokens and playback permissions are unaffected by name-only edits.

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
.\.venv\Scripts\uv.exe run pytest tests/test_playlist_postgres.py
```

Playlist rendering remains in-process. `PlaylistService` coordinates the three
delivery/preview endpoints and reuses the existing channel-resolution rules.

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | Required |
| `SECRET_KEY` | Secret key for sessions | Required |
| `INTEGRATION_API_KEY` | API key accepted by `/api/v1/integrations/*` via `X-API-Key` | Optional unless Integration API is used |
| `FLUSSONIC_URL` | Flussonic API base URL | Optional |
| `FLUSSONIC_USERNAME` | Flussonic API username | Optional |
| `FLUSSONIC_PASSWORD` | Flussonic API password | Optional |
| `WMSPANEL_API_URL` | WMSPanel API base URL | Optional |
| `WMSPANEL_CLIENT_ID` | WMSPanel API client ID | Optional |
| `WMSPANEL_API_KEY` | WMSPanel API key | Optional |
| `WMSPANEL_SERVER_ID` | WMSPanel server ID for the Nimble instance | Optional |
| `NIMBLE_PLAYBACK_URL` | Nimble playback base URL | Optional |
| `NIMBLE_APPLICATION` | Nimble application name used for playback/stat filtering | `live` |
| `AUTH_SERVICE_URL` | Auth Service base URL | Required |
| `AUTH_SERVICE_API_KEY` | Auth Service API key | Required |
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
