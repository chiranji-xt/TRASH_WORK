"""Canonical FastAPI backend for Smart Garbage Detection.

NOTE: This is the real backend. The Flask/Firebase prototype
(mobile-app/app.py) and mobile-app/fixed_sql_app.py are deprecated
prototypes — see DEPRECATED.md. Do not run them in production.
"""
import logging
import os
import shutil
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from geoalchemy2.shape import to_shape
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from . import config, crud, db, models
from .cases import service as case_service
from .priority import score as priority_score
from .verification import checks as verify_checks
from .ml import model as ml_model

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

VALID_STATUSES = ("pending", "cleaned")
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}

# Priority weights load once at startup: a broken config (weights not
# summing to 1) raises ValueError here with a clear message instead of
# silently skewing dispatch order.
PRIORITY_CONFIG = priority_score.config_from_env()

# Verification knobs load once at startup.
VERIFY_CONFIG = verify_checks.config_from_env()

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
    # Cases feature: which case the report landed in + how.
    case_id: Optional[int] = None
    match_outcome: Optional[str] = None
    suggested_duplicate_of: Optional[int] = None
    recurrence_of: Optional[int] = None


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
    case_id: Optional[int] = None


class CaseOut(BaseModel):
    id: int
    status: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    report_count: int = 0
    distinct_reporters: int = 0
    first_reported_at: Optional[datetime] = None
    last_reported_at: Optional[datetime] = None
    recurrence_of: Optional[int] = None
    suggested_duplicate_of: Optional[int] = None
    score_version: Optional[str] = None
    priority: Optional[dict] = None
    closed_at: Optional[datetime] = None
    closing_verification_id: Optional[int] = None


class MergeBody(BaseModel):
    report_id: int


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


def require_cleaner(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    """Cleaner devices may submit cleanup verifications but may NOT set
    report status directly (PATCH stays admin-only). The admin key is
    accepted everywhere a cleaner key is."""
    if config.ADMIN_API_KEY and x_api_key == config.ADMIN_API_KEY:
        return "admin"
    if x_api_key and x_api_key in (config.CLEANER_API_KEYS or []):
        return f"cleaner:{x_api_key[:6]}"
    if not config.ADMIN_API_KEY and not config.CLEANER_API_KEYS:
        raise HTTPException(
            status_code=503,
            detail="No API keys configured. Set ADMIN_API_KEY / CLEANER_API_KEYS in .env.",
        )
    raise HTTPException(status_code=401, detail="Invalid or missing API key")


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
        "case_id": r.case_id,
    }


def _serialize_case(c) -> dict:
    lat, lon = None, None
    try:
        if c.centroid is not None:
            pt = to_shape(c.centroid)
            lat, lon = pt.y, pt.x
    except Exception:
        pass
    return {
        "id": c.id,
        "status": c.status,
        "latitude": lat,
        "longitude": lon,
        "report_count": c.report_count or 0,
        "distinct_reporters": c.distinct_reporters or 0,
        "first_reported_at": c.first_reported_at,
        "last_reported_at": c.last_reported_at,
        "recurrence_of": c.recurrence_of,
        "suggested_duplicate_of": c.suggested_duplicate_of,
        "score_version": c.score_version,
        "closed_at": c.closed_at,
        "closing_verification_id": c.closing_verification_id,
    }


def _serialize_verification(v) -> dict:
    photos = v.photos if isinstance(v.photos, list) else []
    return {
        "id": v.id,
        "case_id": v.case_id,
        "cleaner_id": v.cleaner_id,
        "attempt_no": v.attempt_no,
        "photos": [f"/uploads/{p}" for p in photos],
        "checks": v.checks,
        "decision": v.decision,
        "spot_checked": v.spot_checked,
        "reviewed_by": v.reviewed_by,
        "reviewed_at": v.reviewed_at,
        "review_reason": v.review_reason,
        "created_at": v.created_at,
    }


