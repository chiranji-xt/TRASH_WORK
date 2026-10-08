from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models, crud, db, config
# from .ml import model as ml_model # COMMENTED OUT: We will use direct YOLO integration
import shutil
import os
import uuid
from datetime import datetime
from geoalchemy2.shape import to_shape
from ultralytics import YOLO # ADDED: Import YOLO directly

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads
app.mount("/uploads", StaticFiles(directory=config.UPLOAD_DIR), name="uploads")

# Dependency
def get_db():
    db_session = db.SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()

# ADDED: Load Model Globally
print("[INIT] Loading YOLO model...")
try:
    # Ensure best.pt is in the same directory or provide absolute path
    model = YOLO('best.pt') 
    print("[INIT] YOLO model loaded successfully!")
except Exception as e:
    print(f"[INIT ERROR] Failed to load YOLO model: {e}")
    model = None

@app.get("/health")
def health_check():
    return {"status": "ok", "model_loaded": model is not None}

def run_yolo_prediction(file_path):
    """
    Helper function to run YOLO prediction on a file
    Returns: (prediction_class, confidence, detections_list)
    """
    if model is None:
        print("[PREDICT WARNING] Model is not loaded, returning pending")
        return "pending", None, []

    try:
        results = model(file_path, conf=0.1)
        
        all_detections = []
        primary_pred = "unsorted_waste" # Default if nothing detected but model ran
        primary_conf = 0.0
        
        for result in results:
            for box in result.boxes:
                cls_id = int(box.cls[0])
                class_name = model.names[cls_id]
                conf = float(box.conf[0])
                bbox = box.xyxy[0].tolist()
                
                all_detections.append({
                    "class": class_name,
                    "confidence": conf,
                    "bbox": bbox
                })
                
                # Simple logic: take highest confidence as primary
                if conf > primary_conf:
                    primary_conf = conf
                    primary_pred = class_name
        
        if not all_detections:
            return "unsorted_waste", 0.0, []
            
        return primary_pred, primary_conf, all_detections
        
    except Exception as e:
        print(f"[PREDICT ERROR] YOLO inference failed: {e}")
        return "pending", None, []


