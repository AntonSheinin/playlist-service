# Playlist Service

IPTV Playlist Service for Flussonic and Nimble stream providers.

## Features

- Sync channels from Flussonic and Nimble (read-only cache)
- Organize channels into groups, packages, and tariffs
- Manage users with subscription-based channel access
- Generate personalized M3U/M3U8 playlists with authentication tokens
- Synchronize user tokens with an external Auth Service

## Technology Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.0, Pydantic 2.0
- **Database**: PostgreSQL 15+
- **Frontend**: React, Vite, TypeScript, Material UI

## Quick Start with Docker

1. Clone the repository:
```bash
git clone https://github.com/AntonSheinin/playlist-service.git
cd playlist-service
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
docker-compose exec playlist-service alembic upgrade head
```

6. Create an admin user:
```bash
docker-compose exec -it playlist-service python scripts/create_admin.py
```

7. Access the application at http://localhost:8080

The Docker Compose stack also starts the remote MCP server at http://localhost:8091/mcp when `MCP_AUTH_TOKEN` and `INTEGRATION_API_KEY` are configured in `.env`. Compose passes `INTEGRATION_API_KEY` to the MCP container as `PLAYLIST_SERVICE_API_KEY`.

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

## Project Structure

```
playlist-service/
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

## Integration API

Playlist Service exposes a narrow service-to-service API for urgent user support actions. CRM, automation, and other non-agent systems call this API directly. Configure `INTEGRATION_API_KEY` and send it as `X-API-Key` on requests to `/api/v1/integrations/*`.

Stage 1 endpoints:

- `GET /api/v1/integrations/users/find?q=...`
- `GET /api/v1/integrations/users/{user_id}`
- `POST /api/v1/integrations/users/{user_id}/enable`
- `POST /api/v1/integrations/users/{user_id}/disable`
- `PUT /api/v1/integrations/users/{user_id}/max-sessions`
- `PUT /api/v1/integrations/users/{user_id}/valid-until`
- `GET /api/v1/integrations/users/{user_id}/sessions`

User search is exact-only in stage 1. It matches agreement number, first name, last name, full name, or reversed full name. It is case-insensitive and trims leading/trailing whitespace, but it does not perform partial or fuzzy matching.

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
PLAYLIST_SERVICE_API_URL=http://localhost:8080
PLAYLIST_SERVICE_API_KEY=your-integration-api-key
MCP_HOST=0.0.0.0
MCP_PORT=8091
MCP_AUTH_TOKEN=your-mcp-bearer-token
```

When using Docker Compose, set only `INTEGRATION_API_KEY`; Compose injects it into the MCP container as `PLAYLIST_SERVICE_API_KEY`.

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
| `BASE_URL` | Public Playlist Service base URL, including port when needed | Required |
| `PLAYLIST_SERVICE_API_URL` | Playlist Service base URL used by the MCP server | http://127.0.0.1:8080 |
| `PLAYLIST_SERVICE_API_KEY` | Integration API key used by the MCP server outside Docker Compose | Defaults to `${INTEGRATION_API_KEY}` in Compose |
| `MCP_HOST` | MCP server bind address | 127.0.0.1 |
| `MCP_PORT` | MCP server port | 8091 |
| `MCP_AUTH_TOKEN` | Bearer token required by remote MCP clients | Required for MCP |

## License

MIT