def _serialize_case_with_priority(c, db_session) -> dict:
    """Case JSON plus a freshly computed priority (age at query time)."""
    out = _serialize_case(c)
    try:
        out["priority"] = case_service.score_case_response(
            db_session, c, PRIORITY_CONFIG)
        out["score_version"] = out["priority"].get("version")
    except Exception as e:
        logger.warning("Priority scoring failed for case %s: %s", c.id, e)
        out["priority"] = None
    return out


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

    # Cases feature: group with nearby reports of the same pile.
    # Failure-safe by contract (service returns "skipped") plus a local
    # guard, so matching can never break uploads.
    case_outcome: dict = {"outcome": "skipped", "case_id": None}
    try:
        case_outcome = case_service.assign_report_to_case(
            db_session, report, image_abs_path=file_path)
    except Exception as e:
        logger.warning("Case matching failed (non-fatal): %s", e)

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
        "case_id": case_outcome.get("case_id"),
        "match_outcome": case_outcome.get("outcome"),
        "suggested_duplicate_of": case_outcome.get("suggested_duplicate_of"),
        "recurrence_of": case_outcome.get("recurrence_of"),
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


# ---------- Cases (duplicate-report merging) ----------
@app.get("/cases", response_model=List[CaseOut])
def list_cases(status: Optional[str] = None, min_reports: int = 0,
               min_lon: Optional[float] = None, min_lat: Optional[float] = None,
               max_lon: Optional[float] = None, max_lat: Optional[float] = None,
               sort: Optional[str] = None,
               db_session: Session = Depends(get_db)):
    """One row per real-world problem, with report_count for map badges.

    sort=priority ranks open cases by the transparent priority score
    (computed fresh, since days_open changes without new reports).
    """
    q = db_session.query(models.Case)
    if status:
        normalized = status.lower().strip()
        if normalized not in ("open", "cleaned", "reopened"):
            raise HTTPException(status_code=400, detail="Invalid status filter")
        q = q.filter(models.Case.status == normalized)
    if min_reports > 0:
        q = q.filter(models.Case.report_count >= min_reports)
    if None not in (min_lon, min_lat, max_lon, max_lat):
        box = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
        q = q.filter(models.Case.centroid.intersects(box))
    rows = q.order_by(models.Case.last_reported_at.desc()).limit(500).all()
    if (sort or "").lower() == "priority":
        scored = [_serialize_case_with_priority(c, db_session) for c in rows]
        scored.sort(key=lambda c: (c.get("priority") or {}).get("score", 0),
                    reverse=True)
        return scored
    return [_serialize_case(c) for c in rows]


