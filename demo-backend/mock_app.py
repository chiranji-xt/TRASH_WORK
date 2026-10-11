"""Demo backend for TRASH_WORK — runs WITHOUT Postgres/PostGIS.

Implements the same HTTP API as backend-database/backend/app.py
using an in-memory store, but with REAL YOLOv8 inference when
best.pt is present next to this file (falls back to a fixed mock
prediction otherwise):

  python demo-backend/mock_app.py
  # API at http://localhost:8000, health at /health, docs at /docs
"""
import logging
import os
import sys
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

logger = logging.getLogger(__name__)

app = FastAPI(title="Smart Garbage Detection API (demo)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")
ANNOTATED_DIR = os.path.join(UPLOAD_DIR, "annotated")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(ANNOTATED_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")
app.mount("/annotated", StaticFiles(directory=ANNOTATED_DIR), name="annotated")

# Reuse the proven pure matcher from the real backend (matching.py has no
# DB imports, so this works without Postgres).
try:
    sys.path.insert(0, os.path.join(BASE_DIR, "..", "backend-database"))
    from backend.cases import matching as case_matching
    from backend.priority import score as priority_score
    _MATCHER_AVAILABLE = True
except Exception as e:
    logging.getLogger(__name__).warning("Case matcher unavailable: %s", e)
    case_matching = None
    priority_score = None
    _MATCHER_AVAILABLE = False

# Priority weights load once at startup: broken weights raise ValueError
# here with a clear message instead of silently skewing dispatch.
PRIORITY_CONFIG = priority_score.config_from_env() if _MATCHER_AVAILABLE else None

# Real weights (your trained checkpoint). Override with MODEL_PATH env var.
MODEL_PATH = os.getenv("MODEL_PATH", os.path.join(BASE_DIR, "best.pt"))

# Same per-class bars as the real backend (tuned from validation curves),
# except Plastic relaxed 0.45 -> 0.30: the 0.45 bar was set to suppress
# background false positives, but it also suppresses real pile detections
# (measured: 12 -> 16 kept boxes on a pile scene, no change on clean scenes).
PER_CLASS_CONF = {
    "Cardboard_Paper": 0.25,
    "Glass Waste": 0.20,
    "Metal Waste": 0.15,
    "Plastic Waste": 0.30,
    "Styrofoam": 0.20,
}
CONFIDENCE_THRESHOLD = 0.25

ADMIN_API_KEY = os.getenv("ADMIN_API_KEY", "demo-admin-key")
CLEANER_API_KEYS = [k.strip() for k in os.getenv("CLEANER_API_KEYS", "demo-cleaner-key").split(",") if k.strip()]

# ---- in-memory store (starts empty — add reports via upload) ----
REPORTS = []
NEXT_ID = 1
VALID_STATUSES = ("pending", "cleaned")

# ---- in-memory cases (duplicate-report merging) ----
# Same semantics as the real backend (backend-database/backend/cases/),
# minus PostGIS: distances use haversine, single process needs no locks
# (uploads run sequentially through blocking CPU inference).
CASES = {}
NEXT_CASE_ID = 1
MERGE_LOG = []
CASE_STATUSES = ("open", "cleaned", "reopened")


def _case_config():
    if _MATCHER_AVAILABLE:
        return case_matching.MatchConfig()
    return None


def _member_reports(case_id):
    return [r for r in REPORTS if r.get("case_id") == case_id]


def _abs_photo(url_or_name):
    if not url_or_name:
        return None
    p = os.path.join(UPLOAD_DIR, os.path.basename(url_or_name))
    return p if os.path.exists(p) else None


def _case_classes(case_id):
    classes = []
    for m in _member_reports(case_id):
        if m.get("prediction") and m["prediction"] not in classes:
            classes.append(m["prediction"])
        dets = (m.get("detections") or {}).get("items") or []
        for d in dets:
            if isinstance(d, dict) and d.get("class") and d["class"] not in classes:
                classes.append(d["class"])
    return classes


def _recompute_case(case):
    members = _member_reports(case["id"])
    if not members:
        case["report_count"] = 0
        return
    case["report_count"] = len(members)
    case["centroid_lat"] = sum(m["latitude"] for m in members) / len(members)
    case["centroid_lon"] = sum(m["longitude"] for m in members) / len(members)
    stamps = sorted(m["created_at"] for m in members if m.get("created_at"))
    if stamps:
        case["first_reported_at"] = stamps[0]
        case["last_reported_at"] = stamps[-1]
    # No reporter ids flow through the demo (mobile app sends none),
    # so distinct_reporters stays 0 — same contract as the real backend.
    case["distinct_reporters"] = 0


def _serialize_case(c):
    return {
        "id": c["id"],
        "status": c["status"],
        "latitude": c.get("centroid_lat"),
        "longitude": c.get("centroid_lon"),
        "report_count": c.get("report_count", 0),
        "distinct_reporters": c.get("distinct_reporters", 0),
        "first_reported_at": c.get("first_reported_at"),
        "last_reported_at": c.get("last_reported_at"),
        "recurrence_of": c.get("recurrence_of"),
        "suggested_duplicate_of": c.get("suggested_duplicate_of"),
        "score_version": c.get("score_version"),
        "closed_at": c.get("closed_at"),
        "closing_verification_id": c.get("closing_verification_id"),
    }


def _image_dims(abs_path):
    if not abs_path or not os.path.exists(abs_path):
        return None
    try:
        from PIL import Image
        with Image.open(abs_path) as img:
            return img.size
    except Exception:
        return None


def _case_priority(case):
    """Fresh {score, components, version} for one case (age at query time).

    Anti-double-counting: items, area and class mix come from the single
    member report with the highest detected item count, never the sum.
    """
    if not _MATCHER_AVAILABLE:
        return None
    try:
        members = _member_reports(case["id"])
        if not members:
            return priority_score.score_case(
                priority_score.CaseFacts(), PRIORITY_CONFIG)

        def count_of(m):
            dets = m.get("detections") or {}
            try:
                return int(dets.get("count") or len(dets.get("items") or []) or 0)
            except (TypeError, ValueError):
                return 0

        best = max(members, key=count_of)
        dets = best.get("detections") or {}
        items = [d for d in (dets.get("items") or []) if isinstance(d, dict)]
        classes = [str(d["class"]) for d in items if d.get("class")]
        if best.get("prediction") and best["prediction"] not in classes:
            classes.append(best["prediction"])
        area_frac = 0.0
        dims = _image_dims(_abs_photo(best.get("image_path")))
        if dims and dims[0] > 0 and dims[1] > 0 and items:
            img_area = float(dims[0] * dims[1])
            total = 0.0
            for d in items:
                try:
                    x1, y1, x2, y2 = (float(c) for c in d.get("bbox", [0, 0, 0, 0]))
                    total += max(0.0, x2 - x1) * max(0.0, y2 - y1)
                except (TypeError, ValueError):
                    continue
            area_frac = min(total / img_area, 1.0)
        days_open = 0.0
        try:
            first = case.get("first_reported_at")
            if first:
                days_open = max((datetime.utcnow()
                                 - datetime.fromisoformat(first)).total_seconds() / 86400.0, 0.0)
        except Exception:
            days_open = 0.0
        facts = priority_score.CaseFacts(
            item_count=count_of(best), covered_area_frac=area_frac,
            classes=classes, distinct_reporters=0, days_open=days_open,
            location_sensitivity=1.0)
        out = priority_score.score_case(facts, PRIORITY_CONFIG)
        case["score_version"] = out["version"]
        return out
    except Exception as e:
        logger.warning("Priority scoring failed for case %s: %s", case.get("id"), e)
        return None


def _assign_case(report, file_path):
    """Match one report into the case graph. Never raises for matching
    reasons — returns a skipped outcome so uploads always succeed."""
    outcome = {"outcome": "skipped", "case_id": None}
    if not _MATCHER_AVAILABLE:
        return outcome
    try:
        M = case_matching
        config = M.MatchConfig()
        now = datetime.utcnow()
        inp = M.ReportInput(
            latitude=report["latitude"], longitude=report["longitude"],
            age_hours=0.0,
            classes=[d["class"] for d in
                     ((report.get("detections") or {}).get("items") or [])
                     if isinstance(d, dict) and d.get("class")] or
                    ([report["prediction"]] if report.get("prediction") else []),
            image_path=file_path,
        )
        radius = M.effective_radius_m(config, None)

        def age_hours(iso):
            try:
                return max((now - datetime.fromisoformat(iso)).total_seconds() / 3600.0, 0.0)
            except Exception:
                return 0.0

        candidates = []
        for c in CASES.values():
            if c["status"] not in ("open", "reopened"):
                continue
            if age_hours(c.get("last_reported_at") or "") >= config.match_window_days * 24.0:
                continue
            if M.haversine_m(inp.latitude, inp.longitude,
                             c["centroid_lat"], c["centroid_lon"]) > radius:
                continue
            members = _member_reports(c["id"])
            candidates.append(M.CaseSummary(
                case_id=c["id"], centroid_lat=c["centroid_lat"],
                centroid_lon=c["centroid_lon"],
                last_report_age_hours=age_hours(c.get("last_reported_at") or ""),
                classes=_case_classes(c["id"]),
                photo_paths=[p for p in
                             (_abs_photo(m.get("image_path")) for m in members[:3]) if p],
                status=c["status"], report_count=c["report_count"]))
        candidates = [s for s in candidates
                      if M.is_candidate_fresh(s.last_report_age_hours, config)]
        decision, best = M.match_report(inp, candidates, config)

        def new_case(recurrence_of=None, suggested=None):
            global NEXT_CASE_ID
            cid = NEXT_CASE_ID
            NEXT_CASE_ID += 1
            case = {"id": cid, "status": "open",
                    "centroid_lat": report["latitude"],
                    "centroid_lon": report["longitude"],
                    "first_reported_at": report["created_at"],
                    "last_reported_at": report["created_at"],
                    "report_count": 0, "distinct_reporters": 0,
                    "recurrence_of": recurrence_of,
                    "suggested_duplicate_of": suggested,
                    "created_at": now.isoformat()}
            CASES[cid] = case
            report["case_id"] = cid
            _recompute_case(case)
            return case

        if decision == "auto_merge" and best is not None:
            case = CASES.get(best.case_id)
            if case is None or case["status"] not in ("open", "reopened"):
                case = new_case()
                logged = "new_case"
            else:
                report["case_id"] = case["id"]
                _recompute_case(case)
                logged = "auto_merge"
            MERGE_LOG.append({"report_id": report["id"], "case_id": case["id"],
                              "decision": logged, "score": best.score,
                              "evidence": best.evidence,
                              "created_at": now.isoformat()})
            outcome = {"outcome": logged, "case_id": case["id"],
                       "score": best.score}
        else:
            recurrence_of = None
            cleaned = [c for c in CASES.values() if c["status"] == "cleaned"
                       and age_hours(c.get("last_reported_at") or "")
                       < config.match_window_days * 24.0]
            if cleaned:
                rec = M.find_recurrence_case(
                    inp, [M.CaseSummary(case_id=c["id"],
                                        centroid_lat=c["centroid_lat"],
                                        centroid_lon=c["centroid_lon"])
                          for c in cleaned], config)
                recurrence_of = rec
            suggested = best.case_id if decision == "suggest" and best else None
            case = new_case(recurrence_of, suggested)
            logged = ("suggested" if suggested is not None
                      else ("recurrence" if recurrence_of is not None else "new_case"))
            MERGE_LOG.append({"report_id": report["id"], "case_id": case["id"],
                              "decision": logged,
                              "score": best.score if best else None,
                              "evidence": best.evidence if best else {},
                              "created_at": now.isoformat()})
            outcome = {"outcome": logged, "case_id": case["id"],
                       "score": best.score if best else None,
                       "suggested_duplicate_of": suggested,
                       "recurrence_of": recurrence_of}
        return outcome
    except Exception as e:
        logger.warning("Case matching failed (non-fatal): %s", e)
        return outcome


def _sync_case_on_status(report):
    try:
        cid = report.get("case_id")
        if cid is None or cid not in CASES:
            return
        case = CASES[cid]
        members = _member_reports(cid)
        if not members:
            return
        pending = sum(1 for m in members if (m.get("status") or "").lower() != "cleaned")
        if pending == 0 and case["status"] != "cleaned":
            case["status"] = "cleaned"
        elif pending > 0 and case["status"] == "cleaned":
            case["status"] = "reopened"
    except Exception as e:
        logger.warning("Case status sync failed (non-fatal): %s", e)


class StatusUpdateOut(BaseModel):
    success: bool = True
    report_id: int
    status: str
    message: str


@app.get("/")
def root():
    return {
        "message": "Smart Garbage Detection API (DEMO mock) is running.",
        "health": "/health",
        "docs": "/docs",
        "reports": "/reports",
    }


@app.get("/health")
def health():
    model = _get_model()
    if model is not None:
        info = {"status": "loaded", "model_path": MODEL_PATH,
                "classes": model.names, "task": model.task}
    else:
        info = {"status": "mock (best.pt not found)",
                "classes": ["Plastic Waste", "Cardboard_Paper",
                            "Glass Waste", "Metal Waste", "Styrofoam"]}
    return {"status": "ok", "mode": "demo (no DB, real YOLO if weights present)", "model": info}


@app.get("/reports")
def read_reports(skip: int = 0, limit: int = 100):
    return REPORTS[skip: skip + limit]


@app.get("/reports-in-area")
def reports_in_area(min_lon: float, min_lat: float, max_lon: float, max_lat: float):
    return [r for r in REPORTS
            if min_lat <= r["latitude"] <= max_lat and min_lon <= r["longitude"] <= max_lon]


@app.get("/reports/stats/summary")
def stats_summary():
    per_day, per_class, per_status = {}, {}, {}
    for r in REPORTS:
        day = (r["created_at"] or "unknown")[:10]
        per_day[day] = per_day.get(day, 0) + 1
        per_class[r["prediction"]] = per_class.get(r["prediction"], 0) + 1
        per_status[r["status"]] = per_status.get(r["status"], 0) + 1
    return {"total": len(REPORTS), "per_day": dict(sorted(per_day.items())),
            "per_class": per_class, "per_status": per_status}


@app.get("/reports/stats/hotspots")
def hotspots():
    cells = {}
    for r in REPORTS:
        key = (round(r["latitude"], 2), round(r["longitude"], 2))
        cells[key] = cells.get(key, 0) + 1
    ranked = sorted(({"latitude": k[0], "longitude": k[1], "count": v}
                     for k, v in cells.items()),
                    key=lambda d: d["count"], reverse=True)
    return {"hotspots": ranked[:20]}


@app.get("/reports/by-status/{status}")
def by_status(status: str, skip: int = 0, limit: int = 100):
    normalized = (status or "").lower().strip()
    if normalized not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status. Use pending | cleaned")
    filtered = [r for r in REPORTS if r["status"] == normalized]
    return {"status_filter": normalized, "count": len(filtered),
            "reports": filtered[skip: skip + limit]}


@app.get("/reports/{report_id}")
def read_report(report_id: int):
    for r in REPORTS:
        if r["id"] == report_id:
            return r
    raise HTTPException(status_code=404, detail="Report not found")


# ---------- Real YOLOv8 inference (your trained best.pt) ----------
_model = None


def _get_model():
    """Load best.pt once; return None if weights/ultralytics are missing."""
    global _model
    if _model is not None:
        return _model
    try:
        if not os.path.exists(MODEL_PATH):
            logger.warning("MODEL_PATH not found: %s (using mock predictions)", MODEL_PATH)
            return None
        import torch
        from ultralytics import YOLO
        _orig_load = torch.load

        def _patched(*a, **k):
            k["weights_only"] = False
            return _orig_load(*a, **k)

        torch.load = _patched
        try:
            _model = YOLO(MODEL_PATH)
        finally:
            torch.load = _orig_load
        logger.info("YOLO model loaded: %s classes=%s", MODEL_PATH, _model.names)
    except Exception as e:
        logger.warning("YOLO load failed, using mock predictions: %s", e)
        _model = None
    return _model


# Tile-based detection (SAHI-style): small objects in piles die in the 640px
# resize, so images larger than TILE_SIZE are also scanned in overlapping
# windows and merged with NMS. Disable with TILE_DETECT=0.
TILE_ENABLED = os.getenv("TILE_DETECT", "1") == "1"
TILE_SIZE = int(os.getenv("TILE_SIZE", "640"))
TILE_OVERLAP = 0.2
TILE_MAX_DIM = int(os.getenv("TILE_MAX_DIM", "1280"))
# Per-class merge threshold: 0.5 left tile-duplicates standing (measured
# max same-object IoU ~0.49 on close-ups); 0.4 merges them.
TILE_IOU = float(os.getenv("TILE_IOU", "0.4"))
# Cross-class suppression: near-identical boxes (IoU >= this) keep only the
# top-confidence label instead of stacking e.g. Plastic+Metal on one can.
CROSS_CLASS_IOU = float(os.getenv("CROSS_CLASS_IOU", "0.8"))


def _iou(a, b):
    """Intersection-over-union of two [x1, y1, x2, y2] boxes."""
    ix = max(0.0, min(a[2], b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[3], b[3]) - max(a[1], b[1]))
    inter = ix * iy
    ua = (a[2] - a[0]) * (a[3] - a[1]) + (b[2] - b[0]) * (b[3] - b[1]) - inter
    return inter / ua if ua > 0 else 0.0


def _nms(boxes, scores, iou_thresh):
    """Greedy per-class NMS. boxes: (N,4) list, scores: (N,) list. Returns kept indices."""
    try:
        import torch
        from torchvision.ops import nms
        keep = nms(torch.tensor(boxes, dtype=torch.float32),
                   torch.tensor(scores, dtype=torch.float32), iou_thresh)
        return [int(i) for i in keep.tolist()]
    except Exception:
        pass
    # Pure-python fallback.
    order = sorted(range(len(boxes)), key=lambda i: scores[i], reverse=True)
    kept = []
    for i in order:
        keep = True
        for j in kept:
            ax1, ay1, ax2, ay2 = boxes[i]
            bx1, by1, bx2, by2 = boxes[j]
            ix = max(0.0, min(ax2, bx2) - max(ax1, bx1))
            iy = max(0.0, min(ay2, by2) - max(ay1, by1))
            inter = ix * iy
            ua = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
            if ua > 0 and inter / ua > iou_thresh:
                keep = False
                break
        if keep:
            kept.append(i)
    return kept


def _run_inference(image_path, return_raw=False):
    """Run best.pt on an image. Returns (detections, boxed_url_or_None).

    With return_raw=True, also returns every detection above the LOW floor
    (before per-class bars) for verification's uncertain band.
    """
    model = _get_model()
    if model is None:
        return ([], None, []) if return_raw else ([], None)
    import cv2
    floor = min([CONFIDENCE_THRESHOLD, *PER_CLASS_CONF.values()])
    names = model.names

    img = cv2.imread(image_path)
    if img is None:  # unreadable -> single direct pass (old behaviour)
        result = model(image_path, conf=floor, verbose=False)[0]
        boxes = result.boxes
        h, w = (result.orig_shape if hasattr(result, "orig_shape") else (0, 0))
        img_area = float(h * w) if h and w else 0.0
        raw_all = []
        for box in boxes:
            cid = int(box.cls[0])
            conf = float(box.conf[0])
            label = names.get(cid, f"Unknown-{cid}")
            x1, y1, x2, y2 = (round(float(c), 2) for c in box.xyxy[0].tolist())
            if img_area > 0 and (max(0.0, x2 - x1) * max(0.0, y2 - y1) / img_area) < 0.0008:
                continue
            raw_all.append({"class": label, "class_id": cid,
                            "confidence": round(conf, 4),
                            "bbox": [x1, y1, x2, y2]})
        raw_all.sort(key=lambda d: d["confidence"], reverse=True)
        kept = [d for d in raw_all
                if d["confidence"] >= PER_CLASS_CONF.get(d["class"], CONFIDENCE_THRESHOLD)]
        boxed = _draw_boxes(image_path, kept)
        if return_raw:
            return kept, boxed, raw_all
        return kept, boxed

    h0, w0 = img.shape[:2]
    scale = 1.0
    if max(h0, w0) > TILE_MAX_DIM:
        scale = TILE_MAX_DIM / float(max(h0, w0))
        img = cv2.resize(img, (int(w0 * scale), int(h0 * scale)))
    h, w = img.shape[:2]

    windows = [(0, 0, w, h)]  # full-image pass always runs
    if TILE_ENABLED and (w > TILE_SIZE or h > TILE_SIZE):
        stride = int(TILE_SIZE * (1.0 - TILE_OVERLAP))
        xs = list(range(0, max(w - TILE_SIZE, 1), stride)) + [max(w - TILE_SIZE, 0)]
        ys = list(range(0, max(h - TILE_SIZE, 1), stride)) + [max(h - TILE_SIZE, 0)]
        for y in dict.fromkeys(ys):
            for x in dict.fromkeys(xs):
                windows.append((x, y, min(x + TILE_SIZE, w), min(y + TILE_SIZE, h)))

    raw = []  # (class_id, conf, x1, y1, x2, y2) in working coords
    for (x1, y1, x2, y2) in windows:
        crop = img[y1:y2, x1:x2]
        if crop.size == 0:
            continue
        result = model(crop, conf=floor, verbose=False)[0]
        for box in result.boxes:
            bx1, by1, bx2, by2 = (float(c) for c in box.xyxy[0].tolist())
            raw.append((int(box.cls[0]), float(box.conf[0]),
                        bx1 + x1, by1 + y1, bx2 + x1, by2 + y1))

    # Per-class NMS merge, then cross-class suppression of near-identical
    # boxes, then map back to original-image coords.
    inv = 1.0 / scale
    by_class = {}
    for cid, conf, x1, y1, x2, y2 in raw:
        by_class.setdefault(cid, []).append(
            (conf, x1 * inv, y1 * inv, x2 * inv, y2 * inv))
    merged = []
    for cid, items in by_class.items():
        boxes = [[x1, y1, x2, y2] for _, x1, y1, x2, y2 in items]
        scores = [c for c, _, _, _, _ in items]
        for i in _nms(boxes, scores, TILE_IOU):
            c, x1, y1, x2, y2 = items[i]
            merged.append((cid, c, x1, y1, x2, y2))
    merged.sort(key=lambda m: -m[1])
    deduped = []
    for cid, conf, x1, y1, x2, y2 in merged:
        box = [x1, y1, x2, y2]
        if any(_iou(o[2:], box) >= CROSS_CLASS_IOU for o in deduped):
            continue
        deduped.append((cid, conf, x1, y1, x2, y2))
    merged = deduped

    img_area = float(w0 * h0)
    detections = []
    raw_all = []
    for cid, conf, x1, y1, x2, y2 in merged:
        label = names.get(cid, f"Unknown-{cid}")
        if (max(0.0, x2 - x1) * max(0.0, y2 - y1) / img_area) < 0.0008:
            continue  # tiny noise boxes are not evidence either way
        item = {"class": label, "class_id": cid,
                "confidence": round(conf, 4),
                "bbox": [round(x1, 2), round(y1, 2), round(x2, 2), round(y2, 2)]}
        raw_all.append(item)
        if conf < PER_CLASS_CONF.get(label, CONFIDENCE_THRESHOLD):
            continue
        detections.append(item)
    detections.sort(key=lambda d: d["confidence"], reverse=True)
    boxed_url = _draw_boxes(image_path, detections)
    if return_raw:
        return detections, boxed_url, raw_all
    return detections, boxed_url


def _draw_boxes(image_path, detections):
    """Draw kept detections and save the annotated image. Returns its URL."""
    if not detections:
        return None
    import cv2
    img = cv2.imread(image_path)
    if img is None:
        return None
    boxed_name = "boxed_" + os.path.basename(image_path)
    placed_labels = []  # (x, y, w, h) tag rects, to stagger overlapping tags
    for d in detections:
        x1, y1, x2, y2 = (int(c) for c in d["bbox"])
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 255), 2)
        label = f"{d['class']} {d['confidence']:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        lx, ly = x1, y1 - th - 8
        # Shift the tag down until it no longer covers a previous tag.
        while any(lx < px + pw and lx + tw + 4 > px and ly < py + ph and ly + th + 8 > py
                  for px, py, pw, ph in placed_labels):
            ly += th + 10
        placed_labels.append((lx, ly, tw + 4, th + 8))
        cv2.rectangle(img, (lx, ly), (lx + tw + 4, ly + th + 8), (0, 255, 255), -1)
        cv2.putText(img, label, (lx + 2, ly + th + 3),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
    cv2.imwrite(os.path.join(ANNOTATED_DIR, boxed_name), img)
    return f"/annotated/{boxed_name}"


def _severity(detections):
    if not detections:
        return 1
    count = len(detections)
    area = sum(max(0.0, d["bbox"][2] - d["bbox"][0]) * max(0.0, d["bbox"][3] - d["bbox"][1])
               for d in detections)
    frac = min(area / 409600.0, 3.0)
    return max(1, min(5, 1 + min(count - 1, 2) + (1 if frac > 0.25 else 0) + (1 if frac > 1.0 else 0)))


async def _mock_upload(file: UploadFile, latitude: float, longitude: float):
    global NEXT_ID
    if not (-90.0 <= latitude <= 90.0):
        raise HTTPException(status_code=400, detail="latitude must be between -90 and 90")
    if not (-180.0 <= longitude <= 180.0):
        raise HTTPException(status_code=400, detail="longitude must be between -180 and 180")
    # Save the uploaded photo so the dashboard can display it.
    ext = os.path.splitext(file.filename or "")[1].lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}:
        ext = ".jpg"
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())
    image_url = f"/uploads/{filename}"
    # Real inference with best.pt (falls back to mock if unavailable).
    try:
        detections, boxed_url = _run_inference(file_path)
    except Exception as e:
        logger.warning("Inference failed, storing as pending: %s", e)
        detections, boxed_url = [], None
    if detections:
        prediction, confidence = detections[0]["class"], detections[0]["confidence"]
    else:
        prediction, confidence = "No Waste Detected", 0.0
    severity = _severity(detections)
    report = {
        "id": NEXT_ID,
        "image_path": image_url,
        "boxed_image_path": boxed_url,
        "prediction": prediction,
        "confidence": confidence,
        "severity": severity,
        "status": "pending",
        "latitude": latitude,
        "longitude": longitude,
        "created_at": datetime.utcnow().isoformat(),
        "detections": {"count": len(detections), "items": detections},
        "case_id": None,
    }
    NEXT_ID += 1
    REPORTS.append(report)
    # Group with nearby reports of the same pile (never breaks uploads).
    case_outcome = _assign_case(report, file_path)
    return {
        "success": True,
        "report_id": report["id"],
        "prediction": prediction,
        "confidence": confidence,
        "severity": severity,
        "duplicate_of": None,
        "image_path": image_url,
        "boxed_image_path": boxed_url,
        "detections": {"count": len(detections), "items": detections[:5]} if detections else None,
        "case_id": case_outcome.get("case_id"),
        "match_outcome": case_outcome.get("outcome"),
        "suggested_duplicate_of": case_outcome.get("suggested_duplicate_of"),
        "recurrence_of": case_outcome.get("recurrence_of"),
    }


