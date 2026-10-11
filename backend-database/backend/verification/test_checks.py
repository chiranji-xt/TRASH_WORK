"""Synthetic tests for cleanup verification (mocked detector, no DB).

Covers the spec: far-away flagged, reuse rejected, litter -> FAILED,
clean -> PASSED, low-confidence -> NEEDS_REVIEW, rate limiting.
(The cleaner-cannot-PATCH rule is app-level; covered live on demo.)

Run:  python -m pytest backend/verification/test_checks.py -q
"""

import random
from datetime import datetime, timedelta

import pytest

from .checks import (
    AfterPhoto,
    VerifyConfig,
    VerifyRequest,
    allowed_attempt,
    check_location,
    check_reuse,
    check_time,
    decide_verification,
)


def _photo(path, kind):
    from PIL import Image
    img = Image.new("L", (128, 128))
    px = img.load()
    for y in range(128):
        for x in range(128):
            if kind == "vertical":
                px[x, y] = 0 if x < 64 else 255
            elif kind == "horizontal":
                px[x, y] = 0 if y < 64 else 255
            elif kind == "checker":
                px[x, y] = 0 if (x // 16 + y // 16) % 2 == 0 else 255
            else:  # flat mid-grey (blurry by construction)
                px[x, y] = 128
    img.save(path)


@pytest.fixture()
def pics(tmp_path):
    paths = {}
    for name, kind in [("before1", "vertical"), ("before2", "horizontal"),
                       ("clean", "checker"), ("flat", "flat")]:
        p = str(tmp_path / f"{name}.png")
        _photo(p, kind)
        paths[name] = p
    import shutil
    paths["reuse"] = str(tmp_path / "reuse.png")
    shutil.copy(paths["before1"], paths["reuse"])
    return paths


NOW = datetime(2026, 10, 10, 12, 0, 0)
LAT, LON = 28.6139, 77.2090


def _req(pics, photos, **kw):
    base = dict(case_id=1, centroid_lat=LAT, centroid_lon=LON,
                case_classes=["Plastic Waste"],
                case_first_reported_at=NOW - timedelta(days=1),
                before_photo_paths=[pics["before1"], pics["before2"]],
                prior_after_photo_paths=[], photos=photos,
                cleaner_id="cleaner-7", now=NOW)
    base.update(kw)
    return VerifyRequest(**base)


def _after(path, lat=LAT, lon=LON, at=None):
    return AfterPhoto(path=path, latitude=lat, longitude=lon,
                      captured_at=at if at is not None else NOW)


def _clean_detect(_path):
    return [], None


def _no_review_config(**kw):
    kw.setdefault("spot_check_rate", 0.0)
    return VerifyConfig(**kw)


# --------------------------------------------------------------------------
# 1. Clean photo at the right place -> PASSED
# --------------------------------------------------------------------------

def test_clean_photo_passes(pics):
    out = decide_verification(
        _req(pics, [_after(pics["clean"])]),
        _clean_detect, _no_review_config())
    assert out.decision == "passed", out.needs_review_reasons
    assert out.checks[0]["location"]["ok"] is True
    assert out.checks[0]["reuse"]["ok"] is True


def test_three_photos_ok(pics):
    out = decide_verification(
        _req(pics, [_after(pics["clean"])] * 1),
        _clean_detect, _no_review_config(max_photos=3))
    assert out.decision == "passed"


# --------------------------------------------------------------------------
# 2. Far-away photo -> flagged (location), never auto-close
# --------------------------------------------------------------------------

def test_far_away_photo_flagged(pics):
    out = decide_verification(
        _req(pics, [_after(pics["clean"], lat=LAT + 0.01)]),  # ~1.1 km
        _clean_detect, _no_review_config())
    assert out.decision == "needs_review"
    assert out.checks[0]["location"]["ok"] is False
    assert out.checks[0]["location"]["reason"] == "too_far"


def test_missing_gps_needs_review(pics):
    out = decide_verification(
        _req(pics, [AfterPhoto(path=pics["clean"], captured_at=NOW)]),
        _clean_detect, _no_review_config())
    assert out.decision == "needs_review"
    assert any("location missing" in r for r in out.needs_review_reasons)


# --------------------------------------------------------------------------
# 3. Reused photo -> rejected
# --------------------------------------------------------------------------

def test_reused_before_photo_rejected(pics):
    out = decide_verification(
        _req(pics, [_after(pics["reuse"])]),
        _clean_detect, _no_review_config())
    assert out.decision == "rejected_reuse"


def test_check_reuse_unit(pics):
    from .checks import average_hash
    h1 = average_hash(pics["before1"])
    assert h1 is not None
    ok, detail = check_reuse(h1, [average_hash(pics["before1"])],
                             VerifyConfig())
    assert ok is False and detail["reason"] == "near_duplicate"


# --------------------------------------------------------------------------
# 4. Litter still detected -> FAILED_STILL_LITTER, annotated returned
# --------------------------------------------------------------------------

def test_litter_detected_fails(pics):
    def litter(_path):
        return [{"class": "Plastic Waste", "confidence": 0.9,
                 "bbox": [1, 2, 3, 4]}], "/tmp/boxed.jpg"

    out = decide_verification(
        _req(pics, [_after(pics["clean"])]), litter, _no_review_config())
    assert out.decision == "failed_still_litter"
    assert out.annotated_paths == ["/tmp/boxed.jpg"]
    assert out.checks[0]["detection"]["case_class_hits"] == 1


# --------------------------------------------------------------------------
# 5. Low-confidence detection -> NEEDS_REVIEW (uncertain, never closes)
# --------------------------------------------------------------------------

def test_low_confidence_needs_review(pics):
    def vague(_path):
        return [{"class": "Unknown", "confidence": 0.2,
                 "bbox": [1, 2, 3, 4]}], None

    out = decide_verification(
        _req(pics, [_after(pics["clean"])]), vague, _no_review_config())
    assert out.decision == "needs_review"
    assert any("low-confidence" in r for r in out.needs_review_reasons)


def test_weak_case_class_hit_is_uncertain_not_failed(pics):
    # Plastic at 0.20: above LOW (0.15) but below its production bar
    # (0.45) -> possible weak litter, must not auto-fail nor auto-pass.
    def weak(_path):
        return [{"class": "Plastic Waste", "confidence": 0.2,
                 "bbox": [1, 2, 3, 4]}], None

    req = _req(pics, [_after(pics["clean"])])
    req.case_class_bars = {"Plastic Waste": 0.45}
    out = decide_verification(req, weak, _no_review_config())
    assert out.decision == "needs_review"
    assert out.checks[0]["detection"]["case_class_hits"] == 0
    assert out.checks[0]["detection"]["weak_hits"] == 1


# --------------------------------------------------------------------------
# 6. Blurry photo -> NEEDS_REVIEW (no sharp evidence)
# --------------------------------------------------------------------------

def test_blurry_photo_needs_review(pics):
    out = decide_verification(
        _req(pics, [_after(pics["flat"])]),
        _clean_detect, _no_review_config())
    assert out.decision == "needs_review"


# --------------------------------------------------------------------------
# 7. Time checks
# --------------------------------------------------------------------------

def test_stale_capture_time_flagged(pics):
    old = NOW - timedelta(hours=5)
    out = decide_verification(
        _req(pics, [_after(pics["clean"], at=old)]),
        _clean_detect, _no_review_config())
    assert out.decision == "needs_review"
    assert out.checks[0]["time"]["reason"] == "stale_or_future"


def test_capture_before_first_report_flagged(pics):
    # Wide age window so only the ordering rule can fire.
    cfg = VerifyConfig(verify_max_age_min=60 * 24 * 60)
    req = _req(pics, [_after(pics["clean"], at=NOW - timedelta(days=2))])
    ok, detail = check_time(req.photos[0], req.case_first_reported_at,
                            NOW, cfg)
    assert ok is False and detail["reason"] == "before_first_report"


# --------------------------------------------------------------------------
# 8. Spot checks + rate limiting + photo count guard
# --------------------------------------------------------------------------

def test_spot_check_routes_to_review(pics):
    out = decide_verification(
        _req(pics, [_after(pics["clean"])]),
        _clean_detect,
        VerifyConfig(spot_check_rate=1.0),
        rng=random.Random(0))
    assert out.decision == "needs_review"
    assert out.spot_checked is True


def test_rate_limit_helper():
    cfg = VerifyConfig(max_attempts_per_hour=5)
    assert allowed_attempt(0, cfg) is True
    assert allowed_attempt(4, cfg) is True
    assert allowed_attempt(5, cfg) is False


def test_wrong_photo_count_needs_review(pics):
    out = decide_verification(
        _req(pics, []), _clean_detect, _no_review_config())
    assert out.decision == "needs_review"
    out2 = decide_verification(
        _req(pics, [_after(pics["clean"])] * 4),
        _clean_detect, _no_review_config(max_photos=3))
    assert out2.decision == "needs_review"


def test_tz_aware_capture_times_do_not_crash(pics):
    # Regression: app-sent ISO timestamps carry +00:00 while the server
    # works in naive UTC — comparison must normalize, never throw.
    from datetime import timezone
    aware_now = datetime(2026, 10, 10, 12, 0, 0, tzinfo=timezone.utc)
    photo = AfterPhoto(path=pics["clean"], latitude=LAT, longitude=LON,
                       captured_at=aware_now)
    ok, detail = check_time(photo, NOW - timedelta(days=1),
                            datetime(2026, 10, 10, 12, 5, 0),
                            VerifyConfig())
    assert ok is True
    out = decide_verification(
        _req(pics, [photo]), _clean_detect, _no_review_config())
    assert out.decision == "passed"
