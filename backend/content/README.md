# Content service (IntelliHire API)

The FastAPI backend. Module 1 (authentication and account management) is implemented; see
`docs/learning/01-backend-foundations-and-auth-module.md` at the repo root for a guided tour.

## Structure

```
backend/content/
├── app/
│   ├── main.py            FastAPI app factory: routers, CORS, error handler, startup
│   ├── core/              settings, security (bcrypt/JWT), dependencies (auth/RBAC), rate limit, errors
│   ├── database/          engine/session and SQLAlchemy models (one file per table)
│   ├── schemas/           Pydantic request/response models
│   ├── services/          business rules (auth, profile, email, file storage)
│   └── controller/        routers: /auth, /users, /company, /admin
├── alembic/               database migrations
├── scripts/create_admin.py
├── tests/                 pytest suite, one file per user story
├── asgi.py                local dev server (auto-reload)
├── requirements.txt
└── Dockerfile, docker-entrypoint.sh
```

Request flow: controller -> service -> models. Controllers never contain business rules; services never touch HTTP.

## Local development (Windows PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env                    # edit if needed
docker compose up -d postgres                  # run from the repo root; listens on host port 5434
.\.venv\Scripts\alembic.exe upgrade head       # create/upgrade tables
.\.venv\Scripts\python.exe asgi.py             # http://localhost:8000/docs
```

Create the first platform administrator:

```powershell
.\.venv\Scripts\python.exe -m scripts.create_admin --email admin@intellihire.com --password "Admin@12345"
```

Without Docker, set `DATABASE_URL=sqlite:///./dev.db` in `.env`; migrations and the app work on SQLite too.

## Tests

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Tests use a throw-away SQLite file per test, an in-memory email outbox and fast bcrypt, so they
need no database server and finish in a few seconds.

## Migrations

```powershell
.\.venv\Scripts\alembic.exe revision --autogenerate -m "describe the change"   # after editing models
.\.venv\Scripts\alembic.exe upgrade head
.\.venv\Scripts\alembic.exe downgrade -1
```

## Endpoints (all under `/api/v1`)

| Method | Path | Story |
|---|---|---|
| POST | /auth/register/individual | US-1.1 |
| POST, GET | /auth/verify-email | US-1.2 |
| POST | /auth/resend-verification | US-1.2 |
| POST | /auth/register/company | US-1.3 |
| POST | /auth/login | US-1.4 |
| POST | /auth/logout | US-1.5 |
| POST | /auth/forgot-password, /auth/reset-password | US-1.6 |
| GET | /users/me | US-1.4 |
| GET, PUT | /users/me/profile | US-1.7 |
| POST, GET, DELETE | /users/me/cv | US-1.7 |
| GET | /company/me/status, /company/me | US-1.3 / US-3.6 |
| GET | /admin/overview, /admin/companies/pending | US-1.8 |
| POST | /admin/companies/{id}/approve, /reject | US-12.4 |

Interactive docs: `/docs` (Swagger UI) and `/redoc`. Health check: `/health`.

## Configuration

Every setting is listed with a comment in `.env.example` and typed in `app/core/config.py`.
Environment variables override `.env`. Generate a production `SECRET_KEY` with
`python -c "import secrets; print(secrets.token_urlsafe(48))"`.
