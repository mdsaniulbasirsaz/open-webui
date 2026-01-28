# OpenWebUI Backend

This README documents the backend layout, how core pieces work together, and the steps to add email verification.

## Project tree (base)

```
backend/
|-- .dockerignore
|-- .gitignore
|-- .webui_secret_key
|-- dev.sh
|-- requirements-min.txt
|-- requirements.txt
|-- start.sh
|-- start_windows.bat
|-- data/
|   |-- readme.txt
|   |-- cache/
|   |-- uploads/
|   `-- vector_db/
|-- open_webui/
|   |-- __init__.py
|   |-- alembic.ini
|   |-- config.py
|   |-- constants.py
|   |-- env.py
|   |-- functions.py
|   |-- main.py
|   |-- tasks.py
|   |-- data/
|   |-- internal/
|   |   |-- db.py
|   |   |-- wrappers.py
|   |   `-- migrations/
|   |-- migrations/
|   |   `-- versions/
|   |-- models/
|   |-- retrieval/
|   |   |-- loaders/
|   |   |-- models/
|   |   |-- vector/
|   |   `-- web/
|   |-- routers/
|   |-- socket/
|   |-- static/
|   |   |-- assets/
|   |   |-- fonts/
|   |   `-- swagger-ui/
|   |-- storage/
|   |-- test/
|   |-- tools/
|   `-- utils/
`-- venv/
```

Notes:
- `data/` and `venv/` are runtime and local only. They should not be committed.
- `open_webui/` holds all backend source code.

## How the backend works

- Entry point: `open_webui/main.py` builds the FastAPI app, mounts static assets, registers routers, and wires middleware.
- Configuration: `open_webui/env.py` loads environment variables and sets paths; `open_webui/config.py` defines runtime config values used via `request.app.state.config`.
- Database: `open_webui/internal/db.py` sets up SQLAlchemy engine, sessions, and JSONField; `open_webui/internal/migrations/` holds peewee migrations that run first.
- Models: `open_webui/models/` contains DB schemas (SQLAlchemy), Pydantic models, request forms, and table classes with CRUD helpers.
- Routers: `open_webui/routers/` exposes API endpoints; each router depends on models and utilities.
- Retrieval: `open_webui/retrieval/` handles RAG flows, loaders, vector DB connectors, and web search providers.
- Tasks: `open_webui/tasks.py` is a Redis-backed async task registry for background jobs.
- Socket: `open_webui/socket/` provides real-time model and task updates via websocket.
- Storage: `open_webui/storage/provider.py` defines pluggable storage backends.
- Utilities: `open_webui/utils/` houses auth, rate limits, embeddings, access control, middleware, and helpers.
- Tests: `open_webui/test/` contains pytest tests for routers and utilities.

## Working with models

The common pattern in `open_webui/models/*.py`:
- SQLAlchemy table class (inherits `Base`) defines the DB schema.
- Pydantic model mirrors the table for API responses and internal validation.
- Form models (Pydantic) represent request payloads.
- `*Table` class provides CRUD methods using `get_db_context` from `open_webui/internal/db.py`.

Useful references:
- Users: `open_webui/models/users.py` defines `User`, `UserModel`, and user CRUD helpers.
- Auths: `open_webui/models/auths.py` manages password auth and ties to users.
- Models: `open_webui/models/models.py` defines model entries, metadata, and access control.

When adding or changing models:
1) Update SQLAlchemy schema in the model file.
2) Update Pydantic models and forms as needed.
3) Add or extend CRUD methods in the `*Table` class.
4) Add an Alembic migration in `open_webui/migrations/versions/`.
5) If `ENABLE_DB_MIGRATIONS` is used for peewee migrations, add a matching migration in `open_webui/internal/migrations/`.
6) Update routers in `open_webui/routers/` to expose endpoints and use `Depends(get_session)` for DB access.

## Database migrations (Peewee + Alembic)

On startup (when `ENABLE_DB_MIGRATIONS=True`), OpenWebUI runs:
1) Peewee migrations from `open_webui/internal/migrations/` (via `peewee_migrate.Router`)
2) Alembic migrations from `open_webui/migrations/` (upgrade to `heads`)

### Run migrations locally

From `open-webui/backend/` with the venv activated:
- Upgrade DB to latest:
  - `alembic upgrade heads`
- Check current revision:
  - `alembic current`
- See history:
  - `alembic history --verbose`

### Create a new Alembic migration

1) Make your SQLAlchemy model changes under `open_webui/models/`.
2) Ensure required env vars are set for imports (minimum: `DATABASE_URL`; for web auth deployments also set `WEBUI_SECRET_KEY`).
3) Generate a revision:
   - `alembic revision --autogenerate -m "Your message"`
4) Review the generated file in `open_webui/migrations/versions/` and edit as needed.

Tip: if you want to generate migrations without providing full runtime env, you can set `SKIP_ENV_VALIDATION=True` for the Alembic command invocation.

## Adding email verification

Email verification is not implemented yet. Here is a safe, minimal plan that fits the current architecture.

1) Add DB fields or a verification table
- Option A (simple): add fields to `User` in `open_webui/models/users.py`:
  - `email_verified_at` (BigInteger, nullable)
  - `email_verification_sent_at` (BigInteger, nullable)
- Option B (more flexible): create `open_webui/models/email_verifications.py` with:
  - `id`, `user_id`, `token`, `expires_at`, `used_at`, `created_at`

2) Add migrations
- Add Alembic migration in `open_webui/migrations/versions/` for the new columns or table.
- If peewee migrations are still required in your deployment, add a matching migration in `open_webui/internal/migrations/`.

3) Add email sender utility
- Create `open_webui/utils/email.py` that sends mail using SMTP.
- Add config keys in `open_webui/config.py` (and env support in `open_webui/env.py`) for:
  - `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`, `SMTP_TLS`
- Use `BackgroundTasks` to send messages without blocking requests.

4) Hook into signup
- In `open_webui/routers/auths.py` inside `signup`, generate a verification token after user creation.
- Store the token (Option A in user fields or Option B in a separate table).
- Email the user a link like: `https://<your-host>/api/v1/auths/verify-email?token=<token>`.
- Do not mark the user as fully verified until the token is confirmed.

5) Add verification endpoints
- Add `POST /auths/verify-email` (or `GET` with token) to validate the token, set `email_verified_at`, and mark token as used.
- Add `POST /auths/resend-verification` to re-issue tokens when needed.

6) Enforce verification on protected routes
- Update `open_webui/utils/auth.py` in `get_verified_user` to check `email_verified_at` if a new config flag like `REQUIRE_EMAIL_VERIFICATION` is enabled.
- For OAuth or LDAP signups, set `email_verified_at` automatically if the provider guarantees verified emails.

7) Add tests
- Add tests in `open_webui/test/apps/webui/routers/test_auths.py` to cover signup, verify, and resend flows.

With the above, you will have a minimal but secure email verification flow that matches the existing model and router patterns.