@app.get("/cases/{case_id}")
def read_case(case_id: int, db_session: Session = Depends(get_db)):
    """Case detail: member reports, photos and merge evidence."""
    case = db_session.query(models.Case).filter(models.Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    members = (db_session.query(models.GarbageReport)
               .filter(models.GarbageReport.case_id == case_id)
               .order_by(models.GarbageReport.created_at.desc()).all())
    log = (db_session.query(models.CaseMergeLog)
           .filter(models.CaseMergeLog.case_id == case_id)
           .order_by(models.CaseMergeLog.created_at.desc()).limit(50).all())
    return {
        **_serialize_case(case),
        "reports": [_serialize_report(r) for r in members],
        "priority": case_service.score_case_response(
            db_session, case, PRIORITY_CONFIG),
        "merge_log": [
            {"report_id": e.report_id, "decision": e.decision,
             "score": e.score, "evidence": e.evidence,
             "created_at": e.created_at} for e in log
        ],
    }


@app.post("/cases/{case_id}/merge")
def merge_into_case(case_id: int, body: MergeBody,
                    db_session: Session = Depends(get_db),
                    _admin: bool = Depends(require_admin)):
    """Admin: force a report into a case. Logged as manual_merge."""
    try:
        case = case_service.manual_merge(db_session, case_id, body.report_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "case_id": case.id,
            "report_count": case.report_count}


@app.post("/reports/{report_id}/split")
def split_from_case(report_id: int, db_session: Session = Depends(get_db),
                    _admin: bool = Depends(require_admin)):
    """Admin: pull a report out of its case into a fresh single-report case."""
    try:
        case = case_service.split_report(db_session, report_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"success": True, "report_id": report_id,
            "new_case_id": case.id}


# ---------- Priority (transparent case ranking) ----------
@app.get("/cases/{case_id}/priority")
def case_priority(case_id: int, db_session: Session = Depends(get_db)):
    """Full score breakdown for one case (computed fresh)."""
    case = db_session.query(models.Case).filter(models.Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"case_id": case_id,
            **case_service.score_case_response(db_session, case, PRIORITY_CONFIG)}


@app.get("/priority/weights")
def priority_weights(_admin: bool = Depends(require_admin)):
    """Admin: read the current priority weights. Changes are config-only
    (PRIORITY_W_* env vars); there is no runtime setter by design."""
    return {"version": priority_score.SCORE_VERSION,
            "weights": {
                "items": PRIORITY_CONFIG.w_items,
                "area": PRIORITY_CONFIG.w_area,
                "class": PRIORITY_CONFIG.w_class,
                "reporters": PRIORITY_CONFIG.w_reporters,
                "age": PRIORITY_CONFIG.w_age,
            },
            "caps": {
                "item_cap": PRIORITY_CONFIG.item_cap,
                "reporter_cap": PRIORITY_CONFIG.reporter_cap,
                "age_cap_days": PRIORITY_CONFIG.age_cap_days,
                "extra_class_bonus": PRIORITY_CONFIG.extra_class_bonus,
            },
            "hazard_weights": PRIORITY_CONFIG.hazard_weights}


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
                         reason: Optional[str] = None,
                         db_session: Session = Depends(get_db),
                         _admin: bool = Depends(require_admin)):
    """Update status. Admin-only (cleaner keys are refused with 401):
    cases must close through verification, not direct edits.

    Setting status=cleaned requires a reason (?reason=...) which is written
    to the audit log as an admin_override_cleaned entry.
    """
    status = (status or "").lower().strip()
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400, detail=f"Invalid status. Must be one of: {', '.join(VALID_STATUSES)}"
        )
    if status == "cleaned" and not (reason or "").strip():
        raise HTTPException(
            status_code=400,
            detail="A reason is required to mark a report cleaned (?reason=...). "
                   "Cases should close through POST /cases/{id}/verify-cleanup.",
        )
    report = crud.get_report(db_session, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    report.status = status
    db_session.commit()
    db_session.refresh(report)
    logger.info("Report #%s status -> %s (reason: %s)", report_id, status, reason)
    if status == "cleaned":
        # Audit the override: direct status edits bypass verification.
        db_session.add(models.CaseMergeLog(
            report_id=report_id, case_id=report.case_id,
            decision="admin_override_cleaned", score=None,
            evidence={"reason": (reason or "").strip()}))
        db_session.commit()
    # Keep the parent case lifecycle in sync (all cleaned -> cleaned, etc.).
    try:
        case_service.sync_case_on_report_status(db_session, report)
    except Exception as e:
        logger.warning("Case status sync failed (non-fatal): %s", e)
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


# ---------- Cleanup verification (cases close only through here) ----------
def _verify_detect_fn(image_path: str):
    """Production detector for verification: raw detections at the LOW
    floor (so sub-bar weak hits stay visible as uncertainty) plus an
    annotated image of the production-bar hits.

    Returns (detections, boxed_image_url_or_None).
    """
    model = ml_model.load_model()
    if model is None:
        raise RuntimeError("Detection model is not available")
    result = ml_model._run_model(image_path)
    names = ml_model._current_class_names()
    try:
        h, w = result.orig_shape
        img_area = float(h * w)
    except Exception:
        img_area = 0.0
    raw = []
    for box in result.boxes:
        cid = int(box.cls[0])
        conf = float(box.conf[0])
        if conf < VERIFY_CONFIG.low_confidence:
            continue
        x1, y1, x2, y2 = (round(float(c), 2) for c in box.xyxy[0].tolist())
        if img_area > 0:
            area_frac = max(0.0, x2 - x1) * max(0.0, y2 - y1) / img_area
            if area_frac < ml_model.MIN_BOX_AREA_FRAC:
                continue
        raw.append({"class": names.get(cid, f"Unknown-{cid}"),
                    "class_id": cid, "confidence": round(conf, 4),
                    "bbox": [x1, y1, x2, y2]})
    raw.sort(key=lambda d: d["confidence"], reverse=True)
    drawn = [d for d in raw
             if d["confidence"] >= ml_model.PER_CLASS_CONF.get(
                 d["class"], ml_model.CONFIDENCE_THRESHOLD)]
    boxed_name = ml_model._save_annotated(image_path, drawn)
    boxed_url = f"/annotated/{boxed_name}" if boxed_name else None
    return raw, boxed_url


def _close_case(db_session, case, verification_id: int, reviewer: Optional[str],
                decision_label: str) -> None:
    """Close a case + mark all member reports cleaned. One transaction."""
    now = datetime.now()
    case.status = "cleaned"
    case.closed_at = now
    case.closing_verification_id = verification_id
    members = (db_session.query(models.GarbageReport)
               .filter(models.GarbageReport.case_id == case.id).all())
    for m in members:
        m.status = "cleaned"
    db_session.add(models.CaseMergeLog(
        report_id=None, case_id=case.id, decision=decision_label, score=None,
        evidence={"verification_id": verification_id,
                  "reviewed_by": reviewer,
                  "member_reports": [m.id for m in members]}))
    db_session.commit()


@app.post("/cases/{case_id}/verify-cleanup")
async def verify_cleanup(
    case_id: int,
    files: List[UploadFile] = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    captured_at: Optional[str] = Form(None),
    gps_accuracy_m: Optional[float] = Form(None),
    cleaner_id: Optional[str] = Form(None),
    db_session: Session = Depends(get_db),
    who: str = Depends(require_cleaner),
):
    """Cleaner flow: submit 1..N after-photos proving the pile is gone.

    Returns the decision (passed / failed_still_litter / needs_review /
    rejected_reuse) with per-check evidence and annotated images.
    HONEST LIMIT: the detector cannot prove absence — a missed detection
    can produce a false PASSED, which is why uncertain evidence routes to
    human review and a fraction of passes are spot-checked.
    """
    case = db_session.query(models.Case).filter(models.Case.id == case_id).first()
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.status == "cleaned":
        raise HTTPException(status_code=400, detail="Case is already cleaned")
    if not (VERIFY_CONFIG.min_photos <= len(files) <= VERIFY_CONFIG.max_photos):
        raise HTTPException(
            status_code=400,
            detail=f"Send between {VERIFY_CONFIG.min_photos} and "
                   f"{VERIFY_CONFIG.max_photos} after-photos, got {len(files)}.")

    # Rate limit: max attempts per case per hour.
    window_start = datetime.now() - timedelta(hours=1)
    recent = (db_session.query(models.CleanupVerification)
              .filter(models.CleanupVerification.case_id == case_id,
                      models.CleanupVerification.created_at >= window_start)
              .count())
    if not verify_checks.allowed_attempt(recent, VERIFY_CONFIG):
        raise HTTPException(
            status_code=429,
            detail=f"Too many verification attempts for case {case_id}; "
                   f"try again later (max {VERIFY_CONFIG.max_attempts_per_hour}/hour).")

    try:
        centroid = to_shape(case.centroid)
        centroid_lat, centroid_lon = centroid.y, centroid.x
    except Exception:
        raise HTTPException(status_code=400, detail="Case has no location yet")

    now = datetime.now()
    app_captured = None
    if captured_at:
        try:
            app_captured = datetime.fromisoformat(captured_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="captured_at must be ISO-8601")
    saved = []
    after_photos = []
    for f in files:
        ext = _validate_image(f)
        filename = f"verify_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(config.UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(f.file, buffer)
        if os.path.getsize(file_path) / (1024 * 1024) > config.MAX_UPLOAD_MB:
            os.remove(file_path)
            raise HTTPException(status_code=413, detail="After-photo too large")
        saved.append(filename)
        after_photos.append(verify_checks.AfterPhoto(
            path=file_path, latitude=latitude, longitude=longitude,
            captured_at=app_captured))

    # Context: member photos (before) + earlier after-photos (reuse check).
    members = (db_session.query(models.GarbageReport)
               .filter(models.GarbageReport.case_id == case_id).all())
    before_paths = []
    for m in members:
        p = os.path.join(config.UPLOAD_DIR, os.path.basename(m.image_path or ""))
        if os.path.exists(p):
            before_paths.append(p)
    prior_afters = []
    for v in (db_session.query(models.CleanupVerification)
              .filter(models.CleanupVerification.case_id == case_id).all()):
        for p in (v.photos if isinstance(v.photos, list) else []):
            full = os.path.join(config.UPLOAD_DIR, os.path.basename(p))
            if os.path.exists(full):
                prior_afters.append(full)
    classes = sorted({m.prediction for m in members if m.prediction})
    bars = dict(ml_model.PER_CLASS_CONF) if hasattr(ml_model, "PER_CLASS_CONF") else {}

    req = verify_checks.VerifyRequest(
        case_id=case_id, centroid_lat=centroid_lat, centroid_lon=centroid_lon,
        case_classes=classes, case_first_reported_at=case.first_reported_at,
        before_photo_paths=before_paths[:6],
        prior_after_photo_paths=prior_afters[-6:],
        photos=after_photos,
        cleaner_id=cleaner_id or who,
        now=now, case_class_bars=bars)
    outcome = verify_checks.decide_verification(req, _verify_detect_fn, VERIFY_CONFIG)

    attempt_no = (db_session.query(models.CleanupVerification)
                  .filter(models.CleanupVerification.case_id == case_id).count()) + 1
    row = models.CleanupVerification(
        case_id=case_id, cleaner_id=cleaner_id or who, attempt_no=attempt_no,
        photos=saved,
        checks=[{**c} for c in outcome.checks],
        decision=outcome.decision,
        spot_checked="; ".join(outcome.needs_review_reasons) if outcome.spot_checked else None)
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)

    if outcome.decision == verify_checks.PASSED:
        _close_case(db_session, case, row.id, None, "verification_passed")
    case_status = db_session.query(models.Case).filter(
        models.Case.id == case_id).first().status
    return {
        "success": True,
        "verification_id": row.id,
        "attempt_no": attempt_no,
        "case_id": case_id,
        "case_status": case_status,
        "decision": outcome.decision,
        "checks": outcome.checks,
        "annotated_images": outcome.annotated_paths,
        "needs_review_reasons": outcome.needs_review_reasons,
        "spot_checked": outcome.spot_checked,
        "limits": verify_checks.HONEST_LIMIT,
    }


