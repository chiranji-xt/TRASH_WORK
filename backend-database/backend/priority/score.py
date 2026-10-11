"""Transparent priority score for cases. A formula, NOT a trained model.

Ranks open cases for cleaners with an explainable 0-100 score. Every input
is aggregated to avoid double-counting the same items photographed by
several citizens: item count and covered area come from the single report
with the highest detected item count, never the sum.

LIMITS (read before using the score to promise anything):
- item count and covered area come from the detector and can be wrong
  (missed items, overlapping boxes, false positives);
- the score RANKS cases for dispatch order; it does not measure waste
  volume, weight, or toxicity. Treat it as triage, not measurement.

No DB imports here: score_case() takes plain CaseFacts. Adapters that read
rows/files live in service.py (real backend) and the demo backend.
"""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

SCORE_VERSION = "1.0"


# --------------------------------------------------------------------------
# Config
# --------------------------------------------------------------------------

@dataclass
class PriorityConfig:
    """Weights must sum to 1.0 — misconfiguration fails fast with ValueError
    so a broken config can never silently skew dispatch order."""

    w_items: float = 0.25
    w_area: float = 0.20
    w_class: float = 0.20
    w_reporters: float = 0.15
    w_age: float = 0.20
    # Normalization caps (documented, tunable).
    item_cap: int = 20          # >= 20 items saturates the item component
    reporter_cap: int = 50      # log curve saturates at 50 reporters
    age_cap_days: float = 30.0  # older than this stops gaining urgency
    extra_class_bonus: float = 0.05  # per additional class type, capped at 1.0
    # Per-class hazard weights (max wins, not the average).
    hazard_weights: Dict[str, float] = field(default_factory=lambda: {
        "Glass Waste": 1.0,
        "Metal Waste": 0.8,
        "Plastic Waste": 0.6,
        "Styrofoam": 0.5,
        "Cardboard_Paper": 0.4,
    })

    def __post_init__(self) -> None:
        total = (self.w_items + self.w_area + self.w_class
                 + self.w_reporters + self.w_age)
        if not math.isclose(total, 1.0, abs_tol=1e-6):
            raise ValueError(
                f"Priority weights must sum to 1.0, got {total:.4f} "
                f"(items={self.w_items} area={self.w_area} class={self.w_class} "
                f"reporters={self.w_reporters} age={self.w_age}). "
                f"Fix the config — refusing to start with skewed weights.")


def config_from_env(prefix: str = "PRIORITY_") -> PriorityConfig:
    """Build config from PRIORITY_* env vars (falls back to defaults)."""
    def _f(name: str, default: float) -> float:
        try:
            return float(os.getenv(prefix + name, str(default)))
        except (TypeError, ValueError):
            return default

    return PriorityConfig(
        w_items=_f("W_ITEMS", 0.25),
        w_area=_f("W_AREA", 0.20),
        w_class=_f("W_CLASS", 0.20),
        w_reporters=_f("W_REPORTERS", 0.15),
        w_age=_f("W_AGE", 0.20),
    )


# --------------------------------------------------------------------------
# Inputs
# --------------------------------------------------------------------------

@dataclass
class CaseFacts:
    """Aggregated facts for ONE case. Build from the member report with the
    highest detected item count (not the sum — avoids double counting)."""

    item_count: int = 0            # max detection count across members
    covered_area_frac: float = 0.0  # sum(box areas)/image area, capped at 1.0
    classes: List[str] = field(default_factory=list)  # classes on that report
    distinct_reporters: int = 0
    days_open: float = 0.0
    # Optional hook: 1.0 default. Callers pass e.g. 1.2 near schools;
    # never invent it — leave 1.0 unless real location data exists.
    location_sensitivity: float = 1.0


# --------------------------------------------------------------------------
# Normalization (each 0..1)
# --------------------------------------------------------------------------

def norm_items(count: int, config: PriorityConfig) -> float:
    return min(max(int(count), 0), config.item_cap) / float(config.item_cap)


def norm_area(frac: float) -> float:
    try:
        return min(max(float(frac), 0.0), 1.0)
    except (TypeError, ValueError):
        return 0.0


def norm_class(classes: List[str], config: PriorityConfig) -> float:
    """Max hazard weight + small bonus per extra class type, capped at 1.0."""
    names = [c for c in (classes or []) if c]
    if not names:
        return 0.0
    distinct = set(names)
    top = max((config.hazard_weights.get(c, 0.4) for c in distinct), default=0.0)
    return min(top + config.extra_class_bonus * max(len(distinct) - 1, 0), 1.0)


def norm_reporters(n: int, config: PriorityConfig) -> float:
    """Logarithmic: 50 reports are not 10x worse than 5."""
    n = max(int(n), 0)
    if n <= 0:
        return 0.0
    cap = max(config.reporter_cap, 1)
    return min(math.log10(1 + n) / math.log10(1 + cap), 1.0)


def norm_age(days_open: float, config: PriorityConfig) -> float:
    """Older neglected piles gain urgency, capped at AGE_CAP_DAYS."""
    try:
        days = max(float(days_open), 0.0)
    except (TypeError, ValueError):
        return 0.0
    return min(days / config.age_cap_days, 1.0)


# --------------------------------------------------------------------------
# Scoring
# --------------------------------------------------------------------------

def score_case(facts: CaseFacts,
               config: Optional[PriorityConfig] = None) -> dict:
    """Score one case. Returns {score, components, version}.

    components maps each part to {raw, normalized, weight, contribution}
    so the UI can show WHY a case ranks high. Contributions always sum to
    score/100 (up to rounding).
    """
    config = config or PriorityConfig()
    parts = [
        ("items", facts.item_count,
         norm_items(facts.item_count, config), config.w_items),
        ("area", round(facts.covered_area_frac, 4),
         norm_area(facts.covered_area_frac), config.w_area),
        ("class", list(facts.classes or []),
         norm_class(facts.classes, config), config.w_class),
        ("reporters", facts.distinct_reporters,
         norm_reporters(facts.distinct_reporters, config), config.w_reporters),
        ("age", round(facts.days_open, 2),
         norm_age(facts.days_open, config), config.w_age),
    ]
    components = {}
    total = 0.0
    for name, raw, normalized, weight in parts:
        contribution = weight * normalized
        total += contribution
        components[name] = {
            "raw": raw,
            "normalized": round(normalized, 4),
            "weight": weight,
            "contribution": round(contribution, 4),
        }
    mult = facts.location_sensitivity if facts.location_sensitivity else 1.0
    try:
        mult = max(float(mult), 0.0)
    except (TypeError, ValueError):
        mult = 1.0
    score = round(100.0 * total * mult, 1)
    return {"score": score, "components": components,
            "location_sensitivity": mult, "version": SCORE_VERSION}


def priority_band(score: float) -> str:
    """Colour band for UI badges: critical / high / watch / low."""
    try:
        s = float(score)
    except (TypeError, ValueError):
        return "low"
    if s >= 75:
        return "critical"
    if s >= 50:
        return "high"
    if s >= 25:
        return "watch"
    return "low"
