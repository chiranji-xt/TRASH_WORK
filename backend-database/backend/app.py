from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from . import models, crud, db, config
from .ml import model as ml_model
import shutil
import os
import uuid
from datetime import datetime
from geoalchemy2.shape import to_shape

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allow all for now
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount uploads (original images)
app.mount("/uploads", StaticFiles(directory=config.UPLOAD_DIR), name="uploads")

# Mount annotated images (YOLO boxed images)
app.mount("/annotated", StaticFiles(directory=config.ANNOTATED_DIR), name="annotated")

# Dependency
def get_db():
    db_session = db.SessionLocal()
    try:
        yield db_session
    finally:
        db_session.close()

@app.get("/health")
def health_check():
    return {"status": "ok"}

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
    """
    Endpoint for mobile app to upload image and get prediction
    """
    print(f"[PREDICT] Received request - lat: {latitude}, lon: {longitude}, file: {file.filename}")
    print(f"[PREDICT] Optional fields - category: {category}, severity: {severity}, title: {title}, description: {description}")
    
    try:
        # Validate file
        print(f"[PREDICT] File content type: {file.content_type}")
        
        # More lenient validation - accept if content_type is image/* OR if filename has image extension
        is_valid_image = False
        
        if file.content_type and file.content_type.startswith("image/"):
            is_valid_image = True
        elif file.filename:
            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            file_lower = file.filename.lower()
            if any(file_lower.endswith(ext) for ext in valid_extensions):
                is_valid_image = True
        
        if not is_valid_image:
            print(f"[PREDICT ERROR] Invalid file - content_type: {file.content_type}, filename: {file.filename}")
            raise HTTPException(status_code=400, detail="File must be an image")
        
        print(f"[PREDICT] File validation passed")
        
        # Save file
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(config.UPLOAD_DIR, filename)
        
        print(f"[PREDICT] Saving file to: {file_path}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"[PREDICT] File saved successfully")
        
        # Run ML prediction with annotated image generation
        prediction = "pending"
        confidence = None
        all_detections = []
        detections_json = None
        boxed_filename = None
        
        try:
            print(f"[PREDICT] Running ML prediction...")
            all_detections, boxed_filename = ml_model.run_inference(file_path)
            
            if all_detections:
                # Primary detection is the one with highest confidence
                primary = all_detections[0]
                prediction = primary["class"]
                confidence = primary["confidence"]
                
                print(f"[PREDICT] Primary prediction: {prediction}, Confidence: {confidence}")
                print(f"[PREDICT] Total detections: {len(all_detections)}")
                print(f"[PREDICT] Boxed image: {boxed_filename}")
                
                # Prepare detections JSON for database
                detections_json = {
                    "count": len(all_detections),
                    "primary": {
                        "class": prediction,
                        "confidence": confidence,
                        "bbox": all_detections[0]["bbox"]
                    },
                    "all": all_detections
                }
            else:
                prediction = "No Waste Detected"
                confidence = 0.0
            
        except Exception as e:
            print(f"[PREDICT WARNING] ML prediction failed: {str(e)}")
            import traceback
            traceback.print_exc()
            # If prediction fails, use default values
            prediction = "pending"
            confidence = None
            all_detections = []
            detections_json = None
            boxed_filename = None
        
        # Create DB entry
        print(f"[PREDICT] Creating database entry...")
        try:
            report = crud.create_garbage_report(db, filename, latitude, longitude, prediction, confidence, detections_json, boxed_filename)
            print(f"[PREDICT] Database entry created")
            print(f"[PREDICT] Report object: {report}")
            print(f"[PREDICT] Report ID: {report.id}")
            print(f"[PREDICT] Report ID type: {type(report.id)}")
            
            if report.id is None:
                print(f"[PREDICT ERROR] Report ID is None after database creation!")
                raise HTTPException(status_code=500, detail="Failed to create report - ID is None")
                
        except Exception as db_error:
            print(f"[PREDICT DB ERROR] {type(db_error).__name__}: {str(db_error)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
        
        response = {
            "success": True,
            "report_id": report.id,
            "prediction": prediction,
            "confidence": confidence,
            "image_path": f"/uploads/{filename}",
            "boxed_image_path": f"/annotated/{boxed_filename}" if boxed_filename else None,
            "detections": {
                "count": len(all_detections),
                "items": all_detections[:5]  # Return top 5 detections to avoid large response
            } if all_detections else None
        }
        
        print(f"[PREDICT] Returning response: {response}")
        return response
        
    except HTTPException as he:
        print(f"[PREDICT HTTP ERROR] {he.status_code}: {he.detail}")
        raise he
    except Exception as e:
        print(f"[PREDICT CRITICAL ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
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
    print(f"[UPLOAD-REPORT] Optional fields - category: {category}, severity: {severity}, title: {title}, description: {description}")
    
    try:
        # Validate file
        print(f"[UPLOAD-REPORT] File content type: {file.content_type}")
        
        # More lenient validation - accept if content_type is image/* OR if filename has image extension
        is_valid_image = False
        
        if file.content_type and file.content_type.startswith("image/"):
            is_valid_image = True
        elif file.filename:
            # Check file extension
            valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
            file_lower = file.filename.lower()
            if any(file_lower.endswith(ext) for ext in valid_extensions):
                is_valid_image = True
        
        if not is_valid_image:
            print(f"[UPLOAD-REPORT ERROR] Invalid file - content_type: {file.content_type}, filename: {file.filename}")
            raise HTTPException(status_code=400, detail="File must be an image")
        
        print(f"[UPLOAD-REPORT] File validation passed")
        
        # Save file
        file_ext = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex}.{file_ext}"
        file_path = os.path.join(config.UPLOAD_DIR, filename)
        
        print(f"[UPLOAD-REPORT] Saving file to: {file_path}")
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        print(f"[UPLOAD-REPORT] File saved successfully")
            
        # Run ML prediction with annotated image generation (same as /predict endpoint)
        prediction = "pending"
        confidence = None
        all_detections = []
        detections_json = None
        boxed_filename = None
        
        try:
            print(f"[UPLOAD-REPORT] Running ML prediction...")
            all_detections, boxed_filename = ml_model.run_inference(file_path)
            
            if all_detections:
                # Primary detection is the one with highest confidence
                primary = all_detections[0]
                prediction = primary["class"]
                confidence = primary["confidence"]
                
                print(f"[UPLOAD-REPORT] Primary prediction: {prediction}, Confidence: {confidence}")
                print(f"[UPLOAD-REPORT] Total detections: {len(all_detections)}")
                print(f"[UPLOAD-REPORT] Boxed image: {boxed_filename}")
                
                # Prepare detections JSON for database
                detections_json = {
                    "count": len(all_detections),
                    "primary": {
                        "class": prediction,
                        "confidence": confidence,
                        "bbox": all_detections[0]["bbox"]
                    },
                    "all": all_detections
                }
            else:
                prediction = "No Waste Detected"
                confidence = 0.0
            
        except Exception as e:
            print(f"[UPLOAD-REPORT WARNING] ML prediction failed: {str(e)}")
            import traceback
            traceback.print_exc()
            # If prediction fails, use default values
            prediction = "pending"
            confidence = None
            all_detections = []
            detections_json = None
            boxed_filename = None
        
        print(f"[UPLOAD-REPORT] Creating database entry...")
        try:
            report = crud.create_garbage_report(db, filename, latitude, longitude, prediction, confidence, detections_json, boxed_filename)
            print(f"[UPLOAD-REPORT] Database entry created")
            print(f"[UPLOAD-REPORT] Report object: {report}")
            print(f"[UPLOAD-REPORT] Report ID: {report.id}")
            print(f"[UPLOAD-REPORT] Report ID type: {type(report.id)}")
            
            if report.id is None:
                print(f"[UPLOAD-REPORT ERROR] Report ID is None after database creation!")
                raise HTTPException(status_code=500, detail="Failed to create report - ID is None")
                
        except Exception as db_error:
            print(f"[UPLOAD-REPORT DB ERROR] {type(db_error).__name__}: {str(db_error)}")
            import traceback
            traceback.print_exc()
            raise HTTPException(status_code=500, detail=f"Database error: {str(db_error)}")
        
        response = {
            "success": True,
            "report_id": report.id,
            "prediction": prediction,
            "confidence": confidence,
            "image_path": f"/uploads/{filename}",
            "boxed_image_path": f"/annotated/{boxed_filename}" if boxed_filename else None,
            "detections": {
                "count": len(all_detections),
                "items": all_detections[:5]  # Return top 5 detections
            } if all_detections else None
        }
        
        print(f"[UPLOAD-REPORT] Returning response: {response}")
        return response
        
    except HTTPException as he:
        print(f"[UPLOAD-REPORT HTTP ERROR] {he.status_code}: {he.detail}")
        raise he
    except Exception as e:
        print(f"[UPLOAD-REPORT CRITICAL ERROR] {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/reports")
def read_reports(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    reports = crud.get_reports(db, skip=skip, limit=limit)
    results = []
    for r in reports:
        point = to_shape(r.geom)
        results.append({
            "id": r.id,
            "image_path": f"/uploads/{r.image_path}" if r.image_path else None,
            "boxed_image_path": f"/annotated/{r.boxed_image_path}" if r.boxed_image_path else None,
            "prediction": r.prediction,
            "confidence": r.confidence,
            "status": r.status,
            "latitude": point.y,
            "longitude": point.x,
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
        "image_path": f"/uploads/{r.image_path}" if r.image_path else None,
        "boxed_image_path": f"/annotated/{r.boxed_image_path}" if r.boxed_image_path else None,
        "prediction": r.prediction,
        "confidence": r.confidence,
        "status": r.status,
        "latitude": point.y,
        "longitude": point.x,
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
            "image_path": f"/uploads/{r.image_path}" if r.image_path else None,
            "boxed_image_path": f"/annotated/{r.boxed_image_path}" if r.boxed_image_path else None,
            "prediction": r.prediction,
            "confidence": r.confidence,
            "status": r.status,
            "latitude": point.y,
            "longitude": point.x,
            "created_at": r.created_at
        })
    return results

@app.patch("/reports/{report_id}/status")
def update_report_status(report_id: int, status: str, db: Session = Depends(get_db)):
    """
    Update the status of a garbage report
    
    Args:
        report_id: ID of the report to update
        status: New status ('pending' or 'cleaned')
    """
    # Normalize status to lowercase for case-insensitive comparison
    status = status.lower().strip()
    
    # Validate status
    valid_statuses = ['pending', 'cleaned']
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Get the report
    report = crud.get_report(db, report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")
    
    # Update status
    report.status = status
    db.commit()
    db.refresh(report)
    
    print(f"[UPDATE STATUS] Report #{report_id} status updated to: {status}")
    
    return {
        "success": True,
        "report_id": report_id,
        "status": status,
        "message": f"Report status updated to '{status}'"
    }

@app.get("/reports/by-status/{status}")
def get_reports_by_status(status: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """
    Get reports filtered by status
    
    Args:
        status: Filter by status ('pending' or 'cleaned')
        skip: Number of records to skip
        limit: Maximum number of records to return
    """
    # Validate status
    valid_statuses = ['pending', 'cleaned']
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )
    
    # Query reports by status
    reports = db.query(models.GarbageReport).filter(
        models.GarbageReport.status == status
    ).offset(skip).limit(limit).all()
    
    results = []
    for r in reports:
        point = to_shape(r.geom)
        results.append({
            "id": r.id,
            "image_path": f"/uploads/{r.image_path}" if r.image_path else None,
            "boxed_image_path": f"/annotated/{r.boxed_image_path}" if r.boxed_image_path else None,
            "prediction": r.prediction,
            "confidence": r.confidence,
            "status": r.status,
            "latitude": point.y,
            "longitude": point.x,
            "created_at": r.created_at
        })
    
    return {
        "status_filter": status,
        "count": len(results),
        "reports": results
    }
