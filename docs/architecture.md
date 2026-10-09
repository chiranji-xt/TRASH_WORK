# System Architecture

```mermaid
flowchart LR
    subgraph Mobile["Mobile App (Flutter)"]
        A[Camera / Gallery] --> B[Report form\nlat, lon, category]
        B --> C[DetectionPreviewPage\nPOST /predict]
    end

    subgraph Backend["Backend (FastAPI + PostGIS)"]
        D["POST /predict\nPOST /upload-report\n(shared _process_upload)"]
        D --> E["YOLOv8 model\n(model.names, CONFIDENCE_THRESHOLD)"]
        E --> F["Annotated image\n/annotated/boxed_*"]
        D --> G[("PostgreSQL + PostGIS\ngarbage_reports")]
        D --> H["Duplicate check\nST_DWithin 20 m"]
        H --> G
        G --> I["GET /reports /by-status/*\n/stats/summary /stats/hotspots"]
        J["PATCH /reports/:id/status\nX-API-Key guard"] --> G
    end

    subgraph Dash["Web Dashboard (React + Vite)"]
        K[Map / Heatmap] --> I
        L[Reports table] --> I
        L --> J
        M[Analytics\nper-day, per-class, hotspots] --> I
    end

    C -->|multipart image + lat/lon| D
    I -->|JSON + image URLs| K
    F -->|boxed_image_path| K
```

## Components

- **Mobile (Flutter):** capture → `POST /predict` → boxed image + class → history/map. Base URL via `--dart-define=API_BASE_URL`.
- **Backend (FastAPI):** single `_process_upload` serves `/predict` and `/upload-report`; YOLO inference with one tunable `CONFIDENCE_THRESHOLD`; PostGIS duplicate check (~20 m, same class) + severity score (1–5).
- **Database (PostgreSQL + PostGIS):** `garbage_reports` table managed by Alembic (`backend-database/alembic/`).
- **Dashboard (React):** `VITE_API_URL` for backend; admin login stores `X-API-Key` for status updates; Analytics reads `/reports/stats/*`.
