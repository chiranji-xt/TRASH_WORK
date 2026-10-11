"""Pure cleanup-verification checks. No DB imports by design.

A case closes only through verification (or a reasoned admin override).
The decision engine here is fully deterministic and takes an injected
``detect_fn`` so tests run with a mocked detector and production passes
the real YOLO wrapper.

HONEST LIMIT (also returned in API responses): the detector cannot prove
absence. A missed detection means a false PASSED is possible. That is why
uncertain evidence routes to NEEDS_REVIEW (never auto-close) and why a
configurable fraction of passes are randomly spot-checked by a human.
"""

from __future__ import annotations

import math
import os
import random
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from ..cases.matching import average_hash, hamming_distance, haversine_m

VERIFY_VERSION = "1.0"

# Decisions
PASSED = "passed"
FAILED_STILL_LITTER = "failed_still_litter"
NEEDS_REVIEW = "needs_review"
REJECTED_REUSE = "rejected_reuse"


@dataclass
class VerifyConfig:
    verify_radius_m: float = 50.0
    verify_max_age_min: float = 60.0
    exif_gps_tolerance_m: float = 100.0
    reuse_hamming_threshold: int = 5  # <= this = near-identical photo
    min_photos: int = 1
    max_photos: int = 3
    low_confidence: float = 0.15  # below production bars but above this = uncertain
    blur_variance_min: float = 30.0  # Laplacian variance floor (sharp enough)
    max_attempts_per_hour: int = 5
    spot_check_rate: float = 0.1


def config_from_env(prefix: str = "VERIFY_") -> VerifyConfig:
    def _f(name: str, default: float) -> float:
        try:
            return float(os.getenv(prefix + name, str(default)))
        except (TypeError, ValueError):
            return default

    return VerifyConfig(
        verify_radius_m=_f("RADIUS_M", 50.0),
        verify_max_age_min=_f("MAX_AGE_MIN", 60.0),
        exif_gps_tolerance_m=_f("EXIF_GPS_TOLERANCE_M", 100.0),
        max_attempts_per_hour=int(_f("MAX_ATTEMPTS_PER_HOUR", 5)),
        spot_check_rate=_f("SPOT_CHECK_RATE", 0.1),
    )


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------

@dataclass
class AfterPhoto:
    """One submitted after-photo with app-provided metadata."""

    path: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    captured_at: Optional[datetime] = None  # app capture time, if sent


@dataclass
class VerifyRequest:
    case_id: int
    centroid_lat: float
    centroid_lon: float
    case_classes: Sequence[str] = field(default_factory=list)
    case_first_reported_at: Optional[datetime] = None
    before_photo_paths: Sequence[str] = field(default_factory=list)
    prior_after_photo_paths: Sequence[str] = field(default_factory=list)
    photos: Sequence[AfterPhoto] = field(default_factory=list)
    cleaner_id: Optional[str] = None
    now: Optional[datetime] = None
    # Production per-class bars (same thresholds as live detection).
    # A case-class hit at/above its bar FAILS; between LOW and the bar it
    # is UNCERTAIN (possible weak litter, never auto-close).
    case_class_bars: Dict[str, float] = field(default_factory=dict)


# --------------------------------------------------------------------------
# EXIF helpers (PIL only; missing EXIF is normal, never fatal)
# --------------------------------------------------------------------------

