# Backend from zero: foundations and the IntelliHire authentication module

This guide is written for someone who has never built a backend. It explains what a backend is, how the IntelliHire authentication module (Module 1 of the user stories) is built in FastAPI, and why each file exists. Read it top to bottom once, then keep it open while you read the code.

---

## 1. What a backend is

Think of a restaurant.

| Restaurant | Software | In this project |
|---|---|---|
| Dining room, menu, waiter | **Frontend**: what the user sees and clicks | React app (not in this repo yet) |
| Kitchen | **Backend**: receives orders, applies the rules, prepares results | FastAPI app in `backend/content` |
| Pantry and fridge | **Database**: where data is kept safely between visits | PostgreSQL |
| Order ticket | **HTTP request**: "I want X, here are the details" | `POST /api/v1/auth/login` with a JSON body |
| Plate that comes back | **HTTP response**: a status code plus data | `200 OK` with a JSON body |

The frontend never touches the pantry. It hands a ticket to the kitchen and waits. That separation is the whole point: the backend is the only place where rules are enforced ("you cannot log in before verifying your email"), so nobody can bypass them by editing the web page.

### HTTP in one minute

Every call to the backend has:

- a **method** that says the intent: `GET` read, `POST` create or act, `PUT` update, `DELETE` remove;
- a **path** that names the thing: `/api/v1/users/me/profile`;
- optional **headers**: metadata such as `Authorization: Bearer <token>` (who is calling);
- an optional **body**: JSON data for `POST`/`PUT`.

The reply has a **status code** and usually a JSON body. Codes you will see constantly:

| Code | Meaning | When we send it |
|---|---|---|
| 200 | OK | Successful read, login, update |
| 201 | Created | Registration succeeded |
| 400 | Bad request | Expired or used link, wrong file type |
| 401 | Unauthorized (really: not authenticated) | No or invalid token, wrong password |
| 403 | Forbidden (authenticated, but not allowed) | Candidate opening the admin panel |
| 404 | Not found | Downloading a CV that was never uploaded |
| 409 | Conflict | Email already registered |
| 413 | Payload too large | CV over 5 MB |
| 422 | Unprocessable entity | Body failed validation (password too short) |
| 429 | Too many requests | Rate limit hit |
| 500 | Server error | A bug. Tests exist so this never ships. |

### JSON

JSON is the text format both sides agree on. `{"email": "ali@example.com", "password": "Secret123!"}` is a JSON object. Python turns it into a dict, and FastAPI does that for you.

### What an API is

An API (Application Programming Interface) is the set of paths the backend offers plus the shape of the data each one accepts and returns. FastAPI writes the documentation automatically: run the server and open `http://localhost:8000/docs`.

---

## 2. The tools and why each one is here

| Tool | What it does | Why not something else |
|---|---|---|
| **Python 3.13** | The language | The report's AI work (LangChain, embeddings) is Python; one language for the whole backend |
| **Virtual environment** (`.venv`) | A private folder of installed libraries for this project | Projects on one machine would otherwise fight over versions |
| **pip + requirements.txt** | Installs the libraries listed in the file | Everyone (and Docker) installs exactly the same set |
| **FastAPI** | The web framework: routes URLs to functions, validates data, generates docs | Fast, modern, type-hint driven, async-ready; the user chose it over Django |
| **Uvicorn** | The server that listens on a port and hands requests to FastAPI | FastAPI is just code; something must speak HTTP |
| **Pydantic** | Defines the shape of request/response data and validates it | Validation errors become automatic 422 replies |
| **pydantic-settings** | Reads configuration from environment variables / `.env` | Secrets and ports never live in code |
| **SQLAlchemy** (ORM) | Lets you write Python classes instead of SQL for tables | Portable between SQLite (tests) and PostgreSQL (real) |
| **Alembic** | Version control for the database structure (migrations) | Schema changes must be repeatable on every machine |
| **psycopg** | The PostgreSQL driver SQLAlchemy uses | PostgreSQL is the project database (pgvector later for CV embeddings) |
| **bcrypt** | Hashes passwords | Purpose-built, slow on purpose, salted |
| **PyJWT** | Creates and checks JSON Web Tokens | Stateless login sessions |
| **python-multipart** | Parses file uploads | Needed for the CV upload |
| **pytest + httpx** | Runs tests; TestClient calls the app without a server | Proof that each user story works, every time code changes |
| **Docker + docker-compose** | Runs PostgreSQL (and the API) in containers | Same database everywhere, no local install needed |