@app.post("/predict")
async def predict(file: UploadFile = File(...),
                  latitude: float = Form(...), longitude: float = Form(...)):
    return await _mock_upload(file, latitude, longitude)


@app.post("/upload-report")
async def upload_report(file: UploadFile = File(...),
                        latitude: float = Form(...), longitude: float = Form(...)):
    return await _mock_upload(file, latitude, longitude)


@app.patch("/reports/{report_id}/status", response_model=StatusUpdateOut)
def update_status(report_id: int, status: str,
                  reason: Optional[str] = None,
                  x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    # Admin-only: cleaner keys get 401 here. Cases should close through
    # POST /cases/{id}/verify-cleanup; direct cleaned edits need a reason
    # and are written to the audit log as admin overrides.
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401,
                            detail="Invalid or missing admin API key "
                                   "(demo key: demo-admin-key unless ADMIN_API_KEY is set)")
    status = (status or "").lower().strip()
    if status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status. Use pending | cleaned")
    if status == "cleaned" and not (reason or "").strip():
        raise HTTPException(
            status_code=400,
            detail="A reason is required to mark cleaned (?reason=...). "
                   "Cases should close through verification.")
    for r in REPORTS:
        if r["id"] == report_id:
            r["status"] = status
            if status == "cleaned":
                MERGE_LOG.append({"report_id": report_id, "case_id": r.get("case_id"),
                                  "decision": "admin_override_cleaned", "score": None,
                                  "evidence": {"reason": (reason or "").strip()},
                                  "created_at": datetime.utcnow().isoformat()})
            _sync_case_on_status(r)
            return {"success": True, "report_id": report_id, "status": status,
                    "message": f"Report status updated to '{status}'"}
    raise HTTPException(status_code=404, detail="Report not found")


