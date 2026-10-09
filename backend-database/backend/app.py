"""Canonical FastAPI backend for Smart Garbage Detection.

NOTE: This is the real backend. The Flask/Firebase prototype
(mobile-app/app.py) and mobile-app/fixed_sql_app.py are deprecated
prototypes — see DEPRECATED.md. Do not run them in production.
"""
import logging
import os
import shutil
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from geoalchemy2.shape import to_shape
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import config, crud, db, models
from .ml import model as ml_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

VALID_STATUSES = ("pending", "cleaned")
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

app = FastAPI(title="Smart Garbage Detection API")

# CORS — restricted to dashboard origin(s), never "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)

# Mount uploads (original images) and annotated images (YOLO boxed images)
os.makedirs(config.UPLOAD_DIR, exist_ok=True)
os.makedirs(config.ANNOTATED_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=config.UPLOAD_DIR), name="uploads")
app.mount("/annotated", StaticFiles(directory=config.ANNOTATED_DIR), name="annotated")


# ---------- Pydantic response models ----------
class DetectionItem(BaseModel):
    class_: str = Field(alias="class")
    class_id: Optional[int] = None
    confidence: float
    bbox: List[float] = []

    class Config:
        populate_by_name = True


class DetectionsSummary(BaseModel):
    count: int
    items: List[DetectionItem] = []


class UploadResponse(BaseModel):
    success: bool = True
    report_id: int
    prediction: str
    confidence: Optional[float] = None
    severity: int = 1
    duplicate_of: Optional[int] = None
    image_path: str
    boxed_image_path: Optional[str] = None
    detections: Optional[DetectionsSummary] = None


class ReportOut(BaseModel):
    id: int
    image_path: Optional[str] = None
    boxed_image_path: Optional[str] = None
    prediction: Optional[str] = None
    confidence: Optional[float] = None
    severity: Optional[int] = None
    status: str
    latitude: float
    longitude: float
    created_at: Optional[datetime] = None


class StatusUpdateOut(BaseModel):
    success: bool = True
    report_id: int
    status: str
    message: str


# ---------- Dependencies ----------
def get_db():
    db_session = db.SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()


def require_admin(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    """Simple API-key guard for admin endpoints (e.g. PATCH status).

    Set ADMIN_API_KEY in .env; the dashboard sends it as X-API-Key.
    """
    if not config.ADMIN_API_KEY:
        raise HTTPException(
            status_code=503,
            detail="ADMIN_API_KEY is not configured on the server. Set it in .env.",
        )
    if x_api_key != config.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key")
    return True


# ---------- Helpers ----------
def _validate_coords(latitude: float, longitude: float):
    if not (-90.0 <= latitude <= 90.0):
        raise HTTPException(status_code=400, detail="latitude must be between -90 and 90")
    if not (-180.0 <= longitude <= 180.0):
        raise HTTPException(status_code=400, detail="longitude must be between -180 and 180")


def _validate_image(file: UploadFile):
    is_image = bool(file.content_type and file.content_type.startswith("image/"))
    ext = os.path.splitext(file.filename or "").lower()
    if not is_image:
        if ext not in VALID_EXTENSIONS:
            raise HTTPException(status_code=400, detail="File must be an image (jpg/png/webp)")
    if ext and ext not in VALID_EXTENSIONS:
        # content-type said image/* but extension is suspicious — still allow
        # common case, but block executables masquerading as images.
        if ext in {".exe", ".js", ".html", ".svg"}:
            raise HTTPException(status_code=400, detail="Unsupported file type")
    return ext or ".jpg"


def _severity_score(detections: list) -> int:
    """Severity 1-5 from detection count + total box area fraction.

    Heuristic: more boxes / larger area => higher severity. Stored in the
    detections JSON so no schema migration is required.
    """
    if not detections:
        return 1
    count = len(detections)
    area = 0.0
    for d in detections:
        try:
            x1, y1, x2, y2 = d.get("bbox", [0, 0, 0, 0])
            area += max(0.0, x2 - x1) * max(0.0, y2 - y1)
        except Exception:
            continue
    # area is in pixels^2; normalize loosely (640x640 ref = ~409600)
    area_frac = min(area / 409600.0, 3.0)
    score = 1 + min(count - 1, 2) + (1 if area_frac > 0.25 else 0) + (1 if area_frac > 1.0 else 0)
    return max(1, min(5, int(score)))


def _find_duplicate(db_session: Session, latitude: float, longitude: float, prediction: str):
    """Return an existing pending report within ~20m with the same class, if any.

    Uses PostGIS ST_DWithin on geography for metre-accurate distance.
    """
    try:
        q = (
            db_session.query(models.GarbageReport)
            .filter(
                models.GarbageReport.status == "pending",
                models.GarbageReport.prediction == prediction,
                func.ST_DWithin(
                    models.GarbageReport.geom.cast(__import__("geoalchemy2").Geometry("GEOGRAPHY")),
                    func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326).cast(
                        __import__("geoalchemy2").Geometry("GEOGRAPHY")
                    ),
                    20.0,
                ),
            )
            .order_by(models.GarbageReport.created_at.desc())
            .first()
        )
        return q
    except Exception as e:
        logger.warning("Duplicate check failed (non-fatal): %s", e)
        return None