---

## 3. How one request travels through our code

Take `POST /api/v1/auth/login` with `{"email": "...", "password": "..."}`.

```
Browser / frontend
   |  HTTP request
   v
Uvicorn (server)                                 asgi.py / docker-entrypoint.sh
   |
   v
FastAPI app                                      app/main.py  (create_app)
   |  CORS middleware, then route matching
   v
Rate-limit dependency                            app/core/rate_limit.py   -> 429 if too many tries
   |
   v
Body validation with a schema                    app/schemas/auth.py  LoginRequest  -> 422 if invalid
   |
   v
DB session dependency                            app/database/session.py  get_db
   |
   v
Controller function                              app/controller/auth.py  login()
   |  calls
   v
Service function (the rules)                     app/services/auth_service.py  login() -> authenticate()
   |  reads/writes through models
   v
ORM models  <->  database tables                 app/database/models/user.py  User
   |
   v
Security helpers                                 app/core/security.py  verify_password, create_access_token
   |
   v
Response schema                                  app/schemas/auth.py  TokenResponse
   |  JSON
   v
Browser receives {"access_token": "...", "user": {...}, "dashboard": "/candidate/dashboard"}
```

If anything in the service raises an `AppError` (for example `InvalidCredentials`), the exception handler in `app/main.py` turns it into `{"detail": "Invalid email or password"}` with status 401. The controller never has to think about it.

---

## 4. The project structure and what each folder is for

```
backend/content/
├── app/
│   ├── main.py                 builds the FastAPI app, attaches routers, error handler, CORS
│   ├── core/
│   │   ├── config.py           Settings read from .env / environment
│   │   ├── security.py         bcrypt hashing, JWT create/decode, one-time tokens
│   │   ├── dependencies.py     get_current_user, require_roles, require_permission, require_approved_company
│   │   ├── permissions.py      Role enum, role -> permission map, dashboard per role
│   │   ├── rate_limit.py       sliding-window limiter + FastAPI dependency
│   │   ├── exceptions.py       AppError family: status code + message per situation
│   │   └── time.py             utcnow(), from_timestamp(): one definition of "now"
│   ├── database/
│   │   ├── session.py          engine, SessionLocal, Base, get_db
│   │   └── models/             one file per table: user, company, profile, token
│   ├── schemas/                Pydantic request/response shapes (auth, user, company, common)
│   ├── services/               business rules: auth_service, profile_service, email_service, storage
│   └── controller/             routers: auth, users, company, admin
├── alembic/                    migrations (versions/ holds one file per schema change)
├── alembic.ini
├── scripts/create_admin.py     CLI to create the first platform administrator
├── tests/                      pytest suite, one file per user story
├── asgi.py                     `python asgi.py` runs the dev server with auto-reload
├── requirements.txt
├── Dockerfile, docker-entrypoint.sh, .dockerignore
└── .env.example                every setting, with comments
```

**The layering rule.** Data flows controller → service → model, never the other way. A controller never writes SQL; a service never reads an HTTP header; a model never sends an email. When you are unsure where code belongs, ask "which layer's vocabulary does this use?" HTTP words (status, header, body) belong in controllers; product words (register, verify, shortlist) in services; table words (column, foreign key) in models.

---

## 5. What was built, in the order it was built

### Step 1: environment

```
python -m venv .venv              # private Python
.venv\Scripts\activate            # (PowerShell) use it
pip install -r requirements.txt   # install libraries
```

`.gitignore` was extended so `.venv/`, `uploads/`, `*.db` and `.env` never get committed. Committed secrets are the most common beginner security mistake.

### Step 2: configuration (`app/core/config.py`)

A `Settings` class lists every knob with a type and a default. `pydantic-settings` fills it from environment variables (or `.env`). Tests override values by setting environment variables before importing the app. Key idea: the same code runs in development, test and production; only the environment differs.