def read_exif(path: str) -> dict:
    """{gps: (lat, lon) | None, taken_at: datetime | None}."""
    out: dict = {"gps": None, "taken_at": None}
    try:
        from PIL import Image
        from PIL.ExifTags import GPSTAGS, TAGS

        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return out
            tags = {TAGS.get(k, k): v for k, v in exif.items()}
            taken = tags.get("DateTimeOriginal") or tags.get("DateTime")
            if taken:
                try:
                    out["taken_at"] = datetime.strptime(
                        str(taken), "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    pass
            gps_info = tags.get("GPSInfo")
            if gps_info:
                gps = {GPSTAGS.get(k, k): v for k, v in gps_info.items()}
                out["gps"] = _gps_to_deg(gps)
    except Exception:
        pass
    return out


def _gps_to_deg(gps: dict) -> Optional[Tuple[float, float]]:
    try:
        def conv(v):
            d, m, s = (float(x) for x in v)
            return d + m / 60.0 + s / 3600.0

        lat = conv(gps["GPSLatitude"])
        if str(gps.get("GPSLatitudeRef", "N")).upper().startswith("S"):
            lat = -lat
        lon = conv(gps["GPSLongitude"])
        if str(gps.get("GPSLongitudeRef", "E")).upper().startswith("W"):
            lon = -lon
        return (lat, lon)
    except Exception:
        return None


def blur_variance(path: str) -> Optional[float]:
    """Laplacian variance (sharpness). None if unreadable/no cv2."""
    try:
        import cv2
        img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
        if img is None:
            return None
        return float(cv2.Laplacian(img, cv2.CV_64F).var())
    except Exception:
        return None


# --------------------------------------------------------------------------
# Individual checks — each returns (ok: bool, detail: dict).
# --------------------------------------------------------------------------

def check_location(photo: AfterPhoto, centroid_lat: float, centroid_lon: float,
                   config: VerifyConfig) -> Tuple[bool, dict]:
    if photo.latitude is None or photo.longitude is None:
        return False, {"reason": "missing_gps", "flag": "location_missing"}
    dist = haversine_m(photo.latitude, photo.longitude,
                       centroid_lat, centroid_lon)
    detail: dict = {"distance_m": round(dist, 1), "radius_m": config.verify_radius_m}
    if dist > config.verify_radius_m:
        detail["reason"] = "too_far"
        return False, detail
    exif = read_exif(photo.path)
    if exif["gps"] is not None:
        gap = haversine_m(photo.latitude, photo.longitude,
                          exif["gps"][0], exif["gps"][1])
        detail["exif_gap_m"] = round(gap, 1)
        if gap > config.exif_gps_tolerance_m:
            detail["reason"] = "exif_mismatch"
            detail["flag"] = "exif_disagrees"
            return False, detail
    return True, detail


def _as_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """App-supplied timestamps are often tz-aware (ISO +00:00) while the
    server works in naive UTC. Normalize so subtraction never throws."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def check_time(photo: AfterPhoto, first_reported_at: Optional[datetime],
               now: datetime, config: VerifyConfig) -> Tuple[bool, dict]:
    taken = _as_naive_utc(photo.captured_at)
    if taken is None:
        exif = read_exif(photo.path)
        taken = _as_naive_utc(exif["taken_at"])
    now = _as_naive_utc(now) or datetime.utcnow()
    first_reported_at = _as_naive_utc(first_reported_at)
    detail: dict = {"taken_at": taken.isoformat() if taken else None}
    if taken is None:
        detail["reason"] = "no_capture_time"
        return False, detail
    age_min = (now - taken).total_seconds() / 60.0
    detail["age_min"] = round(age_min, 1)
    if age_min < -5 or age_min > config.verify_max_age_min:
        detail["reason"] = "stale_or_future"
        return False, detail
    if first_reported_at is not None and taken < first_reported_at:
        detail["reason"] = "before_first_report"
        return False, detail
    return True, detail


def check_reuse(photo_hash: Optional[int], reference_hashes: Sequence[int],
                config: VerifyConfig) -> Tuple[bool, dict]:
    """Near-identical to any before/earlier-after photo = re-upload."""
    if photo_hash is None:
        return True, {"compared": 0, "note": "unreadable, cannot compare"}
    best = None
    for ref in reference_hashes:
        d = hamming_distance(photo_hash, ref)
        best = d if best is None else min(best, d)
    detail = {"compared": len(reference_hashes),
              "best_hamming": best if best is not None else -1}
    if best is not None and best <= config.reuse_hamming_threshold:
        detail["reason"] = "near_duplicate"
        return False, detail
    return True, detail


# --------------------------------------------------------------------------
# Decision engine
# --------------------------------------------------------------------------

@dataclass
class VerifyOutcome:
    decision: str
    checks: List[dict]
    annotated_paths: List[str] = field(default_factory=list)
    needs_review_reasons: List[str] = field(default_factory=list)
    spot_checked: bool = False


def _hash_of(path: str) -> Optional[int]:
    return average_hash(path)


def decide_verification(
    req: VerifyRequest,
    detect_fn: Callable[[str], Tuple[list, Optional[str]]],
    config: Optional[VerifyConfig] = None,
    rng: Optional[random.Random] = None,
) -> VerifyOutcome:
    """Run all checks. detect_fn(path) -> (detections, annotated_path).

    Detections are [{class, confidence, ...}]. Production passes the YOLO
    wrapper with production per-class thresholds; tests pass a mock.
    """
    config = config or VerifyConfig()
    now = req.now or datetime.utcnow()
    rng = rng or random.Random()
    checks: List[dict] = []
    review_reasons: List[str] = []
    annotated: List[str] = []
    any_failed_litter = False
    any_uncertain = False
    sharp_found = False
    photos = list(req.photos)
    if not (config.min_photos <= len(photos) <= config.max_photos):
        return VerifyOutcome(
            decision=NEEDS_REVIEW, checks=[],
            needs_review_reasons=[
                f"expected {config.min_photos}..{config.max_photos} photos, got {len(photos)}"],
        )

    ref_hashes = []
    for p in list(req.before_photo_paths) + list(req.prior_after_photo_paths):
        h = _hash_of(p)
        if h is not None:
            ref_hashes.append(h)
    for i, photo in enumerate(photos):
        entry: dict = {"photo_index": i}
        loc_ok, loc_detail = check_location(
            photo, req.centroid_lat, req.centroid_lon, config)
        entry["location"] = {"ok": loc_ok, **loc_detail}
        if not loc_ok and loc_detail.get("reason") == "missing_gps":
            any_uncertain = True
            review_reasons.append(f"photo {i}: location missing")
        elif not loc_ok:
            entry["failed"] = True
            review_reasons.append(
                f"photo {i}: {loc_detail.get('reason', 'location check failed')}"
                + (f" ({loc_detail['distance_m']} m away)"
                   if loc_detail.get("distance_m") is not None else ""))

        time_ok, time_detail = check_time(
            photo, req.case_first_reported_at, now, config)
        entry["time"] = {"ok": time_ok, **time_detail}
        if not time_ok:
            any_uncertain = True
            review_reasons.append(
                f"photo {i}: capture time {time_detail.get('reason')}")

        h = _hash_of(photo.path)
        reuse_ok, reuse_detail = check_reuse(h, ref_hashes, config)
        entry["reuse"] = {"ok": reuse_ok, **reuse_detail}
        if not reuse_ok:
            checks.append({**entry, "rejected": "reuse"})
            return VerifyOutcome(decision=REJECTED_REUSE, checks=checks,
                                 needs_review_reasons=[
                                     f"photo {i} is a near-duplicate of a case photo"])

        sharp = blur_variance(photo.path)
        entry["sharpness"] = {"variance": sharp}
        if sharp is not None and sharp >= config.blur_variance_min:
            sharp_found = True
        if sharp is not None and sharp < config.blur_variance_min:
            any_uncertain = True
            review_reasons.append(f"photo {i}: blurry")

        try:
            detections, boxed = detect_fn(photo.path)
        except Exception as e:
            any_uncertain = True
            review_reasons.append(f"photo {i}: detector error")
            entry["detection"] = {"ok": False, "error": str(e)}
            checks.append(entry)
            continue
        if boxed:
            annotated.append(boxed)
        bars = req.case_class_bars or {}
        case_hits, weak_hits, other_lows = [], [], []
        for d in (detections or []):
            cls = str(d.get("class", ""))
            try:
                conf = float(d.get("confidence", 0))
            except (TypeError, ValueError):
                continue
            bar = bars.get(cls, 0.25)
            if cls in (req.case_classes or []) and conf >= bar:
                case_hits.append(d)
            elif conf >= config.low_confidence:
                (weak_hits if cls in (req.case_classes or []) else other_lows).append(d)
        entry["detection"] = {
            "case_class_hits": len(case_hits),
            "weak_hits": len(weak_hits),
            "other_hits": len(other_lows),
            "top": ({k: case_hits[0].get(k) for k in ("class", "confidence")}
                    if case_hits else None),
        }
        if case_hits:
            any_failed_litter = True
        else:
            lows = weak_hits + other_lows
            if lows:
                any_uncertain = True
                first = lows[0]
                review_reasons.append(
                    f"photo {i}: low-confidence detection "
                    f"({first.get('class')} {float(first.get('confidence', 0)):.2f})")
        checks.append(entry)
        if h is not None:
            ref_hashes.append(h)  # later photos compare against earlier ones

    if any_failed_litter:
        return VerifyOutcome(decision=FAILED_STILL_LITTER, checks=checks,
                             annotated_paths=annotated,
                             needs_review_reasons=review_reasons)
    hard_fail = any(c.get("failed") for c in checks)
    if hard_fail:
        return VerifyOutcome(decision=NEEDS_REVIEW, checks=checks,
                             annotated_paths=annotated,
                             needs_review_reasons=review_reasons or ["location check failed"])
    if any_uncertain or not sharp_found:
        if not sharp_found and "photo sharpness unverifiable" not in review_reasons:
            review_reasons.append("no sharp photo (all blurry or unreadable)")
        return VerifyOutcome(decision=NEEDS_REVIEW, checks=checks,
                             annotated_paths=annotated,
                             needs_review_reasons=review_reasons)
    # All checks green — but spot-check a fraction, and never claim proof.
    if rng.random() < config.spot_check_rate:
        review_reasons.append("random spot check")
        return VerifyOutcome(decision=NEEDS_REVIEW, checks=checks,
                             annotated_paths=annotated,
                             needs_review_reasons=review_reasons,
                             spot_checked=True)
    return VerifyOutcome(decision=PASSED, checks=checks,
                         annotated_paths=annotated,
                         needs_review_reasons=review_reasons)


def allowed_attempt(now_count_in_window: int, config: VerifyConfig) -> bool:
    """Rate limit: at most max_attempts_per_hour verification attempts
    per case. Pure helper; services count rows in the window."""
    return now_count_in_window < config.max_attempts_per_hour


HONEST_LIMIT = (
    "The detector cannot prove absence: a missed detection means a false "
    "PASSED is possible. Uncertain evidence routes to human review, and a "
    "configurable fraction of passes are spot-checked."
)
