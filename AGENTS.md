# AGENTS.md

Guidance for AI coding agents working in this repository.

## Project Overview

Playlist Service is a FastAPI backend with a React/Vite admin UI. It manages IPTV channels, packages, tariffs, users, playlist generation, and synchronization with external Auth, EPG, RUTV, Flussonic, and Nimble services.

## Repository Layout

- `app/`: FastAPI application code.
- `app/routes/`: HTTP route handlers. Keep these thin: validate/request orchestration only.
- `app/services/`: business workflows and persistence-oriented logic.
- `app/clients/`: external service clients and provider integrations.
- `app/models.py`: SQLAlchemy models and association tables.
- `app/schemas.py`: Pydantic API schemas.
- `alembic/`: database migrations.
- `frontend/`: React/Vite/TypeScript admin UI.
- `tests/`: backend tests.

## Development Commands

Use these checks before finishing backend changes:

```powershell
.\.venv\Scripts\uv.exe run python -m compileall app scripts tests
.\.venv\Scripts\uv.exe run pytest
```

Use these checks before finishing frontend changes:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
```

Use `npm.cmd` on Windows PowerShell if `npm.ps1` is blocked by execution policy.

## Code Principles

All new or changed code should follow clean code practices and the SOLID, KISS, and YAGNI principles:

- Keep functions small and focused on one responsibility.
- Prefer explicit, readable code over generic abstractions.
- Add abstractions only when they remove real duplication or clarify ownership.
- Avoid one-line helpers that obscure simple logic.
- Do not add speculative options, fallbacks, configuration, or compatibility paths.
- Preserve existing API contracts unless the task explicitly requires a breaking change.
- Keep error handling intentional and close to the boundary that can recover from it.
- Use type hints and Pydantic/SQLAlchemy typed APIs consistently.

## Backend Guidelines

- Keep route handlers thin; move reusable workflow logic to services.
- Keep external HTTP details inside `app/clients/`.
- Do not add legacy provider fallbacks. Flussonic support is V3-only; Nimble support is through the configured WMSPanel contract.
- Preserve provider values: `flussonic` and `nimble`.
- Preserve response envelopes: `SuccessResponse`, `MessageResponse`, and `PaginatedResponse`.
- Do not add Alembic migrations unless the database schema changes. If adding one, make the reason explicit.
- Prefer set-based SQL over per-row query loops for relationship resolution.
- Keep Auth Service recovery behavior intact unless explicitly asked to change it.

## Frontend Guidelines

- Keep frontend API helpers aligned with backend response envelopes.
- Update `frontend/src/api/types.ts` when backend response schemas change.
- Do not add a frontend test framework unless explicitly requested.
- Prefer existing React Query, Material UI, and local component patterns.

## Testing Guidelines

- Add focused tests for changed behavior, not exhaustive duplicate route tests.
- Prefer unit tests for extracted pure logic and small API compatibility tests for response shape.
- Mock external services; tests should not require Flussonic, Nimble, Auth, EPG, or RUTV network access.
- Avoid testing framework or library behavior that FastAPI, Pydantic, SQLAlchemy, or React already owns.

## Safety Rules

- Do not edit `.env` unless explicitly asked.
- Do not commit secrets, tokens, generated build output, or local caches.
- Do not revert user changes unless explicitly asked.
- Keep public URLs, cookie names, request payloads, and response field names stable by default.
