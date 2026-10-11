"""Top-level re-exports for the cases feature."""
from .matching import (
    MatchConfig,
    ReportInput,
    CaseSummary,
    CandidateScore,
    match_report,
    rank_candidates,
    decide,
)

__all__ = [
    "MatchConfig",
    "ReportInput",
    "CaseSummary",
    "CandidateScore",
    "match_report",
    "rank_candidates",
    "decide",
]
