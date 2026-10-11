"""Database orchestration for the cases (duplicate-merging) feature.

Pure scoring lives in matching.py (unit-tested). This module does the
PostGIS candidate lookup, transactional merge, audit logging, backfill and
admin merge/split. Every public function is failure-safe by contract: the
upload hook wraps calls in try/except so matching can never break uploads.
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timedelta
from typing import List, Optional

from geoalchemy2 import Geometry
from geoalchemy2.shape import to_shape
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .. import config as app_config
from .. import models
from ..priority.score import (
    SCORE_VERSION,
    CaseFacts,
    PriorityConfig,
    config_from_env as priority_config_from_env,
    score_case,
)
from .matching import (
    CaseSummary,
    MatchConfig,
    ReportInput,
    config_from_env,
    effective_radius_m,
    find_recurrence_case,
    is_candidate_fresh,
    match_report,
)

logger = logging.getLogger(__name__)

MAX_CASE_PHOTOS = 3  # pHash comparisons per candidate (CPU guard)


# --------------------------------------------------------------------------
# Advisory-lock key: one lock per ~40 m geo-cell serialises concurrent
# uploads of the same pile so two races cannot create two cases.
# Stable across processes (md5, not hash()).
# --------------------------------------------------------------------------

def merge_lock_key(latitude: float, longitude: float, cell_m: float = 40.0) -> int:
    from .matching import EARTH_RADIUS_M
    import math
    cell_deg = (cell_m / EARTH_RADIUS_M) * (180.0 / math.pi)
    key = f"{round(latitude / cell_deg)}:{round(longitude / cell_deg)}"
    return int(hashlib.md5(key.encode()).hexdigest(), 16) % (2 ** 63 - 1)


def _acquire_cell_lock(db: Session, latitude: float, longitude: float) -> None:
    """Postgres transaction-scoped advisory lock for this geo-cell."""
    key = merge_lock_key(latitude, longitude)
    db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": key})


# --------------------------------------------------------------------------
# Summaries / inputs
# --------------------------------------------------------------------------

def _point_of(report: models.GarbageReport):
    return to_shape(report.geom)


def _classes_of(report: models.GarbageReport) -> List[str]:
    classes = []
    if report.prediction:
        classes.append(report.prediction)
    dets = report.detections if isinstance(report.detections, dict) else {}
    for item in (dets.get("all") or []):
        if isinstance(item, dict) and item.get("class"):
            classes.append(str(item["class"]))
    primary = dets.get("primary") if isinstance(dets, dict) else None
    if isinstance(primary, dict) and primary.get("class"):
        classes.append(str(primary["class"]))
    # Preserve order, drop duplicates.
    return list(dict.fromkeys(classes))


def _photo_abs_path(stored_filename: Optional[str]) -> Optional[str]:
    if not stored_filename:
        return None
    # Stored values are either bare filenames or "/uploads/<file>" URLs.
    name = os.path.basename(stored_filename)
    path = os.path.join(app_config.UPLOAD_DIR, name)
    return path if os.path.exists(path) else None


def _age_hours(ts: Optional[datetime], now: datetime) -> float:
    if ts is None:
        return 0.0
    try:
        return max((now - ts).total_seconds() / 3600.0, 0.0)
    except Exception:
        return 0.0


def _case_summary(case: models.Case, db: Session, now: datetime) -> CaseSummary:
    members = (
        db.query(models.GarbageReport)
        .filter(models.GarbageReport.case_id == case.id)
        .all()
    )
    classes: List[str] = []
    photos: List[str] = []
    for m in members:
        for c in _classes_of(m):
            if c not in classes:
                classes.append(c)
        if len(photos) < MAX_CASE_PHOTOS:
            p = _photo_abs_path(m.image_path)
            if p:
                photos.append(p)
    pt = to_shape(case.centroid) if case.centroid is not None else None
    return CaseSummary(
        case_id=case.id,
        centroid_lat=pt.y if pt is not None else 0.0,
        centroid_lon=pt.x if pt is not None else 0.0,
        last_report_age_hours=_age_hours(case.last_reported_at, now),
        classes=classes,
        photo_paths=photos,
        status=case.status,
        report_count=case.report_count,
    )


def _report_input(report: models.GarbageReport, image_abs_path: Optional[str],
                  gps_accuracy_m: Optional[float] = None) -> ReportInput:
    now = datetime.utcnow()
    pt = _point_of(report)
    return ReportInput(
        latitude=pt.y,
        longitude=pt.x,
        age_hours=_age_hours(report.created_at, now),
        classes=_classes_of(report),
        image_path=image_abs_path,
        gps_accuracy_m=gps_accuracy_m,
        reporter_id=str(report.user_id) if report.user_id is not None else None,
    )


# --------------------------------------------------------------------------
# Candidate lookup
# --------------------------------------------------------------------------

def _candidate_cases(db: Session, latitude: float, longitude: float,
                     radius_m: float, window: timedelta, now: datetime,
                     lock_rows: bool = True):
    """Open/reopened cases near the point and active within the window."""
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    q = (
        db.query(models.Case)
        .filter(models.Case.status.in_(("open", "reopened")))
        .filter(models.Case.last_reported_at >= now - window)
        .filter(
            func.ST_DWithin(
                models.Case.centroid.cast(Geometry("GEOGRAPHY")),
                point.cast(Geometry("GEOGRAPHY")),
                radius_m,
            )
        )
    )
    if lock_rows:
        q = q.with_for_update()
    return q.all()


def _recent_cleaned_cases(db: Session, latitude: float, longitude: float,
                          radius_m: float, window: timedelta, now: datetime):
    point = func.ST_SetSRID(func.ST_MakePoint(longitude, latitude), 4326)
    return (
        db.query(models.Case)
        .filter(models.Case.status == "cleaned")
        .filter(models.Case.last_reported_at >= now - window)
        .filter(
            func.ST_DWithin(
                models.Case.centroid.cast(Geometry("GEOGRAPHY")),
                point.cast(Geometry("GEOGRAPHY")),
                radius_m,
            )
        )
        .all()
    )


# --------------------------------------------------------------------------
# Case maintenance
# --------------------------------------------------------------------------

def _recompute_case(db: Session, case: models.Case) -> None:
    """Refresh centroid/counts/timestamps/reporters from members. One flush."""
    members = (
        db.query(models.GarbageReport)
        .filter(models.GarbageReport.case_id == case.id)
        .all()
    )
    if not members:
        case.report_count = 0
        db.flush()
        return
    lons, lats, reporters = [], [], set()
    first, last = None, None
    for m in members:
        try:
            pt = _point_of(m)
            lons.append(pt.x)
            lats.append(pt.y)
        except Exception:
            continue
        if m.user_id is not None:
            reporters.add(m.user_id)
        if m.created_at is not None:
            first = m.created_at if first is None or m.created_at < first else first
            last = m.created_at if last is None or m.created_at > last else last
    if lons:
        from geoalchemy2.shape import from_shape
        from shapely.geometry import Point
        case.centroid = from_shape(
            Point(sum(lons) / len(lons), sum(lats) / len(lats)), srid=4326)
    case.report_count = len(members)
    # distinct_reporters counts distinct non-null user_ids. NOTE: the mobile
    # app currently sends no reporter id and crud never sets user_id, so this
    # reads 0 until reporter ids are wired through uploads (see README note).
    case.distinct_reporters = len(reporters)
    case.first_reported_at = first
    case.last_reported_at = last
    case.score_version = SCORE_VERSION
    db.flush()


def _log(db: Session, report_id: Optional[int], case_id: Optional[int],
         decision: str, score: Optional[float], evidence: Optional[dict]) -> None:
    db.add(models.CaseMergeLog(
        report_id=report_id, case_id=case_id, decision=decision,
        score=score, evidence=evidence or {}))
    db.flush()


def _create_case(db: Session, report: models.GarbageReport, now: datetime,
                 recurrence_of: Optional[int] = None,
                 suggested_duplicate_of: Optional[int] = None) -> models.Case:
    case = models.Case(
        centroid=report.geom,
        status="open",
        first_reported_at=report.created_at or now,
        last_reported_at=report.created_at or now,
        report_count=0,
        distinct_reporters=0,
        recurrence_of=recurrence_of,
        suggested_duplicate_of=suggested_duplicate_of,
        created_at=now,
    )
    db.add(case)
    db.flush()  # assign id
    report.case_id = case.id
    db.flush()
    _recompute_case(db, case)
    return case


# --------------------------------------------------------------------------
# Main entry point: call after a report row exists (detection succeeded).
# --------------------------------------------------------------------------

def assign_report_to_case(db: Session, report: models.GarbageReport,
                          image_abs_path: Optional[str] = None,
                          gps_accuracy_m: Optional[float] = None,
                          config: Optional[MatchConfig] = None) -> dict:
    """Match one report into the case graph. Returns an outcome dict.

    Never raises for matching reasons: unexpected errors roll back to the
    pre-match savepoint and return {"outcome": "skipped", ...} so the
    upload endpoint still succeeds.
    """
    config = config or config_from_env()
    now = datetime.utcnow()
    outcome: dict = {"outcome": "skipped", "case_id": report.case_id}
    savepoint = db.begin_nested()
    try:
        pt = _point_of(report)
        lat, lon = pt.y, pt.x
        _acquire_cell_lock(db, lat, lon)

        radius = effective_radius_m(config, gps_accuracy_m)
        window = timedelta(days=config.match_window_days)
        report_in = _report_input(report, image_abs_path, gps_accuracy_m)

        candidates = _candidate_cases(db, lat, lon, radius, window, now)
        summaries = [s for s in (_case_summary(c, db, now) for c in candidates)
                     if is_candidate_fresh(s.last_report_age_hours, config)]
        decision, best = match_report(report_in, summaries, config)

        if decision == "auto_merge" and best is not None:
            case = db.query(models.Case).filter(
                models.Case.id == best.case_id).with_for_update().first()
            if case is None or case.status not in ("open", "reopened"):
                raise RuntimeError("merge target vanished; retry as new case")
            report.case_id = case.id
            db.flush()
            _recompute_case(db, case)
            _log(db, report.id, case.id, "auto_merged", best.score, best.evidence)
            outcome = {"outcome": "merged", "case_id": case.id,
                       "score": best.score, "evidence": best.evidence}
        else:
            recurrence_of = None
            if decision in ("suggest", "new_case"):
                cleaned = _recent_cleaned_cases(db, lat, lon, radius, window, now)
                cleaned_summaries = [_case_summary(c, db, now) for c in cleaned]
                recurrence_of = find_recurrence_case(report_in, cleaned_summaries, config)
            suggested = best.case_id if decision == "suggest" and best else None
            case = _create_case(db, report, now, recurrence_of, suggested)
            logged = ("suggested" if suggested is not None
                      else ("recurrence" if recurrence_of is not None else "new_case"))
            _log(db, report.id, case.id, logged,
                 best.score if best else None,
                 best.evidence if best else {"recurrence_of": recurrence_of})
            outcome = {"outcome": logged, "case_id": case.id,
                       "score": best.score if best else None,
                       "suggested_duplicate_of": suggested,
                       "recurrence_of": recurrence_of}

        savepoint.commit()
        db.commit()
        return outcome
    except Exception as e:
        logger.warning("Case matching failed for report %s (non-fatal): %s",
                       getattr(report, "id", "?"), e)
        try:
            savepoint.rollback()
        except Exception:
            pass
        try:
            db.rollback()
        except Exception:
            pass
        outcome["error"] = str(e)
        return outcome


# --------------------------------------------------------------------------
# Backfill + admin ops
# --------------------------------------------------------------------------

def backfill_caseless_reports(db: Session,
                              config: Optional[MatchConfig] = None,
                              limit: Optional[int] = None) -> dict:
    """Run the matcher over all existing reports in time order.

    Usage:  cd backend-database && python -m backend.cases.backfill
    """
    config = config or config_from_env()
    q = (db.query(models.GarbageReport)
           .filter(models.GarbageReport.case_id.is_(None))
           .order_by(models.GarbageReport.created_at.asc(),
                      models.GarbageReport.id.asc()))
    if limit:
        q = q.limit(limit)
    stats = {"merged": 0, "suggested": 0, "new_case": 0, "recurrence": 0, "skipped": 0}
    for report in q.all():
        res = assign_report_to_case(
            db, report, image_abs_path=_photo_abs_path(report.image_path), config=config)
        stats[res.get("outcome", "skipped")] = stats.get(res.get("outcome", "skipped"), 0) + 1
    return stats


def manual_merge(db: Session, case_id: int, report_id: int) -> models.Case:
    """Admin: force a report into a case. Logged as manual_merge."""
    case = db.query(models.Case).filter(
        models.Case.id == case_id).with_for_update().first()
    report = db.query(models.GarbageReport).filter(
        models.GarbageReport.id == report_id).first()
    if case is None:
        raise ValueError(f"case {case_id} not found")
    if report is None:
        raise ValueError(f"report {report_id} not found")
    if report.case_id == case.id:
        return case
    report.case_id = case.id
    if case.status == "cleaned":
        case.status = "reopened"
    db.flush()
    _recompute_case(db, case)
    _log(db, report.id, case.id, "manual_merge", None, {})
    # Recompute the report's previous case, if any.
    db.commit()
    return case


def split_report(db: Session, report_id: int) -> models.Case:
    """Admin: pull a report out of its case into a fresh single-report case."""
    report = db.query(models.GarbageReport).filter(
        models.GarbageReport.id == report_id).first()
    if report is None:
        raise ValueError(f"report {report_id} not found")
    old_case_id = report.case_id
    now = datetime.utcnow()
    new_case = _create_case(db, report, now)
    _log(db, report.id, new_case.id, "manual_split",
         None, {"from_case_id": old_case_id})
    if old_case_id is not None:
        old = db.query(models.Case).filter(models.Case.id == old_case_id).first()
        if old is not None:
            _recompute_case(db, old)
    db.commit()
    return new_case


def sync_case_on_report_status(db: Session, report: models.GarbageReport) -> None:
    """Keep case status consistent when a report is cleaned/reopened.

    All members cleaned -> case cleaned. A pending report on a cleaned
    case -> case reopened. Best-effort; never raises.
    """
    try:
        if report.case_id is None:
            return
        case = db.query(models.Case).filter(
            models.Case.id == report.case_id).first()
        if case is None:
            return
        members = (db.query(models.GarbageReport)
                     .filter(models.GarbageReport.case_id == case.id).all())
        if not members:
            return
        pending = sum(1 for m in members if (m.status or "").lower() != "cleaned")
        if pending == 0 and case.status != "cleaned":
            case.status = "cleaned"
            db.commit()
        elif pending > 0 and case.status == "cleaned":
            case.status = "reopened"
            db.commit()
    except Exception as e:
        logger.warning("Case status sync failed (non-fatal): %s", e)
        try:
            db.rollback()
        except Exception:
            pass


# --------------------------------------------------------------------------
# Priority scoring adapter (row -> CaseFacts -> score).
# Age is computed at query time: days_open changes without new reports.
# --------------------------------------------------------------------------

def _image_dims(abs_path: Optional[str]):
    """(width, height) of a stored photo, or None if unreadable."""
    if not abs_path or not os.path.exists(abs_path):
        return None
    try:
        from PIL import Image
        with Image.open(abs_path) as img:
            return img.size
    except Exception:
        return None


def build_case_facts(db: Session, case: models.Case,
                     config: Optional[PriorityConfig] = None) -> CaseFacts:
    """Aggregate member rows into CaseFacts.

    Anti-double-counting rule: item count, covered area and class mix all
    come from the single member report with the highest detected item
    count — never summed across reports of the same pile.
    """
    members = (
        db.query(models.GarbageReport)
        .filter(models.GarbageReport.case_id == case.id)
        .all()
    )
    if not members:
        return CaseFacts()

    def count_of(m: models.GarbageReport) -> int:
        dets = m.detections if isinstance(m.detections, dict) else {}
        try:
            return int(dets.get("count") or len(dets.get("items") or []) or 0)
        except (TypeError, ValueError):
            return 0

    best = max(members, key=count_of)
    dets = best.detections if isinstance(best.detections, dict) else {}
    items = [d for d in (dets.get("items") or []) if isinstance(d, dict)]
    classes = [str(d["class"]) for d in items if d.get("class")]
    if best.prediction and best.prediction not in classes:
        classes.append(best.prediction)

    area_frac = 0.0
    dims = _image_dims(_photo_abs_path(best.image_path))
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

    reporters = {m.user_id for m in members if m.user_id is not None}
    now = datetime.utcnow()
    days_open = 0.0
    if case.first_reported_at is not None:
        try:
            days_open = max((now - case.first_reported_at).total_seconds() / 86400.0, 0.0)
        except Exception:
            days_open = 0.0
    return CaseFacts(
        item_count=count_of(best),
        covered_area_frac=area_frac,
        classes=classes,
        distinct_reporters=len(reporters),
        days_open=days_open,
        location_sensitivity=1.0,  # hook: no location data invented
    )


def score_case_response(db: Session, case: models.Case,
                        config: Optional[PriorityConfig] = None) -> dict:
    """Full {score, components, version} breakdown for one case."""
    config = config or priority_config_from_env()
    return score_case(build_case_facts(db, case, config), config)
