from sqlalchemy.orm import Session
from . import models
from geoalchemy2.shape import from_shape
from shapely.geometry import Point
from sqlalchemy import func

def create_garbage_report(db: Session, image_path: str, lat: float, lon: float, prediction: str = "pending", confidence: float = None, detections: dict = None, boxed_image_path: str = None):
    print(f"[CRUD] Creating garbage report - image: {image_path}, lat: {lat}, lon: {lon}")
    print(f"[CRUD] Prediction: {prediction}, Confidence: {confidence}")
    print(f"[CRUD] Boxed image: {boxed_image_path}")
    
    # Create geometry point
    # Note: PostGIS uses (lon, lat)
    point = Point(lon, lat)
    print(f"[CRUD] Created point: {point}")
    
    db_report = models.GarbageReport(
        image_path=image_path,
        boxed_image_path=boxed_image_path,
        prediction=prediction,
        confidence=confidence,
        detections=detections,  # Store all detections
        geom=from_shape(point, srid=4326)
    )
    print(f"[CRUD] Created report object, ID before add: {db_report.id}")
    
    db.add(db_report)
    print(f"[CRUD] Added to session, ID before commit: {db_report.id}")
    
    db.commit()
    print(f"[CRUD] Committed, ID after commit: {db_report.id}")
    
    db.refresh(db_report)
    print(f"[CRUD] Refreshed, ID after refresh: {db_report.id}")
    
    return db_report

def get_reports(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.GarbageReport).offset(skip).limit(limit).all()

def get_report(db: Session, report_id: int):
    return db.query(models.GarbageReport).filter(models.GarbageReport.id == report_id).first()

def get_reports_in_area(db: Session, min_lon: float, min_lat: float, max_lon: float, max_lat: float):
    # Using GeoAlchemy2 filter
    box = func.ST_MakeEnvelope(min_lon, min_lat, max_lon, max_lat, 4326)
    return db.query(models.GarbageReport).filter(models.GarbageReport.geom.intersects(box)).all()
