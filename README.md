DukaMe

Kenyan-first commerce operating system for small and growing merchants.

Stack

Backend: FastAPI + SQLAlchemy + Alembic + Redis + MySQL 8.x

Frontend: Vue 3 + TypeScript + Vite + Pinia + Axios

Docker Compose runs the API, worker and Redis. MySQL runs externally.

1. Clone

git clone https://github.com/alumasinde/dukame.git
cd dukame

2. Local hostname (Windows)

Run PowerShell as Administrator and add this to C:\Windows\System32\drivers\etc\hosts:

127.0.0.1 dukamedev.local

3. Backend setup

cd backend
copy .env.example .env

Configure .env with your MySQL database, credentials and secrets.

docker compose -f docker-compose.dev.yml up --build -d
docker compose -f docker-compose.dev.yml exec api alembic upgrade head
docker compose -f docker-compose.dev.yml exec api alembic current
docker compose -f docker-compose.dev.yml logs --tail=100 api

4. Backend commands

docker compose -f docker-compose.dev.yml logs -f api
docker compose -f docker-compose.dev.yml logs -f worker
docker compose -f docker-compose.dev.yml exec api sh
docker compose -f docker-compose.dev.yml run --rm api pytest
docker compose -f docker-compose.dev.yml run --rm api alembic check
docker compose -f docker-compose.dev.yml down
docker compose -f docker-compose.dev.yml restart
docker compose -f docker-compose.dev.yml up -d --force-recreate api worker

API: http://localhost:8000 · Docs: http://localhost:8000/docs · Health: http://localhost:8000/health · Ready: http://localhost:8000/ready

5. Frontend setup

Open a new terminal:

cd frontend
copy .env.example .env
npm install
npm run dev -- --host dukamedev.local

Set VITE_API_BASE_URL=http://localhost:8000/api/v1 in frontend/.env.
Open: http://dukamedev.local:5173

6. Frontend commands

npm run build
npm run preview -- --host dukamedev.local

7. Daily workflow

MySQL → Docker Compose → Alembic → Vue/Vite → Develop → Test → Build

For database changes: update model → create migration → run migration → test backend → verify frontend/API.
Never commit .env or secrets. Use Alembic for schema changes; do not manually modify application tables in HeidiSQL.