### Step 3: database plumbing and models

`session.py` creates the **engine** (knows the database URL, keeps a connection pool) and `SessionLocal` (a factory for per-request sessions). `get_db` is a FastAPI dependency that opens a session for one request and always closes it, even on errors.

Four tables were modelled as Python classes:

| Table | Purpose | Story |
|---|---|---|
| `users` | everyone who can log in: email, name, bcrypt hash, role, status, company link, last login, password_changed_at | US-1.1, 1.3, 1.4, 1.8 |
| `companies` | company record with approval status and rejection reason | US-1.3, 3.6 |
| `candidate_profiles` | one row per candidate: job title, location, bio, JSON lists for skills/education/experience, CV path | US-1.7 |
| `one_time_tokens` | hashed email-verification and password-reset tokens with expiry and used-at | US-1.2, 1.6 |
| `revoked_tokens` | ids (jti) of JWTs that were logged out before expiry | US-1.5 |

Design choices worth copying:

- **UUID primary keys** instead of 1, 2, 3: ids are not guessable and can be generated before insert.
- **Enums stored as text** (`candidate`, `pending_verification`): readable in any database tool, identical on SQLite and PostgreSQL.
- **Naive UTC datetimes everywhere** (`core/time.py`): one convention avoids a whole family of timezone bugs.
- **JSON columns** for lists that are always read and written together (skills). A separate table would only add joins.

### Step 4: migrations (Alembic)

The models describe the tables we want; the database has the tables that exist. Alembic compares the two and writes the difference as a migration file:

```
alembic revision --autogenerate -m "auth module tables"   # writes alembic/versions/<timestamp>_auth_module_tables.py
alembic upgrade head                                      # applies every migration not yet applied
```

Every developer and every deployment runs `alembic upgrade head`; the Docker entrypoint does it on start. Never create tables by hand.

### Step 5: security helpers (`app/core/security.py`)

- `hash_password` / `verify_password`: bcrypt with a configurable cost (12 in production, 4 in tests for speed).
- `create_access_token`: signs `{"sub": user id, "role": ..., "jti": unique id, "iat": issued at, "exp": expiry}` with `SECRET_KEY`.
- `decode_access_token`: verifies the signature and expiry.
- `generate_one_time_token` / `hash_token`: random 43-character strings for email links; only the SHA-256 hash is stored.

### Step 6: services (the rules)

`auth_service.py` reads top to bottom as the life of an account:

1. `register_individual`: reject duplicate email (case-insensitive), hash the password, create the user as `pending_verification`, issue a verification token, commit, then email the link.
2. `verify_email`: find the token by hash, refuse if used or expired, mark used, set the user `active`.
3. `resend_verification`: silently do nothing for unknown or already-active emails (no account enumeration), otherwise invalidate old tokens and send a new one.
4. `register_company`: create the company as `pending` and its administrator as an `active` user with role `company_admin`.
5. `decide_company`: platform admin approves (sets `approved_at`) or rejects (stores the reason); emails the outcome.
6. `authenticate` / `login`: verify the password **before** looking at account status, so the error never reveals whether an email exists; then block unverified or suspended accounts; stamp `last_login_at`; return a 24-hour JWT and the dashboard path for the role.
7. `logout`: write the token's `jti` into `revoked_tokens`.
8. `request_password_reset` / `reset_password`: same neutral behaviour as resend; a reset updates `password_changed_at`, which invalidates every token issued earlier.

`profile_service.py` creates the profile lazily, applies partial updates (`exclude_unset`), computes the completion percentage, and validates CV uploads by extension, declared type, size and the real file header (`%PDF-`).

`email_service.py` separates *composing* an email from *delivering* it, with console, memory (tests) and SMTP backends. `storage.py` hides the filesystem behind `save` / `delete` / `absolute_path`, so moving to Azure Blob Storage later touches one file.

### Step 7: controllers (the endpoints)