@app.post("/predict")
async def predict_garbage(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: str = Form(None),
    severity: int = Form(None),
    title: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    print(f"[PREDICT] Received request - lat: {latitude}, lon: {longitude}, file: {file.filename}")
    
    try:
        # Validate file
        is_valid_image = False
        if file.content_type and file.content_type.startswith("image/"):
            is_valid_image = True
        elif file.filename:
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            file_lower = file.filename.lower()
            if any(file_lower.endswith(ext) for ext in valid_extensions):
                is_valid_image = True
        
        if not is_valid_image:
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Save file
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(config.UPLOAD_DIR, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Run ML prediction (DIRECT CALL)
        print(f"[PREDICT] Running ML prediction...")
        prediction, confidence, all_detections = run_yolo_prediction(file_path)
        print(f"[PREDICT] Result: {prediction}, Conf: {confidence}, Count: {len(all_detections)}")
        
        # Prepare detections JSON
        detections_json = None
        if all_detections:
            detections_json = {
                "count": len(all_detections),
                "primary": {
                    "class": prediction,
                    "confidence": confidence,
                    "bbox": all_detections[0]["bbox"] if all_detections else None
                },
                "all": all_detections
            }
        
        # Create DB entry
        try:
            report = crud.create_garbage_report(db, filename, latitude, longitude, prediction, confidence, detections_json)
            if report.id is None:
                raise HTTPException(status_code=500, detail="Failed to create report - ID is None")
        except Exception as db_error:
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
        
        response = {
            "success": True,
            "report_id": report.id,
            "prediction": prediction,
            "confidence": confidence,
            "image_path": filename,
            "detections": {
                "count": len(all_detections),
                "items": all_detections[:5]
            } if all_detections else None
        }
        return response
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[PREDICT CRITICAL ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@app.post("/upload-report")
async def upload_report(
    file: UploadFile = File(...),
    latitude: float = Form(...),
    longitude: float = Form(...),
    category: str = Form(None),
    severity: int = Form(None),
    title: str = Form(None),
    description: str = Form(None),
    db: Session = Depends(get_db)
):
    print(f"[UPLOAD-REPORT] Received request - lat: {latitude}, lon: {longitude}, file: {file.filename}")
    
    try:
        # Validate file
        is_valid_image = False
        if file.content_type and file.content_type.startswith("image/"):
            is_valid_image = True
        elif file.filename:
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            file_lower = file.filename.lower()
            if any(file_lower.endswith(ext) for ext in valid_extensions):
                is_valid_image = True
        
        if not is_valid_image:
            raise HTTPException(status_code=400, detail="File must be an image")
        
        # Save file
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(config.UPLOAD_DIR, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Run ML prediction (DIRECT CALL)
        print(f"[UPLOAD-REPORT] Running ML prediction...")
        prediction, confidence, all_detections = run_yolo_prediction(file_path)
        print(f"[UPLOAD-REPORT] Result: {prediction}, Conf: {confidence}, Count: {len(all_detections)}")
            
        # Prepare detections JSON
        detections_json = None
        if all_detections:
            detections_json = {
                "count": len(all_detections),
                "primary": {
                    "class": prediction,
                    "confidence": confidence,
                    "bbox": all_detections[0]["bbox"] if all_detections else None
                },
                "all": all_detections
            }
        
        print(f"[UPLOAD-REPORT] Creating database entry...")
        try:
            report = crud.create_garbage_report(db, filename, latitude, longitude, prediction, confidence, detections_json)
            if report.id is None:
                raise HTTPException(status_code=500, detail="Failed to create report - ID is None")
        except Exception as db_error:
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
        
        response = {
            "success": True,
            "report_id": report.id,
            "prediction": prediction,
            "confidence": confidence,
            "image_path": filename,
            "detections": {
                "count": len(all_detections),
                "items": all_detections[:5]
            } if all_detections else None
        }
        return response
        
    except HTTPException as he:
        raise he
    except Exception as e:
        print(f"[UPLOAD-REPORT CRITICAL ERROR] {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/reports")
def read_reports(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    reports = crud.get_reports(db, skip=skip, limit=limit)
    results = []
    for r in reports:
        point = to_shape(r.geom)
        results.append({
            "id": r.id,
            "image_path": r.image_path,
            "prediction": r.prediction,
            "confidence": r.confidence,
            "latitude": point.y,
            "longitude": point.x,
            "status": getattr(r, "status", "Pending"),
            "created_at": r.created_at
        })
    return results

@app.get("/reports/{report_id}")
def read_report(report_id: int, db: Session = Depends(get_db)):
    r = crud.get_report(db, report_id)
    if r is None:
        raise HTTPException(status_code=404, detail="Report not found")
    
    point = to_shape(r.geom)
    
    return {
        "id": r.id,
        "image_path": r.image_path,
        "prediction": r.prediction,
        "confidence": r.confidence,
        "latitude": point.y,
        "longitude": point.x,
        "status": getattr(r, "status", "Pending"),
        "created_at": r.created_at
    }

@app.get("/reports-in-area")
def read_reports_in_area(min_lon: float, min_lat: float, max_lon: float, max_lat: float, db: Session = Depends(get_db)):
    reports = crud.get_reports_in_area(db, min_lon, min_lat, max_lon, max_lat)
    results = []
    for r in reports:
        point = to_shape(r.geom)
        results.append({
            "id": r.id,
            "image_path": r.image_path,
            "prediction": r.prediction,
            "confidence": r.confidence,
            "latitude": point.y,
            "longitude": point.x,
            "status": getattr(r, "status", "Pending"),
            "created_at": r.created_at
        })
    return results
