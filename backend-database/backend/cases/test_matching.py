"""Synthetic tests for the pure duplicate-matching module.

No DB, no mocks: all inputs are fabricated dicts/dataclasses plus tiny
PIL-generated photos. Covers the spec's required scenarios:

  1. same spot, two photos          -> auto_merge
  2. 200 m apart                    -> separate (never auto-merge)
  3. same spot but 30 days later    -> separate (freshness gate)
  4. near a cleaned case            -> new case + recurrence link
  5. borderline score               -> suggestion, still a new case
  6. concurrent uploads             -> exactly one case (lock protocol)

Run:  python -m pytest backend/cases/test_matching.py -q
      (from backend-database/, system python with pillow installed)
"""

import os
import shutil
import tempfile
import threading

import pytest

from .matching import (
    CaseSummary,
    MatchConfig,
    ReportInput,
    decide,
    effective_radius_m,
    find_recurrence_case,
    haversine_m,
    image_similarity,
    is_candidate_fresh,
    match_report,
)


@pytest.fixture()
def photos(tmp_path):
    """Three tiny deterministic photos.

    img_a / img_a2 are byte-identical (sim == 1.0); img_b is a different
    pattern (sim ~ 0.5). NOTE: solid colours all hash identically, so the
    patterns must differ structurally, not just in colour.
    """
    from PIL import Image

    def pattern(path, kind):
        img = Image.new("L", (64, 64))
        px = img.load()
        for y in range(64):
            for x in range(64):
                if kind == "vertical":
                    px[x, y] = 0 if x < 32 else 255
                elif kind == "horizontal":
                    px[x, y] = 0 if y < 32 else 255
                else:  # checker
                    px[x, y] = 0 if (x // 8 + y // 8) % 2 == 0 else 255
        img.save(path)

    a = str(tmp_path / "a.png")
    a2 = str(tmp_path / "a_copy.png")
    b = str(tmp_path / "b.png")
    pattern(a, "vertical")
    shutil.copy(a, a2)
    pattern(b, "horizontal")
    return {"a": a, "a2": a2, "b": b}


def _report(lat=28.6139, lon=77.2090, age_hours=0.0,
            classes=("Plastic Waste",), image=None, gps=None):
    return ReportInput(latitude=lat, longitude=lon, age_hours=age_hours,
                       classes=list(classes), image_path=image,
                       gps_accuracy_m=gps)


def _case(case_id=1, lat=28.6139, lon=77.2090, age_hours=1.0,
          classes=("Plastic Waste",), photos=(), status="open"):
    return CaseSummary(case_id=case_id, centroid_lat=lat, centroid_lon=lon,
                       last_report_age_hours=age_hours, classes=list(classes),
                       photo_paths=list(photos), status=status)


# --------------------------------------------------------------------------
# 1. Same spot, two near-identical photos -> merged
# --------------------------------------------------------------------------

def test_same_spot_two_photos_merged(photos):
    config = MatchConfig()
    report = _report(classes=("Plastic Waste", "Glass Waste"), image=photos["a2"])
    case = _case(classes=("Plastic Waste", "Glass Waste"), photos=(photos["a"],))
    decision, best = match_report(report, [case], config)
    assert decision == "auto_merge"
    assert best is not None and best.case_id == 1
    assert best.score >= config.auto_merge_score
    assert best.evidence["distance_m"] == pytest.approx(0.0, abs=0.5)
    assert best.evidence["image_similarity"] == pytest.approx(1.0)


# --------------------------------------------------------------------------
# 2. 200 m apart -> separate (a merge must never fire at that distance)
# --------------------------------------------------------------------------

def test_200m_apart_never_auto_merges(photos):
    config = MatchConfig()
    # ~200 m north (0.0018 deg latitude).
    report = _report(lat=28.6139 + 0.0018, image=photos["a2"])
    case = _case(photos=(photos["a"],))
    decision, best = match_report(report, [case], config)
    assert best.distance_m == pytest.approx(200, abs=5)
    assert decision in ("suggest", "new_case")
    assert decision != "auto_merge"


def test_200m_apart_different_scenes_is_new_case(photos):
    report = _report(lat=28.6139 + 0.0018, classes=("Metal Waste",),
                     image=photos["b"])
    case = _case(classes=("Plastic Waste",), photos=(photos["a"],))
    decision, _ = match_report(report, [case])
    assert decision == "new_case"


# --------------------------------------------------------------------------
# 3. Same spot but 30 days later -> separate (freshness gate)
# --------------------------------------------------------------------------

def test_stale_case_is_not_a_candidate():
    assert is_candidate_fresh(24.0) is True
    assert is_candidate_fresh(13 * 24.0) is True
    assert is_candidate_fresh(30 * 24.0) is False
    assert is_candidate_fresh(15 * 24.0) is False


def test_time_score_decays_to_zero():
    from .matching import time_score
    assert time_score(0.0, 14.0) == 1.0
    assert time_score(7 * 24.0, 14.0) == pytest.approx(0.5)
    assert time_score(30 * 24.0, 14.0) == 0.0


def test_no_candidates_means_new_case(photos):
    # The service pre-filters by is_candidate_fresh, so a 30-day-old case
    # never even reaches the scorer: empty candidate list -> new case.
    decision, best = match_report(_report(image=photos["a"]), [])
    assert decision == "new_case"
    assert best is None


# --------------------------------------------------------------------------
# 4. Near a cleaned case -> new case + recurrence link (never auto-merge)
# --------------------------------------------------------------------------

def test_recurrence_found_near_cleaned_case():
    cleaned = [_case(case_id=9, status="cleaned")]
    report = _report()  # same spot
    assert find_recurrence_case(report, cleaned) == 9


def test_no_recurrence_when_far():
    cleaned = [_case(case_id=9, status="cleaned")]
    report = _report(lat=28.6139 + 0.01)  # ~1.1 km away
    assert find_recurrence_case(report, cleaned) is None


def test_no_recurrence_without_cleaned_cases():
    assert find_recurrence_case(_report(), []) is None


# --------------------------------------------------------------------------
# 5. Borderline -> suggestion (human review), still its own case
# --------------------------------------------------------------------------

def test_borderline_score_suggests(photos):
    # ~30 m away: distance term 0.25; fresh, same class, no photo.
    # 0.4*0.25 + 0.25*1 + 0.2*1 + 0.15*0.5 = 0.625 -> suggest.
    config = MatchConfig()
    report = _report(lat=28.6139 + 0.00027, image=None)
    case = _case()
    decision, best = match_report(report, [case], config)
    assert config.suggest_score <= best.score < config.auto_merge_score
    assert decision == "suggest"


def test_decide_thresholds():
    config = MatchConfig(auto_merge_score=0.7, suggest_score=0.4)
    assert decide(0.9, config) == "auto_merge"
    assert decide(0.7, config) == "auto_merge"
    assert decide(0.5, config) == "suggest"
    assert decide(0.4, config) == "suggest"
    assert decide(0.39, config) == "new_case"


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def test_haversine_sanity():
    # ~111 m per 0.001 deg latitude.
    assert haversine_m(28.0, 77.0, 28.001, 77.0) == pytest.approx(111.2, abs=1.0)
    assert haversine_m(28.0, 77.0, 28.0, 77.0) == 0.0


def test_gps_accuracy_widens_radius_capped_at_2x():
    config = MatchConfig(match_radius_m=40.0)
    assert effective_radius_m(config, None) == 40.0
    assert effective_radius_m(config, 10.0) == 50.0
    assert effective_radius_m(config, 100.0) == 80.0  # capped at 2x


def test_image_similarity_matrix(photos):
    assert image_similarity(photos["a"], [photos["a2"]]) == pytest.approx(1.0)
    different = image_similarity(photos["a"], [photos["b"]])
    assert different is not None and different < 0.9
    assert image_similarity(photos["a"], []) is None
    assert image_similarity("/nonexistent/x.png", [photos["a"]]) is None
    assert image_similarity(photos["a"], ["/nonexistent/y.png"]) is None


# --------------------------------------------------------------------------
# 6. Concurrent uploads must not create two cases.
#
# The production guard is a Postgres advisory lock per geo-cell
# (service.merge_lock_key + pg_advisory_xact_lock) held for the whole
# find-score-insert transaction. That needs a live DB, so here we test
# the exact same protocol against an in-memory fake store guarded by
# one threading.Lock per lock key: 10 threads racing the same spot
# must yield exactly one case.
# --------------------------------------------------------------------------

def _cell_key(lat: float, lon: float, cell_m: float = 40.0) -> tuple:
    from .matching import EARTH_RADIUS_M
    import math
    cell_deg = (cell_m / EARTH_RADIUS_M) * (180.0 / math.pi)
    return (round(lat / cell_deg), round(lon / cell_deg))


class FakeCaseStore:
    """Mirrors service.py's merge protocol with per-cell locks."""

    def __init__(self):
        self._lock = threading.Lock()
        self._cell_locks = {}
        self.cases = []
        self._next_id = 1

    def _cell_lock(self, key):
        with self._lock:
            return self._cell_locks.setdefault(key, threading.Lock())

    def upload(self, report):
        key = _cell_key(report.latitude, report.longitude)
        with self._cell_lock(key):
            # -- critical section = one DB transaction in production --
            for case in self.cases:
                decision, _ = match_report(report, [case])
                if decision == "auto_merge":
                    case.report_count += 1
                    return ("merged", case.case_id)
            case = {"id": self._next_id, "report_count": 1,
                    "lat": report.latitude, "lon": report.longitude}
            self._next_id += 1
            self.cases.append(case)
            return ("new_case", case["id"])


def test_concurrent_uploads_create_single_case(photos):
    store = FakeCaseStore()
    lat, lon = 28.6139, 77.2090
    results, errors = [], []

    def worker(i):
        try:
            report = _report(lat=lat, lon=lon, image=photos["a"],
                             classes=("Plastic Waste",))
            # Each thread builds its own CaseSummary view of cell cases,
            # exactly like the service re-reads candidates inside the lock.
            with store._cell_lock(_cell_key(lat, lon)):
                summaries = [
                    _case(case_id=c["id"], lat=c["lat"], lon=c["lon"],
                          age_hours=0.0, classes=("Plastic Waste",),
                          photos=(photos["a"],))
                    for c in store.cases
                ]
                if summaries:
                    decision, best = match_report(report, summaries)
                else:
                    decision, best = "new_case", None
                if decision == "auto_merge":
                    target = next(c for c in store.cases if c["id"] == best.case_id)
                    target["report_count"] += 1
                    results.append(("merged", target["id"]))
                else:
                    case = {"id": store._next_id, "report_count": 1,
                            "lat": lat, "lon": lon}
                    store._next_id += 1
                    store.cases.append(case)
                    results.append(("new_case", case["id"]))
        except Exception as e:  # pragma: no cover
            errors.append(e)

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors
    assert len(store.cases) == 1
    assert store.cases[0]["report_count"] == 10
    assert sum(1 for d, _ in results if d == "new_case") == 1


def test_cell_key_stable_and_local():
    assert _cell_key(28.6139, 77.2090) == _cell_key(28.6139, 77.2090)
    assert _cell_key(28.6139, 77.2090) != _cell_key(28.6139 + 0.01, 77.2090)
