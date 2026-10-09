# Data Flow

```mermaid
sequenceDiagram
    participant Citizen as Citizen (mobile)
    participant App as Flutter app
    participant API as FastAPI backend
    participant YOLO as YOLOv8 model
    participant DB as PostGIS
    participant Dash as Dashboard

    Citizen->>App: Take photo + location
    App->>API: POST /predict (image, lat, lon, category, severity)
    API->>API: Validate image, size ≤ MAX_UPLOAD_MB, lat/lon ranges
    API->>YOLO: run_inference (conf=CONFIDENCE_THRESHOLD)
    YOLO-->>API: detections + boxed image
    API->>DB: Duplicate? ST_DWithin(geom, point, 20m) + same class
    alt duplicate found
        API->>DB: Bump original severity +1
    end
    API->>DB: INSERT garbage_report (severity in detections JSON)
    API-->>App: {report_id, prediction, confidence, severity, boxed_image_path}
    App->>App: Show boxed image + class; add to history
    Dash->>API: GET /reports / GET /reports/by-status/pending
    API->>DB: SELECT reports
    DB-->>Dash: Reports + image URLs
    Dash->>Dash: Map pins, heatmap, analytics, hotspots
    Dash->>API: PATCH /reports/{id}/status?status=cleaned (X-API-Key)
    API->>DB: UPDATE status
    API-->>Dash: {success, status}
```

## Key contracts

- **Statuses (everywhere):** `pending` | `cleaned` (lowercase; server normalizes case).
- **Images:** originals at `/uploads/*`, annotated at `/annotated/boxed_*`.
- **Stats:** `GET /reports/stats/summary` (per-day, per-class, per-status) and `GET /reports/stats/hotspots` (ranked cells) power the Analytics page.
