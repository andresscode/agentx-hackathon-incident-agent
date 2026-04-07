# Quick Guide

## Run with Docker Compose

```bash
git clone <repo-url>
cd incident-agent
docker compose up --build
```

Open http://localhost:3000 — add and delete todos to verify the stack works.

---

> This must be migrated to the README file

## Local Development

### Prerequisites
- Node.js 20+, pnpm
- Python 3.12+, uv
- PostgreSQL (or use `docker compose up db` to run just the database)

### Database
```bash
docker compose up db
```

### Backend
```bash
cd backend
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
cp .env.example .env
pnpm install
pnpm dev
```