class MergeBody(BaseModel):
    report_id: int


@app.get("/cases")
def list_cases(status: Optional[str] = None, min_reports: int = 0,
               min_lon: Optional[float] = None, min_lat: Optional[float] = None,
               max_lon: Optional[float] = None, max_lat: Optional[float] = None,
               sort: Optional[str] = None):
    """One row per real-world problem, with report_count for map badges.

    sort=priority ranks open cases by the transparent priority score
    (computed fresh, since days_open changes without new reports).
    """
    out = list(CASES.values())
    if status:
        normalized = status.lower().strip()
        if normalized not in CASE_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status filter")
        out = [c for c in out if c["status"] == normalized]
    if min_reports > 0:
        out = [c for c in out if c.get("report_count", 0) >= min_reports]
    if None not in (min_lon, min_lat, max_lon, max_lat):
        out = [c for c in out
               if c.get("centroid_lat") is not None
               and min_lat <= c["centroid_lat"] <= max_lat
               and min_lon <= c["centroid_lon"] <= max_lon]
    out.sort(key=lambda c: c.get("last_reported_at") or "", reverse=True)
    rows = [_serialize_case(c) for c in out[:500]]
    if (sort or "").lower() == "priority":
        for row, case in zip(rows, out[:500]):
            row["priority"] = _case_priority(case)
        rows.sort(key=lambda r: ((r.get("priority") or {}).get("score", 0)),
                  reverse=True)
    return rows


