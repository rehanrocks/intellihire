# IntelliHire

AI-powered recruitment, interview and talent-community platform (COMSATS Lahore FYP).
Backend: FastAPI + PostgreSQL (pgvector), containerised with Docker.

Specification: the FYP report and the derived user-stories document (`docs/IntelliHire-User-Stories.docx`).
Learning guide for the backend: `docs/learning/01-backend-foundations-and-auth-module.md`.

## Prerequisites

- Docker Desktop (with Compose)
- Python 3.12+ (only for running the API outside Docker)
- Git

## Quick start (everything in Docker)

```powershell
git clone <repository-url>
cd intellihire
docker compose up -d --build
```

Services:

| Service | What | URL |
|---|---|---|
| postgres | PostgreSQL 15 with the pgvector extension available (`ankane/pgvector` image) | localhost:5434 (host port = `POSTGRES_PORT` in `.env`) |
| content | FastAPI API; runs `alembic upgrade head` on start | http://localhost:4010/docs |
| adminer | Database browser | http://localhost:8080 (server `postgres`, user/password `postgres`, db `intellihire`) |

Create the first platform administrator inside the running API container:

```powershell
docker compose exec content python -m scripts.create_admin --email admin@intellihire.com --password "Admin@12345"
```

## Developing the API locally

See `backend/content/README.md`. Short version: start only PostgreSQL with
`docker compose up -d postgres`, then run the API from a virtual environment with auto-reload.

## Environment variables

`.env` at the repo root configures ports and credentials for docker-compose. Important keys:

| Key | Purpose |
|---|---|
| `POSTGRES_PORT` | Host port for PostgreSQL (5434 by default to avoid clashing with a local PostgreSQL on 5432) |
| `POSTGRES_DB`, `POSTGRES_USERNAME`, `POSTGRES_PASSWORD` | Database name and credentials |
| `CONTENT_PORT` | Host port for the API |
| `SECRET_KEY` | Signs login tokens; change it for any real deployment |
| `FRONTEND_URL` | Base URL used in emailed links |
| `EMAIL_BACKEND` | `console` (print emails to logs), `smtp`, or `memory` (tests) |

The API service reads its own settings from these (see `docker-compose.yml`) and, when run
locally, from `backend/content/.env` (copy of `.env.example`).

## Stopping

```powershell
docker compose down        # stop containers
docker compose down -v     # also remove volumes
```

Database files persist in `backend/db_data/` and uploaded CVs in `backend/uploads/`; both are git-ignored.

## Project status

| Module | Status |
|---|---|
| 1. Authentication and account management | Implemented, 66 automated tests |
| 2 to 12 | Planned; see the user-stories document for the backlog |