| Endpoint | Story | Notes |
|---|---|---|
| `POST /auth/register/individual` | US-1.1 | 201, rate limited |
| `POST /auth/verify-email`, `GET /auth/verify-email?token=` | US-1.2 | GET exists so the emailed link works without a frontend |
| `POST /auth/resend-verification` | US-1.2 | neutral message |
| `POST /auth/register/company` | US-1.3 | returns company + admin user |
| `POST /auth/login` | US-1.4 | token, user, dashboard; rate limited |
| `POST /auth/logout` | US-1.5 | needs the token; revokes it |
| `POST /auth/forgot-password`, `POST /auth/reset-password` | US-1.6 | neutral message; reset logs out old sessions |
| `GET /users/me` | US-1.4 | any role |
| `GET/PUT /users/me/profile`, `POST/GET/DELETE /users/me/cv` | US-1.7 | candidate only |
| `GET /company/me/status`, `GET /company/me` | US-1.3 / 3.6 | the second needs an approved company |
| `GET /admin/overview`, `GET /admin/companies/pending`, `POST /admin/companies/{id}/approve|reject` | US-1.8 / 12.4 | platform admin only |

All paths are under `/api/v1`. Versioning the path lets a future `/api/v2` coexist with old clients.

### Step 8: tests

`tests/` holds one file per story. `conftest.py` forces test settings (in-memory email outbox, fast bcrypt, rate limiting off, temp upload folder), creates a fresh SQLite database file per test, and provides helpers (`register_candidate`, `login`, `auth_headers`, `make_user`). Run them with:

```
cd backend/content
.venv\Scripts\python.exe -m pytest
```

66 tests cover every acceptance criterion in the Module 1 stories, including the alternate flows (expired links, duplicate emails, suspended accounts, forged tokens, oversized CVs).

### Step 9: Docker

`Dockerfile` builds the API image; `docker-entrypoint.sh` runs migrations then Uvicorn; `docker-compose.yml` starts PostgreSQL (with a health check), Adminer, and the API with the right environment variables.

---

## 6. Concepts you must own

### Hashing is not encryption

Encryption is reversible with a key. Hashing is one-way. We store `bcrypt(password)` and at login compute `bcrypt(typed password)` and compare. If the database leaks, attackers get hashes, not passwords, and bcrypt's slowness (plus a random salt per hash) makes guessing expensive. Never write your own hashing.

### A JWT is a signed note, not a secret

Paste a token into https://jwt.io and you will read its contents. That is fine: the signature guarantees nobody changed it. What must stay secret is `SECRET_KEY`. Consequences:

- Do not put private data in a token.
- Logging out needs extra work (our `revoked_tokens` list), because the token itself stays valid until `exp`.
- A password reset should kill old tokens: we compare the token's `iat` with `password_changed_at`.

### Authentication vs authorization

Authentication: who are you? (`get_current_user`, status 401 when it fails.) Authorization: are you allowed? (`require_roles`, `require_permission`, status 403.) Keep the words straight; the status codes follow.

### Dependencies (dependency injection)

`Depends(get_current_user)` tells FastAPI to run that function first and hand its result to your endpoint. Dependencies compose: `require_approved_company` depends on `get_current_user`, which depends on `get_db`. The endpoint stays a few lines long and security lives in one place.

### Validation at the edge

Schemas reject bad input before any of our code runs: `password: str = Field(min_length=8, max_length=72)` is both documentation and enforcement. The 72 limit is a bcrypt fact (it ignores bytes beyond 72, and new versions refuse them).

### Do not reveal which emails exist

"Forgot password" and "resend verification" return the same message whether or not the account exists, and login returns the same error for unknown email and wrong password. Timing is equalised by hashing a dummy password when the email is unknown. This blocks *account enumeration*.

### One-time tokens are hashed too

If the `one_time_tokens` table leaked, stored raw tokens would let an attacker reset anyone's password. Storing SHA-256 hashes means the table alone is useless; only the email holder has the raw token.

### Migrations are code

Schema changes are files in `alembic/versions`, reviewed and committed like any code. `upgrade()` applies, `downgrade()` reverts.

### Tests are the specification, executable

Each test name says what must be true: `test_wrong_password_and_unknown_email_give_the_same_message`. When you change code, the suite tells you in seconds whether a story broke.

---

## 7. Three real problems hit while building this, and how they were found

