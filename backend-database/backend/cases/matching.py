"""Pure duplicate-report matching for the cases feature.

No SQLAlchemy / no DB imports here by design: every function takes plain
dicts and dataclasses so the scoring can be unit-tested synthetically
(see test_matching.py) and reused by any storage backend.

Pipeline (implemented in service.py, scored here):
  1. Candidate cases are pre-filtered by the DB: status in (open, reopened),
     ST_DWithin(centroid, report, MATCH_RADIUS_M), last_reported_at within
     MATCH_WINDOW_DAYS.
  2. Each candidate is scored 0..1 from distance, time gap, class overlap
     (Jaccard) and image similarity (perceptual-hash Hamming distance).
  3. decide() maps the score to auto_merge / suggest / new_case.
  4. Cleaned cases are NEVER auto-merge targets; proximity to a recently
     cleaned case instead records a recurrence link (handled in service.py).
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

@dataclass
class MatchConfig:
    """Tunable knobs. Defaults per feature spec; override via constructor."""

    match_radius_m: float = 40.0
    match_window_days: float = 14.0
    auto_merge_score: float = 0.70
    suggest_score: float = 0.40
    # Score weights (must sum to 1.0).
    w_distance: float = 0.40
    w_time: float = 0.25
    w_class: float = 0.20
    w_image: float = 0.15

    def __post_init__(self) -> None:
        total = self.w_distance + self.w_time + self.w_class + self.w_image
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(f"match weights must sum to 1.0, got {total}")


def config_from_env(prefix: str = "CASE_") -> MatchConfig:
    """Build a MatchConfig from CASE_* env vars (falls back to defaults)."""
    def _f(name: str, default: float) -> float:
        try:
            return float(os.getenv(prefix + name, str(default)))
        except (TypeError, ValueError):
            return default

    return MatchConfig(
        match_radius_m=_f("MATCH_RADIUS_M", 40.0),
        match_window_days=_f("MATCH_WINDOW_DAYS", 14.0),
        auto_merge_score=_f("AUTO_MERGE_SCORE", 0.70),
        suggest_score=_f("SUGGEST_SCORE", 0.40),
    )


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------

@dataclass
class ReportInput:
    """A new report to match. Plain data, no ORM."""

    latitude: float
    longitude: float
    # Hours since now (0 = just taken). Service converts created_at deltas.
    age_hours: float = 0.0
    # Detected class names, e.g. {"Plastic Waste", "Glass Waste"}.
    classes: Sequence[str] = field(default_factory=list)
    # Absolute path of the uploaded photo (None skips image similarity).
    image_path: Optional[str] = None
    # GPS accuracy in metres, if the app stored it (None = unknown).
    gps_accuracy_m: Optional[float] = None
    reporter_id: Optional[str] = None


@dataclass
class CaseSummary:
    """A merge candidate. Plain data, no ORM."""

    case_id: int
    centroid_lat: float
    centroid_lon: float
    # Hours since the case's last report.
    last_report_age_hours: float = 0.0
    # Union of detected class names across member reports.
    classes: Sequence[str] = field(default_factory=list)
    # Absolute paths of member photos used for pHash comparison.
    # Only a few are needed; service passes up to _MAX_CASE_PHOTOS.
    photo_paths: Sequence[str] = field(default_factory=list)
    status: str = "open"
    report_count: int = 1


# --------------------------------------------------------------------------
# Geo / time helpers
# --------------------------------------------------------------------------

EARTH_RADIUS_M = 6_371_000.0


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in metres."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(math.sqrt(a))


def effective_radius_m(config: MatchConfig, gps_accuracy_m: Optional[float]) -> float:
    """Widen the match radius by GPS accuracy, capped at 2x.

    A phone reporting +/-25 m accuracy should still match the same pile.
    """
    if gps_accuracy_m is None or gps_accuracy_m <= 0:
        return config.match_radius_m
    return min(config.match_radius_m + gps_accuracy_m, 2.0 * config.match_radius_m)


def distance_score(distance_m: float, radius_m: float) -> float:
    """1.0 at zero distance, linear decay to 0.0 at the radius."""
    if distance_m <= 0:
        return 1.0
    if distance_m >= radius_m:
        return 0.0
    return 1.0 - distance_m / radius_m


def time_score(age_hours: float, window_days: float) -> float:
    """1.0 for fresh reports, linear decay to 0.0 at the window edge."""
    window_hours = max(window_days * 24.0, 1e-6)
    if age_hours <= 0:
        return 1.0
    if age_hours >= window_hours:
        return 0.0
    return 1.0 - age_hours / window_hours


def class_jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    """Jaccard overlap of detected class sets.

    Empty-vs-empty (e.g. both "No Waste Detected") scores 0.5: weak
    evidence, neither for nor against. Empty-vs-nonempty scores 0.0.
    """
    sa, sb = set(a or []), set(b or [])
    if not sa and not sb:
        return 0.5
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


# --------------------------------------------------------------------------
# Image similarity (perceptual hash, PIL only)
# --------------------------------------------------------------------------

def average_hash(image_path: str, hash_size: int = 8) -> Optional[int]:
    """64-bit average hash of an image. None if unreadable."""
    try:
        from PIL import Image

        with Image.open(image_path) as img:
            img = img.convert("L").resize((hash_size, hash_size), Image.BILINEAR)
            w, h = img.size
            pixels = [img.getpixel((x, y)) for y in range(h) for x in range(w)]
        avg = sum(pixels) / len(pixels)
        bits = 0
        for px in pixels:
            bits = (bits << 1) | (1 if px >= avg else 0)
        return bits
    except Exception:
        return None


def hamming_distance(h1: int, h2: int) -> int:
    """Bit differences between two hashes."""
    return bin(h1 ^ h2).count("1")


def image_similarity(new_path: Optional[str], case_photos: Sequence[str],
                     max_photos: int = 3) -> Optional[float]:
    """Best similarity of the new photo vs a case's photos, 0..1.

    Returns None when there is nothing to compare (missing files), so the
    caller can fall back to a neutral score instead of punishing the match.
    """
    if not new_path or not os.path.exists(new_path):
        return None
    new_hash = average_hash(new_path)
    if new_hash is None:
        return None
    best: Optional[float] = None
    for path in list(case_photos or [])[:max_photos]:
        if not path or not os.path.exists(path):
            continue
        other = average_hash(path)
        if other is None:
            continue
        sim = 1.0 - hamming_distance(new_hash, other) / 64.0
        best = sim if best is None else max(best, sim)
    return best


# --------------------------------------------------------------------------
# Scoring + decision
# --------------------------------------------------------------------------

@dataclass
class CandidateScore:
    case_id: int
    score: float
    distance_m: float
    evidence: Dict[str, float]


def score_candidate(report: ReportInput, case: CaseSummary,
                    config: Optional[MatchConfig] = None) -> CandidateScore:
    """Score one (report, candidate case) pair. Higher = more likely duplicate."""
    config = config or MatchConfig()
    radius = effective_radius_m(config, report.gps_accuracy_m)
    dist = haversine_m(report.latitude, report.longitude,
                       case.centroid_lat, case.centroid_lon)
    d = distance_score(dist, radius)
    # Time gap between the new report and the case's latest activity.
    gap_hours = max(report.age_hours, case.last_report_age_hours)
    t = time_score(gap_hours, config.match_window_days)
    c = class_jaccard(report.classes, case.classes)
    img_sim = image_similarity(report.image_path, case.photo_paths)
    img = img_sim if img_sim is not None else 0.5
    score = (config.w_distance * d + config.w_time * t
             + config.w_class * c + config.w_image * img)
    evidence = {
        "distance_m": round(dist, 2),
        "radius_m": round(radius, 2),
        "distance_score": round(d, 4),
        "gap_hours": round(gap_hours, 2),
        "time_score": round(t, 4),
        "class_jaccard": round(c, 4),
        "image_similarity": round(img, 4) if img_sim is not None else -1.0,
        "w_distance": config.w_distance,
        "w_time": config.w_time,
        "w_class": config.w_class,
        "w_image": config.w_image,
    }
    return CandidateScore(case_id=case.case_id, score=round(score, 4),
                          distance_m=round(dist, 2), evidence=evidence)


def rank_candidates(report: ReportInput, cases: Sequence[CaseSummary],
                    config: Optional[MatchConfig] = None) -> List[CandidateScore]:
    """Score all candidates, best first."""
    config = config or MatchConfig()
    ranked = [score_candidate(report, case, config) for case in cases]
    ranked.sort(key=lambda s: s.score, reverse=True)
    return ranked


def decide(score: float, config: Optional[MatchConfig] = None) -> str:
    """Map a score to auto_merge / suggest / new_case."""
    config = config or MatchConfig()
    if score >= config.auto_merge_score:
        return "auto_merge"
    if score >= config.suggest_score:
        return "suggest"
    return "new_case"


def match_report(report: ReportInput, cases: Sequence[CaseSummary],
                 config: Optional[MatchConfig] = None) -> Tuple[str, Optional[CandidateScore]]:
    """Full decision for one report: (decision, best_candidate_or_None)."""
    config = config or MatchConfig()
    ranked = rank_candidates(report, cases, config)
    if not ranked:
        return "new_case", None
    best = ranked[0]
    return decide(best.score, config), best


# --------------------------------------------------------------------------
# Candidate gating (used by service.py when querying, unit-tested here)
# --------------------------------------------------------------------------

def is_candidate_fresh(last_report_age_hours: float,
                       config: Optional[MatchConfig] = None) -> bool:
    """A case is only a merge candidate if its latest report is inside the
    match window. A case gone quiet for 30 days never merges, no matter how
    close or similar — the report starts a new case instead."""
    config = config or MatchConfig()
    return last_report_age_hours < config.match_window_days * 24.0


def find_recurrence_case(report: ReportInput, cleaned_cases: Sequence[CaseSummary],
                         config: Optional[MatchConfig] = None) -> Optional[int]:
    """Nearest *cleaned* case within (GPS-widened) radius, if any.

    Cleaned cases are never auto-merge targets. When a new report lands near
    one, the service creates a NEW case and stores recurrence_of pointing at
    the old case id (used later by hotspot analytics to spot re-dumping).
    Returns the old case id or None.
    """
    config = config or MatchConfig()
    radius = effective_radius_m(config, report.gps_accuracy_m)
    best_id: Optional[int] = None
    best_dist = radius
    for case in cleaned_cases:
        dist = haversine_m(report.latitude, report.longitude,
                           case.centroid_lat, case.centroid_lon)
        if dist <= best_dist:
            best_dist = dist
            best_id = case.case_id
    return best_id
