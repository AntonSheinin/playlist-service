# Playlist Service

IPTV Playlist Service for Flussonic Media Server.

## Features

- Sync channels from Flussonic (read-only cache)
- Organize channels into groups, packages, and tariffs
- Manage users with subscription-based channel access
- Generate personalized M3U/M3U8 playlists with authentication tokens
- Synchronize user tokens with an external Auth Service

## Technology Stack

- **Backend**: Python 3.12+, FastAPI, SQLAlchemy 2.0, Pydantic 2.0
- **Database**: PostgreSQL 15+
- **Frontend**: Jinja2, HTMX, Tailwind CSS

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
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Configuration settings
│   ├── dependencies.py         # FastAPI dependencies
│   ├── exceptions.py           # Custom exceptions
│   ├── models/                 # SQLAlchemy models
│   ├── schemas/                # Pydantic schemas
│   ├── services/               # Business logic
│   ├── routes/                 # API endpoints
│   ├── clients/                # External API clients
│   ├── templates/              # Jinja2 templates
│   ├── static/                 # Static files
│   └── utils/                  # Utility functions
├── alembic/                    # Database migrations
├── scripts/                    # Utility scripts
├── docker-compose.yml          # Docker Compose configuration
├── Dockerfile                  # Docker image definition
└── pyproject.toml              # Python project configuration
```

## API Documentation

Once running, API documentation is available at:
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## Key Workflows

### Channel Sync
1. Admin clicks "Sync from Flussonic" in the dashboard
2. Service fetches channel list from Flussonic API
3. New channels are added, existing channels updated
4. Channels missing from Flussonic are marked as "orphaned"

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
| `FLUSSONIC_URL` | Flussonic API base URL | Required |
| `FLUSSONIC_USERNAME` | Flussonic API username | admin |
| `FLUSSONIC_PASSWORD` | Flussonic API password | Required |
| `AUTH_SERVICE_URL` | Auth Service base URL | Required |
| `AUTH_SERVICE_API_KEY` | Auth Service API key | Required |
| `API_HOST` | Server bind address | 0.0.0.0 |
| `API_PORT` | Server port | 8080 |

## License

MIT
