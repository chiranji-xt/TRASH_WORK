import logging

from sqlalchemy import func
from sqlalchemy.orm import Session
from geoalchemy2.shape import from_shape
from shapely.geometry import Point

from . import models

logger = logging.getLogger(__name__)


def create_garbage_report(db: Session, image_path: str, lat: float, lon: float,
                          prediction: str = "pending", confidence: float = None,
                          detections: dict = None, boxed_image_path: str = None):
    logger.info("Creating report: image=%s lat=%s lon=%s prediction=%s conf=%s",
                image_path, lat, lon, prediction, confidence)

    # Note: PostGIS uses (lon, lat)
    point = Point(lon, lat)

    db_report = models.GarbageReport(
        image_path=image_path,
        boxed_image_path=boxed_image_path,
        prediction=prediction,
        confidence=confidence,
        detections=detections,  # Store all detections (+ severity)
        geom=from_shape(point, srid=4326)
    )

    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    logger.info("Report created with id=%s", db_report.id)

    return db_report


def get_reports(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.GarbageReport).offset(skip).limit(limit).all()


def get_report(db: Session, report_id: int):
    return db.query(models.GarbageReport).filter(models.GarbageReport.id == report_id).first()


def get_reports_in_area(db: Session, min_lon: float, min_lat: float, max_lon: float, max_lat: float):
    # Using GeoAlchemy2 filter
    box = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
    return db.query(models.GarbageReport).filter(models.GarbageReport.geom.intersects(box)).all()
