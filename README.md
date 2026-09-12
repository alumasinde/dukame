# DukaMe

Kenyan-first commerce operating system for small and growing merchants.

DukaMe is being built as a real production application, with a FastAPI backend, MySQL, Redis and a Vue 3 frontend. The application is designed around small Kenyan merchants who need a simple way to manage their online shop, customers and commerce operations.

> **Setting up locally or looking for a command?** See [`DEPLOY.md`](./DEPLOY.md) for environment config and the full command reference. This file covers what the project is and how it's structured.

## Repository layout

```text
DukaMe/
├── backend/        # FastAPI, SQLAlchemy, Alembic, Redis, workers and tests
├── frontend/       # Vue 3 + TypeScript + Vite merchant application
├── frontend-test/  # Plain browser client for backend/API testing
└── .github/        # CI workflows
```

`frontend/` is the actual application frontend. `frontend-test/` is kept as a lightweight API testing client and is not part of the production UI.

## Architecture overview

```text
Browser
   │
   ▼
Frontend (Vue 3 / Vite)
   │
   │ HTTP /api/v1
   ▼
FastAPI backend
   │
   ├── MySQL (external, 8.x)
   └── Redis
```

The frontend and backend are independently deployable. MySQL runs outside Docker by design — it's treated as an external managed dependency, not a container the app owns.

### Backend

- FastAPI, Python 3.12+
- SQLAlchemy 2.x (async)
- MySQL 8.x (external)
- Alembic migrations
- Redis
- JWT access tokens + opaque refresh tokens
- Argon2 password hashing
- Email verification and password reset flows
- Multi-tenant workspaces/shops with tenant-scoped RBAC
- Subscription and plan management
- Structured JSON logging, request IDs, centralized error handling
- Configurable Redis-backed rate limiting
- Health and readiness endpoints

### Frontend

- Vue 3, TypeScript, Vite
- Vue Router, Pinia, Axios
- Responsive merchant dashboard
- Authentication and session handling
- Shop/workspace management
- Billing and subscription views
- Team and RBAC views
- Account settings

## Module-first backend architecture

Business modules own their domain code. Shared infrastructure belongs in `app/core`.

```text
backend/app/
├── core/
│   ├── config.py
│   ├── database.py
│   ├── errors.py
│   ├── health.py
│   ├── logging.py
│   ├── rate_limit.py
│   └── redis.py
│
├── modules/
│   ├── auth/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── routes/
│   ├── tenancy/
│   ├── rbac/
│   └── subscriptions/
│
└── api/v1/
```

New business functionality should follow the same module-first approach rather than placing domain logic in large global folders.

## Frontend architecture

```text
frontend/src/
├── lib/          # API and shared infrastructure
├── stores/       # Pinia application state
├── layouts/      # Application shells
├── views/        # Route-level pages
├── router.ts     # Route and navigation guards
├── App.vue
├── main.ts
└── styles.css
```

As DukaMe grows, frontend business features should also be organized by feature rather than creating one large component or service layer.

## Database rule

Alembic migrations are the authoritative mechanism for application schema changes.

Do not:

- create application tables manually in HeidiSQL during normal development
- alter application tables manually to bypass migrations
- add schema mutation code to application startup

HeidiSQL is useful for inspecting data, checking indexes and diagnosing database problems — not for schema changes.

## Production principles

DukaMe is being developed with production deployment in mind.

- Do not hardcode business configuration.
- Keep secrets in environment/secret management systems.
- Use Alembic for schema changes.
- Validate all API input.
- Never trust prices or totals supplied by the browser.
- Keep tenant authorization server-side.
- Use rate limiting on sensitive endpoints.
- Keep authentication tokens out of URLs and logs where possible.
- Use structured logging and request IDs.
- Keep payment processing idempotent.
- Use durable background processing for critical asynchronous work.
- Keep MySQL transactions and concurrency rules explicit.
- Store uploaded media outside MySQL.
- Keep production frontend and backend independently deployable.

## Phase roadmap

DukaMe is being developed in eight major phases:

1. Foundation & Infrastructure
2. Identity, Tenancy & Subscriptions
3. Store & Catalogue
4. Cart, Checkout, Orders & Inventory
5. Payments & M-Pesa
6. WhatsApp & Notifications
7. Merchant Operations & Growth
8. Production Hardening & Launch

A phase should be completed and validated before moving to the next phase.

## License

See the repository for the current project license and usage terms.