def _serialize_report(r) -> dict:
    point = to_shape(r.geom)
    dets = r.detections if isinstance(r.detections, dict) else None
    return {
        "id": r.id,
        "image_path": f"/uploads/{r.image_path}" if r.image_path else None,
        "boxed_image_path": f"/annotated/{r.boxed_image_path}" if r.boxed_image_path else None,
        "prediction": r.prediction,
        "confidence": r.confidence,
        "severity": (dets or {}).get("severity"),
        "status": r.status,
        "latitude": point.y,
        "longitude": point.x,
        "created_at": r.created_at,
    }


async def _process_upload(
    file: UploadFile,
    latitude: float,
    longitude: float,
    db_session: Session,
    category: Optional[str] = None,
    severity: Optional[int] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
) -> dict:
    """Shared implementation for POST /predict and POST /upload-report."""
    _validate_coords(latitude, longitude)
    ext = _validate_image(file)
    logger.info("Upload: lat=%s lon=%s file=%s", latitude, longitude, file.filename)

    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(config.UPLOAD_DIR, filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Enforce file-size limit after save (streaming check would be nicer;
    # this keeps memory low while staying simple).
    size_mb = os.path.getsize(file_path) / (1024 * 1024)
    if size_mb > config.MAX_UPLOAD_MB:
        os.remove(file_path)
        raise HTTPException(
            status_code=413, detail=f"File too large ({size_mb:.1f} MB > {config.MAX_UPLOAD_MB} MB)"
        )

    prediction = "pending"
    confidence = None
    all_detections: list = []
    detections_json = None
    boxed_filename = None

    try:
        all_detections, boxed_filename = ml_model.run_inference(file_path)
        if all_detections:
            primary = all_detections[0]
            prediction = primary["class"]
            confidence = primary["confidence"]
        else:
            prediction = "No Waste Detected"
            confidence = 0.0
    except Exception as e:
        logger.warning("ML inference failed, storing as pending: %s", e)
        prediction = "pending"
        confidence = None
        all_detections = []
        boxed_filename = None

    auto_severity = _severity_score(all_detections)
    if severity is not None:
        try:
            auto_severity = max(1, min(5, int(severity)))
        except (TypeError, ValueError):
            pass

    if all_detections or True:
        detections_json = {
            "count": len(all_detections),
            "severity": auto_severity,
            "primary": (
                {
                    "class": prediction,
                    "confidence": confidence,
                    "bbox": all_detections[0]["bbox"],
                }
                if all_detections
                else None
            ),
            "all": all_detections,
        }

    # Duplicate detection: same class within ~20m => link instead of double-count.
    duplicate_of = None
    if prediction not in ("pending", "No Waste Detected"):
        dup = _find_duplicate(db_session, latitude, longitude, prediction)
        if dup is not None:
            duplicate_of = dup.id
            logger.info("Duplicate of report #%s (within 20m, class=%s)", dup.id, prediction)
            # Bump severity on the original to reflect repeated sightings.
            try:
                old = dup.detections if isinstance(dup.detections, dict) else {}
                old_sev = int(old.get("severity", 1))
                old["severity"] = max(1, min(5, old_sev + 1))
                from sqlalchemy.orm.attributes import flag_modified

                dup.detections = dict(old)
                flag_modified(dup, "detections")
                db_session.commit()
            except Exception as e:
                logger.warning("Could not bump duplicate severity: %s", e)

    try:
        report = crud.create_garbage_report(
            db_session, filename, latitude, longitude,
            prediction, confidence, detections_json, boxed_filename,
        )
        if report.id is None:
            raise HTTPException(status_code=500, detail="Failed to create report")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Database error: %s", e)
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    return {
        "success": True,
        "report_id": report.id,
        "prediction": prediction,
        "confidence": confidence,
        "severity": auto_severity,
        "duplicate_of": duplicate_of,
        "image_path": f"/uploads/{filename}",
        "boxed_image_path": f"/annotated/{boxed_filename}" if boxed_filename else None,
        "detections": (
            {"count": len(all_detections), "items": all_detections[:5]}
            if all_detections
            else None
        ),
    }


# ---------- Routes ----------
@app.get("/health")
def health_check():
    info = ml_model.get_model_info()
    return {"status": "ok", "model": info}


@app.post("/predict", response_model=UploadResponse)
async def predict_garbage(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: str = Form(None),
    severity: int = Form(None),
    title: str = Form(None),
    description: str = Form(None),
    db_session: Session = Depends(get_db),
):
    """Mobile upload + inference. Shared logic with /upload-report."""
    return await _process_upload(file, latitude, longitude, db_session,
                                 category, severity, title, description)


@app.post("/upload-report", response_model=UploadResponse)
async def upload_report(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: str = Form(None),
    severity: int = Form(None),
    title: str = Form(None),
    description: str = Form(None),
    db_session: Session = Depends(get_db),
):
    """Dashboard upload. Shared logic with /predict."""
    return await _process_upload(file, latitude, longitude, db_session,
                                 category, severity, title, description)


@app.get("/reports", response_model=List[ReportOut])
def read_reports(skip: int = 0, limit: int = 100, db_session: Session = Depends(get_db)):
    if skip < 0 or limit < 1 or limit > 500:
        raise HTTPException(status_code=400, detail="Invalid pagination (skip>=0, 1<=limit<=500)")
    return [_serialize_report(r) for r in crud.get_reports(db_session, skip=skip, limit=limit)]


@app.get("/reports/{report_id}", response_model=ReportOut)
def read_report(report_id: int, db_session: Session = Depends(get_db)):
    r = crud.get_report(db_session, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return _serialize_report(r)


@app.get("/reports-in-area", response_model=List[ReportOut])
def read_reports_in_area(min_lon: float, min_lat: float, max_lon: float, max_lat: float,
                         db_session: Session = Depends(get_db)):
    _validate_coords(min_lat, min_lon)
    _validate_coords(max_lat, max_lon)
    reports = crud.get_reports_in_area(db_session, min_lon, min_lat, max_lon, max_lat)
    return [_serialize_report(r) for r in reports]


@app.get("/reports/stats/summary")
def reports_stats(db_session: Session = Depends(get_db)):
    """Aggregates powering the Analytics page: per-day counts, class split, status split."""
    rows = db_session.query(models.GarbageReport).all()
    per_day: dict = {}
    per_class: dict = {}
    per_status: dict = {}
    for r in rows:
        day = r.created_at.date().isoformat() if r.created_at else "unknown"
        per_day[day] = per_day.get(day, 0) + 1
        per_class[r.prediction or "unknown"] = per_class.get(r.prediction or "unknown", 0) + 1
        per_status[r.status or "unknown"] = per_status.get(r.status or "unknown", 0) + 1
    return {
        "total": len(rows),
        "per_day": dict(sorted(per_day.items())),
        "per_class": per_class,
        "per_status": per_status,
    }


@app.get("/reports/stats/hotspots")
def reports_hotspots(db_session: Session = Depends(get_db)):
    """Top grid cells (~0.01 deg ≈ 1km) ranked by report count for municipal teams."""
    rows = db_session.query(models.GarbageReport).all()
    cells: dict = {}
    for r in rows:
        try:
            pt = to_shape(r.geom)
            key = (round(pt.y, 2), round(pt.x, 2))
            cells[key] = cells.get(key, 0) + 1
        except Exception:
            continue
    ranked = sorted(
        ({"latitude": k[0], "longitude": k[1], "count": v} for k, v in cells.items()),
        key=lambda d: d["count"],
        reverse=True,
    )
    return {"hotspots": ranked[:20]}


@app.patch("/reports/{report_id}/status", response_model=StatusUpdateOut)
def update_report_status(report_id: int, status: str,
                         db_session: Session = Depends(get_db),
                         _admin: bool = Depends(require_admin)):
    """Update status. Requires X-API-Key admin header. Statuses: pending | cleaned."""
    status = (status or "").lower().strip()
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"
        )
    report = crud.get_report(db_session, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = status
    db_session.commit()
    db_session.refresh(report)
    logger.info("Report #%s status -> %s", report_id, status)
    return {"success": True, "report_id": report_id, "status": status,
            "message": f"Report status updated to '{status}'"}


@app.get("/reports/by-status/{status}")
def get_reports_by_status(status: str, skip: int = 0, limit: int = 100,
                          db_session: Session = Depends(get_db)):
    """Reports filtered by status (case-insensitive: Pending/pending both work)."""
    normalized = (status or "").lower().strip()
    if normalized not in VALID_STATUSES:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"
        )
    reports = (
        db_session.query(models.GarbageReport)
        .filter(models.GarbageReport.status == normalized)
        .offset(skip).limit(limit).all()
    )
    results = [_serialize_report(r) for r in reports]
    return {"status_filter": normalized, "count": len(results), "reports": results}
