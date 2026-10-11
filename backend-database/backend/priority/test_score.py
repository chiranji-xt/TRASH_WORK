"""Synthetic tests for the priority score (no DB needed).

Covers the spec: monotonicity, caps, weights-sum startup failure,
zero-detection validity, breakdown summation, golden value.

Run:  python -m pytest backend/priority/test_score.py -q
"""

import math

import pytest

from .score import (
    CaseFacts,
    PriorityConfig,
    norm_age,
    norm_area,
    norm_class,
    norm_items,
    norm_reporters,
    priority_band,
    score_case,
)


def _facts(**kw):
    base = dict(item_count=5, covered_area_frac=0.3,
                classes=["Plastic Waste"], distinct_reporters=2,
                days_open=7.0)
    base.update(kw)
    return CaseFacts(**base)


# --------------------------------------------------------------------------
# Monotonicity: more items / reporters / age never lowers the score.
# --------------------------------------------------------------------------

@pytest.mark.parametrize("field,values", [
    ("item_count", [0, 1, 5, 20, 100]),
    ("distinct_reporters", [0, 1, 5, 50, 500]),
    ("days_open", [0.0, 1.0, 7.0, 30.0, 365.0]),
    ("covered_area_frac", [0.0, 0.2, 0.6, 1.0, 5.0]),
])
def test_monotone_in_each_input(field, values):
    scores = [score_case(_facts(**{field: v}))["score"] for v in values]
    assert scores == sorted(scores), f"{field}: {scores}"


def test_more_classes_never_lowers():
    base = score_case(_facts(classes=["Plastic Waste"]))["score"]
    assert score_case(_facts(classes=["Plastic Waste", "Glass Waste"]))["score"] >= base


# --------------------------------------------------------------------------
# Caps work.
# --------------------------------------------------------------------------

def test_caps():
    cfg = PriorityConfig()  # item_cap=20, reporter_cap=50, age_cap=30
    assert norm_items(20, cfg) == 1.0
    assert norm_items(10_000, cfg) == 1.0
    assert norm_items(-3, cfg) == 0.0
    assert norm_reporters(50, cfg) == pytest.approx(1.0)
    assert norm_reporters(10_000, cfg) == 1.0
    assert norm_age(30.0, cfg) == 1.0
    assert norm_age(365.0, cfg) == 1.0
    assert norm_area(2.5) == 1.0
    assert norm_area(-0.1) == 0.0
    # Class mix capped: Glass (1.0) + bonus cannot exceed 1.0.
    assert norm_class(["Glass Waste", "Metal Waste", "Plastic Waste"], cfg) == 1.0


def test_class_weights_and_bonus():
    cfg = PriorityConfig()
    assert norm_class(["Glass Waste"], cfg) == 1.0
    assert norm_class(["Cardboard_Paper"], cfg) == pytest.approx(0.4)
    assert norm_class(["Plastic Waste", "Cardboard_Paper"], cfg) == pytest.approx(0.65)
    assert norm_class([], cfg) == 0.0
    assert norm_class(["Unknown Stuff"], cfg) == pytest.approx(0.4)


# --------------------------------------------------------------------------
# Weights must sum to 1 or startup fails loudly.
# --------------------------------------------------------------------------

def test_bad_weights_raise():
    with pytest.raises(ValueError, match="must sum to 1.0"):
        PriorityConfig(w_items=0.5, w_area=0.5, w_class=0.5,
                       w_reporters=0.5, w_age=0.5)


def test_default_weights_valid():
    PriorityConfig()  # must not raise


# --------------------------------------------------------------------------
# Zero-detection case: low but valid.
# --------------------------------------------------------------------------

def test_zero_detection_case():
    out = score_case(CaseFacts())
    assert out["version"]
    assert 0.0 <= out["score"] <= 100.0
    assert out["score"] < 25.0  # low band, not alarming
    assert out["components"]["items"]["normalized"] == 0.0
    assert out["components"]["class"]["normalized"] == 0.0


def test_old_untouched_zero_detection_still_ranks_by_age():
    fresh = score_case(CaseFacts(days_open=0.0))["score"]
    stale = score_case(CaseFacts(days_open=30.0))["score"]
    assert stale > fresh


# --------------------------------------------------------------------------
# Breakdown contributions sum to the score.
# --------------------------------------------------------------------------

def test_breakdown_sums_to_score():
    out = score_case(_facts(item_count=12, covered_area_frac=0.55,
                            classes=["Glass Waste", "Metal Waste"],
                            distinct_reporters=9, days_open=21.0))
    total = sum(c["contribution"] for c in out["components"].values())
    assert total * 100 == pytest.approx(out["score"], abs=0.15)
    for name, comp in out["components"].items():
        assert set(comp) == {"raw", "normalized", "weight", "contribution"}, name
        assert 0.0 <= comp["normalized"] <= 1.0, name


# --------------------------------------------------------------------------
# Golden value with fixed inputs (guards against silent formula drift).
# Hand-computed: items 10->0.5; area 0.4; class Glass+Plastic->1.0;
# reporters 4->log10(5)/log10(51)=0.4093; age 15->0.5.
# 100*(0.25*0.5+0.2*0.4+0.2*1.0+0.15*0.4093+0.2*0.5) = 56.6395 -> 56.6.
# --------------------------------------------------------------------------

def test_golden_value():
    out = score_case(CaseFacts(item_count=10, covered_area_frac=0.4,
                               classes=["Glass Waste", "Plastic Waste"],
                               distinct_reporters=4, days_open=15.0))
    assert out["score"] == pytest.approx(56.6, abs=0.1)
    assert out["version"] == "1.0"
    assert out["components"]["reporters"]["normalized"] == pytest.approx(
        math.log10(5) / math.log10(51), abs=1e-4)


# --------------------------------------------------------------------------
# Bands + sensitivity hook.
# --------------------------------------------------------------------------

def test_bands():
    assert priority_band(90) == "critical"
    assert priority_band(75) == "critical"
    assert priority_band(60) == "high"
    assert priority_band(30) == "watch"
    assert priority_band(10) == "low"


def test_location_sensitivity_defaults_to_neutral():
    plain = score_case(_facts())["score"]
    assert score_case(_facts(location_sensitivity=1.0))["score"] == plain
    boosted = score_case(_facts(location_sensitivity=1.2))["score"]
    assert boosted == pytest.approx(plain * 1.2, abs=0.15)
