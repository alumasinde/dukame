# DukaMe

Kenyan-first commerce operating system for small and growing merchants.

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

## Development

1. Copy `.env.example` to `.env`.
2. Set the external MySQL connection values.
3. Start the Docker services:

```bash
docker compose -f docker-compose.dev.yml up --build
```

4. Run migrations from the API container:

```bash
docker compose -f docker-compose.dev.yml run --rm api alembic upgrade head
```

5. Run the test suite:

```bash
docker compose -f docker-compose.dev.yml run --rm api pytest
```

The API is exposed on `http://localhost:8000` by default.

## Required environment

See `.env.example`. Secrets must not be committed.