@app.get("/verifications")
def list_verifications(decision: Optional[str] = None,
                       case_id: Optional[int] = None,
                       db_session: Session = Depends(get_db),
                       _admin: bool = Depends(require_admin)):
    """Admin review queue (e.g. ?decision=needs_review)."""
    q = db_session.query(models.CleanupVerification)
    if decision:
        q = q.filter(models.CleanupVerification.decision == decision.lower().strip())
    if case_id is not None:
        q = q.filter(models.CleanupVerification.case_id == case_id)
    rows = q.order_by(models.CleanupVerification.created_at.desc()).limit(200).all()
    return [_serialize_verification(v) for v in rows]


@app.post("/verifications/{verification_id}/review")
def review_verification(verification_id: int, approve: bool,
                        reason: Optional[str] = None,
                        db_session: Session = Depends(get_db),
                        _admin: bool = Depends(require_admin)):
    """Admin approves/rejects a NEEDS_REVIEW verification. Reason required."""
    if not (reason or "").strip():
        raise HTTPException(status_code=400, detail="A review reason is required.")
    row = (db_session.query(models.CleanupVerification)
           .filter(models.CleanupVerification.id == verification_id).first())
    if row is None:
        raise HTTPException(status_code=404, detail="Verification not found")
    if row.decision not in (verify_checks.NEEDS_REVIEW,):
        raise HTTPException(status_code=400,
                            detail=f"Only needs_review verifications can be reviewed (is {row.decision})")
    reviewer = "admin"
    row.reviewed_by = reviewer
    row.reviewed_at = datetime.now()
    row.review_reason = reason.strip()
    case = db_session.query(models.Case).filter(models.Case.id == row.case_id).first()
    if approve and case is not None and case.status != "cleaned":
        _close_case(db_session, case, row.id, reviewer, "verification_approved")
        row.decision = verify_checks.PASSED
    else:
        db_session.add(models.CaseMergeLog(
            report_id=None, case_id=row.case_id, decision="verification_rejected",
            score=None, evidence={"verification_id": row.id,
                                  "reviewed_by": reviewer,
                                  "reason": reason.strip()}))
        row.decision = verify_checks.FAILED_STILL_LITTER
    db_session.commit()
    db_session.refresh(row)
    return {"success": True, "verification": _serialize_verification(row)}
