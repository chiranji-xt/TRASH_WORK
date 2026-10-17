# Smart Garbage Detection & Community Mapping System

AI-powered platform that detects garbage from citizen-submitted photos using YOLOv8,
stores geotagged reports in a PostGIS-enabled PostgreSQL database, and visualizes
them through a Flutter mobile app and a React dashboard. Built for municipal
clean-up teams and community-driven environmental monitoring.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quickstart with Docker](#quickstart-with-docker)
- [Manual Installation](#manual-installation)
- [Usage](#usage)
- [API Endpoints](#api-endpoints)
- [Mobile App](#mobile-app)
- [Web Dashboard](#web-dashboard)
- [ML / Object Detection](#ml--object-detection)
- [Configuration](#configuration)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

**Smart Garbage Detection & Community Mapping System** enables citizens to report
litter by submitting photos from a mobile app. Reports are automatically analyzed
with YOLOv8 object detection, geotagged, and stored in a spatial database. A web
dashboard lets administrators visualize reports on a map, track cleanup status,
and view analytics such as hotspots and per-class statistics.

---

## Features

- **Photo-based reporting** via Flutter mobile app
- **Garbage detection** using YOLOv8 object detection model
- **Geotagged reports** stored in PostgreSQL with PostGIS extension
- **Interactive map** visualization on React dashboard
- **Report status management** (pending / cleaned) with admin authentication
- **Analytics**: per-day, per-class, and hotspot charts
- **Docker Compose** orchestration for database + backend
- **Alembic** database migrations

---

## Architecture

```
+----------------+      +----------------------+      +------------------+
|  Flutter App   |----->|   FastAPI Backend    |----->| PostgreSQL+PostGIS|
|  (Mobile)      |      |  (Python)            |      |  (Database)      |
+----------------+      +----------------------+      +------------------+
                                             |
                                             v
                                    +----------------+
                                    |  YOLOv8 Model |
                                    |  Object Det.  |
                                    +----------------+
                                             ^
                                             |
                                    +----------------+
                                    |   React Dash   |
                                    |   (Web App)    |
                                    +----------------+
```

---

## Project Structure

```
TRASH_WORK/
├── README.md
├── docker-compose.yml
├── .gitignore
├── .gitattributes
├── backend-database/          # FastAPI + SQLAlchemy + Alembic + PostGIS
│   ├── README.md
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── .env.example
│   ├── alembic.ini
│   └── backend/
├── demo-backend/              # Secondary/demo backend
├── docs/                      # Architecture & data flow docs
│   ├── architecture.md
│   └── data_flow.md
├── machine-learning/          # YOLOv8 training & results
│   ├── README.md
│   └── results/
├── mobile-app/                # Flutter mobile client
│   ├── README.md
│   ├── DEPRECATED.md
│   └── pubspec.yaml
└── web-dashboard/             # React + Vite + Tailwind dashboard
    └── frontend/
        ├── README.md
        ├── package.json
        ├── vite.config.js
        ├── tailwind.config.js
        └── src/
```

---

## Prerequisites

| Component | Requirement |
|-----------|-------------|
| Docker (recommended) | Docker + Docker Compose |
| Python | 3.10+ |
| Node.js | 18+ |
| Flutter | 3.x |
| PostgreSQL | 15+ with PostGIS |
| Git LFS | For ML model weights |

---

## Quickstart with Docker

```bash
# 1. Clone the repository
git clone https://github.com/chiranji-xt/TRASH_WORK.git
cd TRASH_WORK

# 2. Configure environment variables
cp backend-database/.env.example backend-database/.env
# Edit DB_PASSWORD, ADMIN_API_KEY, MODEL_PATH, ALLOWED_ORIGINS

# 3. Start all services
docker compose up --build

# 4. Verify
curl http://localhost:8000/health
```

Services:

- **Backend API**: `http://localhost:8000`
- **API Docs (Swagger)**: `http://localhost:8000/docs`
- **PostgreSQL**: port `5432`

---

## Manual Installation

### Backend + Database

```bash
cd backend-database

# Copy environment file
cp .env.example .env
# Edit DB_PASSWORD, ADMIN_API_KEY, MODEL_PATH, ALLOWED_ORIGINS

# Install Python dependencies
pip install -r requirements.txt

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn backend.app:app --reload
```

### Mobile App

```bash
cd mobile-app
flutter pub get
flutter run --dart-define=API_BASE_URL=http://<backend-host>:8000
```

### Web Dashboard

```bash
cd web-dashboard/frontend
npm install
VITE_API_URL=http://localhost:8000 npm run dev
```

---

## Usage

1. **Submit a report** — Open the Flutter app, go to the Report tab, pick a photo, and submit.
2. **View detection** — The app returns a boxed image with detected garbage class.
3. **Map visualization** — The React dashboard displays live pins on a map.
4. **Update status** — Admins can mark reports as `cleaned` using the admin API key.
5. **Analytics** — View per-day, per-class, and hotspot charts from `/reports/stats/*`.

---

## API Endpoints

| Method | Endpoint | Description | Auth |
|--------|----------|-------------|------|
| `GET` | `/health` | Health check | No |
| `POST` | `/predict` | Upload image for detection | No |
| `POST` | `/upload-report` | Upload image + geolocation as report | No |
| `GET` | `/reports` | List all reports | No |
| `GET` | `/reports/{id}` | Get report by ID | No |
| `GET` | `/reports-in-area` | Reports within a geographic area | No |
| `GET` | `/reports/by-status/{status}` | Filter by `pending` or `cleaned` | No |
| `GET` | `/reports/stats/summary` | Aggregated report stats | No |
| `GET` | `/reports/stats/hotspots` | Garbage hotspot locations | No |
| `PATCH` | `/reports/{id}/status?status=cleaned` | Update report status | Admin key |

---

## Mobile App

- **Framework**: Flutter (Dart)
- **Run**: `flutter run --dart-define=API_BASE_URL=<backend-url>`
- **Notes**: See `mobile-app/README.md` and `mobile-app/DEPRECATED.md`

---

## Web Dashboard

- **Framework**: React + Vite + Tailwind CSS
- **Run**: `npm install && VITE_API_URL=<backend-url> npm run dev`
- **Path**: `web-dashboard/frontend/`

---

## ML / Object Detection

- **Model**: YOLOv8
- **Training details & weights**: `machine-learning/`
- **Run training**: See `machine-learning/README.md`

---

## Configuration

Environment variables are defined in `backend-database/.env.example`. Key settings:

- `DB_PASSWORD` — PostgreSQL password
- `ADMIN_API_KEY` — Admin key for status updates
- `MODEL_PATH` — Path to YOLOv8 weights
- `ALLOWED_ORIGINS` — CORS allowed origins

Never commit real `.env` values to version control.

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m "Add your message"`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

Please follow existing code style and add tests where applicable.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

---

**TRASH_WORK** — Community-powered waste detection and mapping.
