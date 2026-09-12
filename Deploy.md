# DukaMe — Local Dev Quick Reference

## One-time setup

**Hosts file** (Windows, as Administrator) — `C:\Windows\System32\drivers\etc\hosts`:
```
127.0.0.1 dukamedev.local
```

**Clone:**
```powershell
git clone https://github.com/alumasinde/dukame.git
cd dukame
```

**Backend env** — `backend/.env` (copy from `.env.example`):
```env
DATABASE_URL=mysql+aiomysql://USER:PASSWORD@HOST:3306/dukame
REDIS_URL=redis://redis:6379/0
JWT_SECRET=replace-with-a-long-random-development-secret
```

**Frontend env** — `frontend/.env` (copy from `.env.example`):
```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

**Prerequisites:** Git, Docker Desktop, Node.js 20+, MySQL 8.x (runs *outside* Docker — inspect with HeidiSQL).

---

## Every-day startup order

```powershell
# 1. Backend + worker + Redis
cd backend
docker compose -f docker-compose.dev.yml up --build

# 2. Migrations (new terminal)
docker compose -f docker-compose.dev.yml run --rm api alembic upgrade head

# 3. Frontend (new terminal)
cd frontend
npm install          # first time only
npm run dev -- --host dukamedev.local
```

Open: `http://dukamedev.local:5173`

---

## Common commands

| Task | Command |
|---|---|
| Run backend tests | `docker compose -f docker-compose.dev.yml run --rm api pytest` |
| Rebuild image (new deps) | `docker compose -f docker-compose.dev.yml build --no-cache api` |
| Stop everything | `docker compose -f docker-compose.dev.yml down` |
| Tail API logs | `docker compose -f docker-compose.dev.yml logs -f api` |
| Tail worker logs | `docker compose -f docker-compose.dev.yml logs -f worker` |
| Shell into API container | `docker compose -f docker-compose.dev.yml exec api sh` |
| Check current migration | `docker compose -f docker-compose.dev.yml run --rm api alembic current` |
| Check migration consistency | `docker compose -f docker-compose.dev.yml run --rm api alembic check` |
| Frontend production build | `npm run build` (from `frontend/`) |
| Preview frontend build | `npm run preview -- --host dukamedev.local` |

---

## Health checks

- `http://localhost:8000/health` — process is up
- `http://localhost:8000/ready` — MySQL + Redis are reachable
- `http://localhost:8000/docs` — Swagger (debug mode only)

---

## Hard rules

- **Never** hand-edit application tables in HeidiSQL — Alembic migrations only.
- **Never** commit `.env` or secrets.
- MySQL is external, not in Docker Compose.
- Model change → Alembic migration → `alembic upgrade head` → tests → frontend check.