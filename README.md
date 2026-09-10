# DukaMe

Kenyan-first commerce operating system for small and growing merchants.

DukaMe is being built as a real production application, with a FastAPI backend, MySQL, Redis and a Vue 3 frontend. The application is designed around small Kenyan merchants who need a simple way to manage their online shop, customers and commerce operations.

## Repository layout

```text
DukaMe/
├── backend/        # FastAPI, SQLAlchemy, Alembic, Redis, workers and tests
├── frontend/       # Vue 3 + TypeScript + Vite merchant application
├── frontend-test/  # Plain browser client for backend/API testing
└── .github/        # CI workflows
```

`frontend/` is the actual application frontend. `frontend-test/` is kept as a lightweight API testing client and is not part of the production UI.

## Current architecture

### Backend

- FastAPI
- Python 3.12+
- SQLAlchemy 2.x async
- MySQL 8.x external database
- Alembic migrations
- Redis
- Docker Compose for API, worker and Redis
- JWT access tokens
- Opaque refresh tokens
- Argon2 password hashing
- Email verification and password reset flows
- Multi-tenant workspaces/shops
- Tenant-scoped RBAC
- Subscription and plan management
- Structured JSON logging
- Request IDs
- Centralized error handling
- Configurable Redis-backed rate limiting
- Health and readiness endpoints

### Frontend

- Vue 3
- TypeScript
- Vite
- Vue Router
- Pinia
- Axios
- Responsive merchant dashboard
- Authentication and session handling
- Shop/workspace management
- Billing and subscription views
- Team and RBAC views
- Account settings

## Local development URL

Use the local hostname:

```text
http://dukamedev.local
```

The recommended local setup is:

```text
Browser
   │
   ▼
http://dukamedev.local
   │
   │ Vue/Vite
   ▼
Frontend :5173
   │
   │ HTTP /api/v1
   ▼
FastAPI :8000
   │
   ├── MySQL (external)
   └── Redis (Docker)
```

During development, Vite runs the frontend on port `5173` while FastAPI runs on port `8000`. The hostname `dukamedev.local` is used as the browser-facing development hostname.

## Prerequisites

Install:

- Git
- Docker Desktop
- Node.js 20+ and npm
- MySQL 8.x
- HeidiSQL (recommended for database inspection)

MySQL is intentionally **not** included in Docker Compose. Your MySQL server/database runs outside Docker and is managed or inspected separately, for example with HeidiSQL.

## 1. Clone the repository

```powershell
git clone https://github.com/alumasinde/dukame.git
cd dukame
```

If the repository is already cloned:

```powershell
git pull origin main
```

## 2. Configure the local hostname

On Windows, edit the hosts file as Administrator:

```text
C:\Windows\System32\drivers\etc\hosts
```

Add:

```text
127.0.0.1 dukamedev.local
```

After saving, verify it:

```powershell
ping dukamedev.local
```

It should resolve to `127.0.0.1`.

## 3. Configure the backend

```powershell
cd backend
copy .env.example .env
```

Open `backend/.env` and configure your external MySQL connection and local secrets.

At minimum, the backend requires:

```env
DATABASE_URL=mysql+aiomysql://USER:PASSWORD@HOST:3306/dukame
REDIS_URL=redis://redis:6379/0
JWT_SECRET=replace-with-a-long-random-development-secret
```

Use the actual MySQL username, password, host and database name for your local installation.

Do not commit `.env` or any secrets to Git.

## 4. Start the backend infrastructure

From `backend/`:

```powershell
docker compose -f docker-compose.dev.yml up --build
```

This starts:

- FastAPI API
- Background worker
- Redis

MySQL remains outside Docker.

The backend API is available at:

```text
http://localhost:8000
```

The versioned API base is:

```text
http://localhost:8000/api/v1
```

When debug mode is enabled, FastAPI documentation is available at:

```text
http://localhost:8000/docs
```

## 5. Run database migrations

Open another PowerShell window and from `backend/` run:

```powershell
docker compose -f docker-compose.dev.yml run --rm api alembic upgrade head
```

Check the current migration:

```powershell
docker compose -f docker-compose.dev.yml run --rm api alembic current
```

Check migration consistency:

```powershell
docker compose -f docker-compose.dev.yml run --rm api alembic check
```

### Database rule

Alembic migrations are the authoritative mechanism for application schema changes.

Do not:

- create application tables manually in HeidiSQL during normal development
- alter application tables manually to bypass migrations
- add schema mutation code to application startup

HeidiSQL is useful for inspecting data, checking indexes and diagnosing database problems.

## 6. Start the Vue frontend

Open another PowerShell window:

```powershell
cd C:\projects\dukame\frontend
npm install
```

Create the frontend environment file:

```powershell
copy .env.example .env
```

Set the API URL in `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Start Vite:

```powershell
npm run dev -- --host dukamedev.local
```

Open:

```text
http://dukamedev.local:5173
```

### Optional: use `dukamedev.local` without `:5173`

If you specifically want:

```text
http://dukamedev.local
```

with no port in the browser, put a local reverse proxy in front of Vite and FastAPI. The application architecture already keeps the frontend and API separately deployable; the reverse proxy can later route `/` to Vite and `/api/` to FastAPI.

For the current Vite development server, `http://dukamedev.local:5173` is the direct development URL.

## 7. Run the frontend build

Before considering frontend changes complete:

```powershell
cd frontend
npm run build
```

This runs TypeScript checking and creates the Vite production build.

Preview the production build locally with:

```powershell
npm run preview -- --host dukamedev.local
```

## 8. Run backend tests

From `backend/`:

```powershell
docker compose -f docker-compose.dev.yml run --rm api pytest
```

If the Docker image does not contain the development test dependencies, rebuild it first:

```powershell
docker compose -f docker-compose.dev.yml build --no-cache api
```

Then run the tests again.

Do not install backend test dependencies globally on Windows just to make the project work. The Docker environment is the authoritative backend development environment.

## 9. Useful backend commands

Start services:

```powershell
docker compose -f docker-compose.dev.yml up --build
```

Stop services:

```powershell
docker compose -f docker-compose.dev.yml down
```

View logs:

```powershell
docker compose -f docker-compose.dev.yml logs -f api
```

View worker logs:

```powershell
docker compose -f docker-compose.dev.yml logs -f worker
```

Open a shell inside the API container:

```powershell
docker compose -f docker-compose.dev.yml exec api sh
```

Run Alembic:

```powershell
docker compose -f docker-compose.dev.yml exec api alembic upgrade head
```

## 10. Health checks

API health:

```text
http://localhost:8000/health
```

Dependency readiness:

```text
http://localhost:8000/ready
```

`/health` confirms that the API process is running. `/ready` also checks required infrastructure such as MySQL and Redis.

## 11. Development workflow

Use this order when starting development:

```text
1. Start external MySQL
       ↓
2. Start Docker Compose
       ↓
3. Run Alembic migrations
       ↓
4. Start Vue/Vite
       ↓
5. Open dukamedev.local:5173
       ↓
6. Develop against /api/v1
       ↓
7. Run backend tests
       ↓
8. Run frontend build
```

For database changes:

```text
Model change
    ↓
Alembic migration
    ↓
Migration upgrade
    ↓
Backend tests
    ↓
Frontend/API verification
```

## 12. Module-first backend architecture

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

## 13. Frontend architecture

The Vue application follows a reusable application structure:

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

## 14. Production principles

DukaMe is being developed with production deployment in mind.

Key rules:

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
