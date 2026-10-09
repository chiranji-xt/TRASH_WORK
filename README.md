# Smart Garbage Detection and Community Mapping System

AI-based system that detects garbage from citizen-submitted photos (YOLOv8),
stores geotagged reports in PostGIS, and visualizes them on a Flutter mobile app
and a React dashboard.

## Modules

| Module | Path | Run |
|---|---|---|
| Backend + Database (canonical API) | `backend-database/` | `uvicorn backend.app:app` (see its README) or `docker compose up` |
| Machine Learning | `machine-learning/` | training info + weights (see its README) |
| Mobile App | `mobile-app/` | `flutter run --dart-define=API_BASE_URL=<backend>` |
| Web Dashboard | `web-dashboard/frontend/` | `npm install && npm run dev` with `VITE_API_URL` set |

## Quickstart (one command)

```bash
# 1. Configure secrets (never commit real values)
cp backend-database/.env.example backend-database/.env
# edit DB_PASSWORD, ADMIN_API_KEY, MODEL_PATH, ALLOWED_ORIGINS

# 2. Run DB + backend
docker compose up --build
# backend at http://localhost:8000, health at /health
```

Without Docker: Postgres 15 + PostGIS → `pip install -r backend-database/requirements.txt` →
`cd backend-database && alembic upgrade head` → `uvicorn backend.app:app --reload`.

## Docs

- `docs/architecture.md` — system diagram
- `docs/data_flow.md` — photo → detection → dashboard sequence
- `mobile-app/DEPRECATED.md` — which backend files are obsolete

## Demo (30 seconds)

1. Mobile: Report tab → pick photo → Submit → see boxed image + class.
2. Dashboard: map shows the new pin live; Reports → change status to `cleaned` (requires admin key login).
3. Analytics: per-day / per-class / hotspot charts update from `/reports/stats/*`.