@app.get("/cases/{case_id}")
def read_case(case_id: int):
    """Case detail: member reports, photos and merge evidence."""
    case = CASES.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    members = sorted(_member_reports(case_id),
                     key=lambda r: r.get("created_at") or "", reverse=True)
    log = [e for e in MERGE_LOG if e.get("case_id") == case_id][-50:]
    return {**_serialize_case(case), "reports": members, "merge_log": log,
            "priority": _case_priority(case)}


def _require_admin(x_api_key: Optional[str]):
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing admin API key")


@app.post("/cases/{case_id}/merge")
def merge_into_case(case_id: int, body: MergeBody,
                    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    """Admin: force a report into a case."""
    _require_admin(x_api_key)
    case = CASES.get(case_id)
    report = next((r for r in REPORTS if r["id"] == body.report_id), None)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    report["case_id"] = case_id
    if case["status"] == "cleaned":
        case["status"] = "reopened"
    _recompute_case(case)
    MERGE_LOG.append({"report_id": report["id"], "case_id": case_id,
                      "decision": "manual_merge", "score": None, "evidence": {},
                      "created_at": datetime.utcnow().isoformat()})
    return {"success": True, "case_id": case_id, "report_count": case["report_count"]}


@app.post("/reports/{report_id}/split")
def split_from_case(report_id: int,
                    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    """Admin: pull a report out of its case into a fresh single-report case."""
    _require_admin(x_api_key)
    global NEXT_CASE_ID
    report = next((r for r in REPORTS if r["id"] == report_id), None)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    old_case_id = report.get("case_id")
    now = datetime.utcnow().isoformat()
    cid = NEXT_CASE_ID
    NEXT_CASE_ID += 1
    case = {"id": cid, "status": "open",
            "centroid_lat": report["latitude"], "centroid_lon": report["longitude"],
            "first_reported_at": report["created_at"],
            "last_reported_at": report["created_at"],
            "report_count": 0, "distinct_reporters": 0,
            "recurrence_of": None, "suggested_duplicate_of": None,
            "created_at": now}
    CASES[cid] = case
    report["case_id"] = cid
    _recompute_case(case)
    MERGE_LOG.append({"report_id": report_id, "case_id": cid,
                      "decision": "manual_split", "score": None,
                      "evidence": {"from_case_id": old_case_id},
                      "created_at": now})
    if old_case_id in CASES:
        _recompute_case(CASES[old_case_id])
    return {"success": True, "report_id": report_id, "new_case_id": cid}


# ---------- Cleanup verification (cases close only through here) ----------
VERIFICATIONS = []
NEXT_VERIFY_ID = 1

try:
    from backend.verification import checks as verify_checks
    VERIFY_CONFIG = verify_checks.config_from_env()
except Exception as e:
    logging.getLogger(__name__).warning("Verification unavailable: %s", e)
    verify_checks = None
    VERIFY_CONFIG = None


def _serialize_verification(v):
    return {
        "id": v["id"],
        "case_id": v["case_id"],
        "cleaner_id": v.get("cleaner_id"),
        "attempt_no": v.get("attempt_no", 1),
        "photos": [f"/uploads/{p}" for p in (v.get("photos") or [])],
        "checks": v.get("checks"),
        "decision": v.get("decision"),
        "spot_checked": v.get("spot_checked"),
        "reviewed_by": v.get("reviewed_by"),
        "reviewed_at": v.get("reviewed_at"),
        "review_reason": v.get("review_reason"),
        "created_at": v.get("created_at"),
    }


def _verify_detect_fn(image_path):
    """Demo detector for verification: raw hits at the LOW floor plus a
    boxed image of the production-bar hits."""
    if _get_model() is None:
        raise RuntimeError("Detection model is not available")
    kept, boxed_url, raw_all = _run_inference(image_path, return_raw=True)
    return raw_all, boxed_url


def _close_case_demo(case, verification_id, reviewer, decision_label):
    now = datetime.utcnow().isoformat()
    case["status"] = "cleaned"
    case["closed_at"] = now
    case["closing_verification_id"] = verification_id
    for m in _member_reports(case["id"]):
        m["status"] = "cleaned"
    MERGE_LOG.append({"report_id": None, "case_id": case["id"],
                      "decision": decision_label, "score": None,
                      "evidence": {"verification_id": verification_id,
                                   "reviewed_by": reviewer},
                      "created_at": now})


def _who_from_key(x_api_key):
    if x_api_key == ADMIN_API_KEY:
        return "admin"
    return f"cleaner:{(x_api_key or '')[:6]}"


@app.post("/cases/{case_id}/verify-cleanup")
async def verify_cleanup(
    case_id: int,
    files: List[UploadFile] = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    captured_at: Optional[str] = Form(None),
    cleaner_id: Optional[str] = Form(None),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """Cleaner flow: submit 1..N after-photos proving the pile is gone.

    HONEST LIMIT: the detector cannot prove absence — a missed detection
    can produce a false PASSED, which is why uncertain evidence routes to
    human review and a fraction of passes are spot-checked.
    """
    if verify_checks is None or VERIFY_CONFIG is None:
        raise HTTPException(status_code=503, detail="Verification engine unavailable")
    who = _who_from_key(x_api_key)
    if x_api_key != ADMIN_API_KEY and x_api_key not in CLEANER_API_KEYS:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")
    case = CASES.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    if case.get("status") == "cleaned":
        raise HTTPException(status_code=400, detail="Case is already cleaned")
    if not (VERIFY_CONFIG.min_photos <= len(files) <= VERIFY_CONFIG.max_photos):
        raise HTTPException(
            status_code=400,
            detail=f"Send between {VERIFY_CONFIG.min_photos} and "
                   f"{VERIFY_CONFIG.max_photos} after-photos, got {len(files)}.")
    now = datetime.utcnow()
    recent = sum(1 for v in VERIFICATIONS
                 if v["case_id"] == case_id
                 and (now - datetime.fromisoformat(v["created_at"])).total_seconds() < 3600)
    if recent >= VERIFY_CONFIG.max_attempts_per_hour:
        raise HTTPException(
            status_code=429,
            detail=f"Too many verification attempts for case {case_id}; try again later.")

    app_captured = None
    if captured_at:
        try:
            app_captured = datetime.fromisoformat(captured_at)
        except ValueError:
            raise HTTPException(status_code=400, detail="captured_at must be ISO-8601")
    saved, after_photos = [], []
    for f in files:
        ext = os.path.splitext(f.filename or "")[1].lower() or ".jpg"
        if ext not in {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}:
            ext = ".jpg"
        filename = f"verify_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}{ext}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        with open(file_path, "wb") as buffer:
            buffer.write(await f.read())
        saved.append(filename)
        after_photos.append(verify_checks.AfterPhoto(
            path=file_path, latitude=latitude, longitude=longitude,
            captured_at=app_captured))

    members = _member_reports(case_id)
    before_paths = [p for p in
                    (_abs_photo(m.get("image_path")) for m in members[:6]) if p]
    prior_afters = []
    for v in VERIFICATIONS:
        if v["case_id"] == case_id:
            for p in (v.get("photos") or [])[-6:]:
                full = os.path.join(UPLOAD_DIR, os.path.basename(p))
                if os.path.exists(full):
                    prior_afters.append(full)
    classes = sorted({m["prediction"] for m in members if m.get("prediction")})
    req = verify_checks.VerifyRequest(
        case_id=case_id, centroid_lat=case["centroid_lat"],
        centroid_lon=case["centroid_lon"], case_classes=classes,
        case_first_reported_at=(datetime.fromisoformat(case["first_reported_at"])
                                if case.get("first_reported_at") else None),
        before_photo_paths=before_paths,
        prior_after_photo_paths=prior_afters,
        photos=after_photos, cleaner_id=cleaner_id or who, now=now,
        case_class_bars=dict(PER_CLASS_CONF))
    outcome = verify_checks.decide_verification(req, _verify_detect_fn, VERIFY_CONFIG)

    global NEXT_VERIFY_ID
    vid = NEXT_VERIFY_ID
    NEXT_VERIFY_ID += 1
    row = {"id": vid, "case_id": case_id, "cleaner_id": cleaner_id or who,
           "attempt_no": sum(1 for v in VERIFICATIONS if v["case_id"] == case_id) + 1,
           "photos": saved, "checks": outcome.checks, "decision": outcome.decision,
           "spot_checked": ("; ".join(outcome.needs_review_reasons)
                            if outcome.spot_checked else None),
           "reviewed_by": None, "reviewed_at": None, "review_reason": None,
           "created_at": now.isoformat()}
    VERIFICATIONS.append(row)
    if outcome.decision == verify_checks.PASSED:
        _close_case_demo(case, vid, None, "verification_passed")
    return {
        "success": True, "verification_id": vid, "attempt_no": row["attempt_no"],
        "case_id": case_id, "case_status": case["status"],
        "decision": outcome.decision, "checks": outcome.checks,
        "annotated_images": outcome.annotated_paths,
        "needs_review_reasons": outcome.needs_review_reasons,
        "spot_checked": outcome.spot_checked,
        "limits": verify_checks.HONEST_LIMIT,
    }


@app.get("/verifications")
def list_verifications(decision: Optional[str] = None,
                       case_id: Optional[int] = None,
                       x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    """Admin review queue (e.g. ?decision=needs_review)."""
    _require_admin(x_api_key)
    out = list(VERIFICATIONS)
    if decision:
        out = [v for v in out if v["decision"] == decision.lower().strip()]
    if case_id is not None:
        out = [v for v in out if v["case_id"] == case_id]
    out.sort(key=lambda v: v["created_at"], reverse=True)
    return [_serialize_verification(v) for v in out[:200]]


@app.post("/verifications/{verification_id}/review")
def review_verification(verification_id: int, approve: bool,
                        reason: Optional[str] = None,
                        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    """Admin approves/rejects a NEEDS_REVIEW verification. Reason required."""
    _require_admin(x_api_key)
    if not (reason or "").strip():
        raise HTTPException(status_code=400, detail="A review reason is required.")
    row = next((v for v in VERIFICATIONS if v["id"] == verification_id), None)
    if row is None:
        raise HTTPException(status_code=404, detail="Verification not found")
    if row["decision"] != "needs_review":
        raise HTTPException(
            status_code=400,
            detail=f"Only needs_review verifications can be reviewed (is {row['decision']})")
    row["reviewed_by"] = "admin"
    row["reviewed_at"] = datetime.utcnow().isoformat()
    row["review_reason"] = reason.strip()
    case = CASES.get(row["case_id"])
    if approve and case is not None and case.get("status") != "cleaned":
        _close_case_demo(case, row["id"], "admin", "verification_approved")
        row["decision"] = "passed"
    else:
        MERGE_LOG.append({"report_id": None, "case_id": row["case_id"],
                          "decision": "verification_rejected", "score": None,
                          "evidence": {"verification_id": row["id"],
                                       "reviewed_by": "admin",
                                       "reason": reason.strip()},
                          "created_at": row["reviewed_at"]})
        row["decision"] = "failed_still_litter"
    return {"success": True, "verification": _serialize_verification(row)}


@app.get("/cases/{case_id}/priority")
def case_priority(case_id: int):
    """Full score breakdown for one case (computed fresh)."""
    case = CASES.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found")
    return {"case_id": case_id, **(_case_priority(case) or {})}


@app.get("/priority/weights")
def priority_weights(x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    """Admin: read the current priority weights. Changes are config-only
    (PRIORITY_W_* env vars); there is no runtime setter by design."""
    _require_admin(x_api_key)
    return {"version": priority_score.SCORE_VERSION if _MATCHER_AVAILABLE else None,
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("mock_app:app", host="0.0.0.0", port=8000, reload=False)
