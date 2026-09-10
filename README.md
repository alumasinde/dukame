# DukaMe

Kenyan-first commerce operating system for small and growing merchants.

## Repository layout

```text
DukaMe/
├── backend/        # FastAPI, SQLAlchemy, Alembic, Redis, workers and tests
├── frontend-test/  # Language-independent browser client for backend testing
└── .github/        # CI workflows
```

The production frontend will be built separately. `frontend-test` is intentionally plain HTML/CSS/JavaScript so the backend can be tested without depending on the production frontend framework.

## Phase 1

Phase 1 establishes the production-oriented application foundation:

- FastAPI API with `/api/v1`
- SQLAlchemy 2.x and Alembic
- External MySQL database (outside Docker)
- Redis for shared infrastructure
- Dockerized API and worker services
- Structured JSON logging and request IDs
- Centralized error handling
- Configurable rate limiting foundation
- Health and readiness endpoints
- Pytest test foundation
- CI checks for linting, type checking, tests, and migration consistency
- Migration-first database workflow

## Database policy

Alembic migrations are the authoritative mechanism for application schema changes. Do not use application startup to mutate the schema, and do not create or alter application tables manually in HeidiSQL as part of normal development.

HeidiSQL remains useful for inspection, diagnostics, and controlled administration.

## Backend development

```bash
cd backend
copy .env.example .env
```

Set the external MySQL connection values in `.env`, then start the API and worker:

```bash
docker compose -f docker-compose.dev.yml up --build
```

Run migrations:

```bash
docker compose -f docker-compose.dev.yml run --rm api alembic upgrade head
```

Run tests:

```bash
docker compose -f docker-compose.dev.yml run --rm api pytest
```

The API is exposed on `http://localhost:8000` by default.

## Backend test frontend

The language-independent test frontend is in `frontend-test/`. From the repository root:

```bash
cd frontend-test
python -m http.server 5500
```

Then open `http://localhost:5500` and use the endpoint buttons to verify the backend.

The test frontend is not the production Vue frontend. It exists to validate API connectivity, CORS, health checks and responses before the real frontend is implemented.

## Required environment

See `backend/.env.example`. Secrets must not be committed.