1. **Routers "missing".** A quick script listed only 5 routes. The cause: newer FastAPI versions attach included routers lazily, so the counting filter was wrong, not the app. Lesson: when a diagnostic disagrees with the tests, suspect the diagnostic.
2. **`admin@intellihire.local` rejected with 422.** The email validator refuses reserved domains such as `.local` and `.test`. Lesson: read the full error body; it named the rule.
3. **PostgreSQL password refused.** A locally installed PostgreSQL 18 already owned port 5432, so the app talked to the wrong server. Found with `Get-NetTCPConnection -LocalPort 5432`. Fix: map the container to 5434. Lesson: "connection refused / auth failed" often means "wrong server", not "wrong password".
4. **A reset-password test failed intermittently.** JWT `iat` is a whole second; `password_changed_at` had microseconds, so a token issued in the same second as the reset was rejected. Fix: compare at second precision. Lesson: time precision mismatches are a classic source of flaky tests.

---

## 8. Running it yourself

```
# 1. database (from the repo root). Host port is POSTGRES_PORT in .env (5434).
docker compose up -d postgres

# 2. API (from backend/content)
copy .env.example .env               # once; adjust DATABASE_URL if needed
.venv\Scripts\alembic.exe upgrade head
.venv\Scripts\python.exe asgi.py     # http://localhost:8000/docs

# 3. first platform administrator
.venv\Scripts\python.exe -m scripts.create_admin --email admin@intellihire.com --password "Admin@12345"

# 4. whole stack in Docker instead (API on http://localhost:4010)
docker compose up -d --build
```

A full walk-through with PowerShell:

```
$api = "http://localhost:8000/api/v1"
Invoke-RestMethod -Method Post -Uri "$api/auth/register/individual" -ContentType application/json -Body '{"full_name":"Ali Khan","email":"ali@example.com","password":"Secret123!"}'
# look at the server console: the verification email is printed there; copy the token
Invoke-RestMethod -Method Post -Uri "$api/auth/verify-email" -ContentType application/json -Body '{"token":"<paste>"}'
$login = Invoke-RestMethod -Method Post -Uri "$api/auth/login" -ContentType application/json -Body '{"email":"ali@example.com","password":"Secret123!"}'
Invoke-RestMethod -Uri "$api/users/me" -Headers @{ Authorization = "Bearer $($login.access_token)" }
```

---

## 9. Exercises

1. Add `POST /auth/change-password` for a logged-in user (needs the current password). Write the test first.
2. Add `POST /admin/users/{id}/suspend` and `/unsuspend` (US-12.6). The dependency work is already done; it is mostly a service function and a test.
3. Add a `GET /users/me/sessions` that lists revoked tokens for the user. Ask yourself why we cannot list *active* tokens.
4. Change `email_backend` to `smtp` with a free Mailtrap account and watch a real email arrive.
5. Break something on purpose (remove the `.lower()` in `get_user_by_email`) and read which tests fail and why.

---

## 10. Glossary

- **API**: the set of endpoints a backend exposes.
- **ASGI**: the interface between a Python async web framework and a server (Uvicorn).
- **bcrypt**: a password hashing algorithm.
- **CORS**: browser rule about which web origins may call an API.
- **Dependency**: a function FastAPI runs before an endpoint and injects the result of.
- **Endpoint / route**: one method + path combination, e.g. `POST /auth/login`.
- **Engine / session**: SQLAlchemy's connection pool / per-request unit of work.
- **Enum**: a fixed set of named values (`Role.CANDIDATE`).
- **Foreign key**: a column that references another table's primary key.
- **JWT**: a signed JSON token used to prove identity on each request.
- **Migration**: a versioned script that changes the database schema.
- **Middleware**: code that runs on every request before routing (CORS here).
- **ORM**: object-relational mapper; Python classes standing in for tables.
- **Rate limiting**: capping how often a client may call an endpoint.
- **RBAC**: role-based access control.
- **Schema (Pydantic)**: the declared shape of request/response data.
- **Service**: a function holding business rules, independent of HTTP.
- **Status code**: the three-digit result of an HTTP response.
- **UUID**: a 128-bit random identifier.
