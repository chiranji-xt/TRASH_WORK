from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from geoalchemy2 import Geometry
from .db import Base
import datetime

class GarbageReport(Base):
    __tablename__ = "garbage_reports"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True)
    image_path = Column(String, nullable=False)
    boxed_image_path = Column(String, nullable=True)  # Path to annotated image with bounding boxes
    prediction = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)
    detections = Column(JSON, nullable=True)  # Store all detections with bounding boxes
    status = Column(String, default='pending', nullable=False)  # 'pending' or 'cleaned'
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    geom = Column(Geometry('POINT', srid=4326))
    # Duplicate-merging ("cases" feature): the case this report belongs to.
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True, index=True)

    case = relationship("Case", back_populates="reports", foreign_keys=[case_id])


class Case(Base):
    """A real-world garbage problem: one or more reports of the same pile.

    The dashboard shows one marker per case with a report_count badge.
    """

    __tablename__ = "cases"

    id = Column(Integer, primary_key=True, index=True)
    centroid = Column(Geometry('POINT', srid=4326), nullable=True)
    status = Column(String, default='open', nullable=False)  # 'open' | 'cleaned' | 'reopened'
    first_reported_at = Column(DateTime, nullable=True)
    last_reported_at = Column(DateTime, nullable=True)
    report_count = Column(Integer, default=0, nullable=False)
    distinct_reporters = Column(Integer, default=0, nullable=False)
    # If this case re-appeared near a previously cleaned case, that old id.
    recurrence_of = Column(Integer, ForeignKey("cases.id"), nullable=True)
    # Suggestion for human review: "possible duplicate of case X".
    suggested_duplicate_of = Column(Integer, ForeignKey("cases.id"), nullable=True)
    # Formula version that last scored this case (traceability).
    score_version = Column(String, nullable=True)
    # Verification-driven closure (cleanup_verifications.id).
    closed_at = Column(DateTime, nullable=True)
    closing_verification_id = Column(Integer, ForeignKey("cleanup_verifications.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    reports = relationship("GarbageReport", back_populates="case",
                           foreign_keys="GarbageReport.case_id")


class CaseMergeLog(Base):
    """Audit trail of every merge decision (auto or manual)."""

    __tablename__ = "case_merge_log"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("garbage_reports.id"), nullable=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=True)
    # auto_merged | suggested | new_case | manual_merge | manual_split | recurrence
    # | verification_passed | verification_failed | verification_review
    # | verification_approved | verification_rejected | admin_override_cleaned
    decision = Column(String, nullable=False)
    score = Column(Float, nullable=True)
    evidence = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)


class CleanupVerification(Base):
    """One cleanup-verification attempt: after-photos + per-check evidence.

    A case closes only via a PASSED verification (or an approved review /
    a reasoned admin override). See backend/verification/checks.py and its
    HONEST LIMIT: the detector cannot prove absence.
    """

    __tablename__ = "cleanup_verifications"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"), nullable=False, index=True)
    cleaner_id = Column(String, nullable=True)
    attempt_no = Column(Integer, default=1, nullable=False)
    photos = Column(JSON, nullable=True)  # list of stored after-photo filenames
    checks = Column(JSON, nullable=True)  # per-photo check evidence
    decision = Column(String, nullable=False)  # passed | failed_still_litter
    #                                        | needs_review | rejected_reuse
    spot_checked = Column(String, nullable=True)  # reason when randomly reviewed
    reviewed_by = Column(String, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    review_reason = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
