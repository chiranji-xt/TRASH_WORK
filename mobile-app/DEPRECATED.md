# Deprecated prototypes — do NOT run

The canonical backend is `backend-database/backend/app.py` (FastAPI + PostGIS).

| File | Status |
|---|---|
| `mobile-app/app.py` (Flask + Firebase) | DEPRECATED prototype. Kept for reference only. |
| `mobile-app/fixed_sql_app.py` | DEPRECATED experiment (direct-YOLO FastAPI copy, `conf=0.1`, no boxed images). Its logic is merged into the canonical `backend/app.py` with a single `CONFIDENCE_THRESHOLD`. |

If you need Firebase behaviour, port it as a feature into the canonical backend
instead of reviving these files.
