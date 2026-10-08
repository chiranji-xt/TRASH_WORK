from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
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
