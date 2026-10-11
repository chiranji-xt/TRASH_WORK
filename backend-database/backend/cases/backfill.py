"""Backfill cases for pre-existing reports: python -m backend.cases.backfill."""
import logging

from ..db import SessionLocal
from .service import backfill_caseless_reports

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    db = SessionLocal()
    try:
        stats = backfill_caseless_reports(db)
        print(stats)
    finally:
        db.close()
