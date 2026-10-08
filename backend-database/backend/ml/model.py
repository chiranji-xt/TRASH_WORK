"""
YOLOv8 Garbage Detection Model
Handles loading and inference for the trained garbage classification model
"""
import os
# Set environment variable BEFORE importing torch/ultralytics
os.environ['TORCH_ALLOW_UNSAFE_LOADING'] = '1'

from ultralytics import YOLO
from ..config import MODEL_PATH

# Global model instance
model = None

# Class names mapping - Original model (8 classes)
CLASS_NAMES = {
    0: "Cardboard Waste",
    1: "Cigarette",
    2: "Food Waste",
    3: "Glass Waste",
    4: "Metal Waste",
    5: "Paper Waste",
    6: "Plastic Waste",
    7: "Styrofoam"
}

def load_model():
    """Load the YOLOv8 model from the specified path"""
    global model  # CRITICAL: Must declare global to modify module-level variable
    
    if model is not None:
        print("[ML MODEL] Model already loaded")
        return model
    
    try:
        print(f"[ML MODEL] Loading model from: {MODEL_PATH}")
        
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at: {MODEL_PATH}")
        
        # Load YOLO model with torch.load workaround for pickle compatibility
        print("[ML MODEL] Initializing YOLO model...")
        
        # Try loading with weights_only=False for older PyTorch models
        import torch
        import warnings
        warnings.filterwarnings('ignore', category=FutureWarning)
        
        # Monkey-patch torch.load to use weights_only=False
        original_load = torch.load
        def patched_load(*args, **kwargs):
            kwargs['weights_only'] = False
            return original_load(*args, **kwargs)
        torch.load = patched_load
        
        try:
            model = YOLO(MODEL_PATH)
        finally:
            # Restore original torch.load
            torch.load = original_load
        
        print(f"[ML MODEL] ✓ Model loaded successfully!")
        print(f"[ML MODEL] Model type: {type(model)}")
        print(f"[ML MODEL] Number of classes: {len(CLASS_NAMES)}")
        print(f"[ML MODEL] Classes: {list(CLASS_NAMES.values())}")
        
        return model
        
    except Exception as e:
        print(f"[ML MODEL ERROR] ✗ Failed to load model!")
        print(f"[ML MODEL ERROR] Error type: {type(e).__name__}")
        print(f"[ML MODEL ERROR] Error message: {str(e)}")
        import traceback
        traceback.print_exc()
        # Don't raise - let it fall back to pending
        return None

def predict(image_path):
    """
    Run inference on an image and return predictions
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        tuple: (primary_class, confidence, all_detections)
            - primary_class (str): Class name of highest confidence detection
            - confidence (float): Confidence score (0-1) of primary detection
            - all_detections (list): List of all detections with details
    """
    global model
    
    # Load model if not already loaded
    if model is None:
        load_model()
    
    try:
        print(f"[ML MODEL] Running inference on: {image_path}")
        
        # Run inference with 25% confidence threshold
        # Higher threshold reduces false positives from backgrounds/patterns
        results = model(image_path, conf=0.25, verbose=False)
        
        # Get the first result (single image)
        result = results[0]
        
        # Check if any detections were found
        if len(result.boxes) == 0:
            print(f"[ML MODEL] No detections found")
            return "No Waste Detected", 0.0, []
        
        # Extract all detections
        all_detections = []
        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
            
            detection = {
                "class": CLASS_NAMES.get(class_id, f"Unknown-{class_id}"),
                "class_id": class_id,
                "confidence": round(confidence, 4),
                "bbox": [round(coord, 2) for coord in bbox]
            }
            all_detections.append(detection)
        
        # Sort by confidence (highest first)
        all_detections.sort(key=lambda x: x["confidence"], reverse=True)
        
        # Primary detection is the one with highest confidence
        primary = all_detections[0]
        primary_class = primary["class"]
        primary_confidence = primary["confidence"]
        
        print(f"[ML MODEL] Primary detection: {primary_class} ({primary_confidence:.2%})")
        print(f"[ML MODEL] Total detections: {len(all_detections)}")
        
        return primary_class, primary_confidence, all_detections
        
    except Exception as e:
        print(f"[ML MODEL ERROR] Prediction failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e

def get_class_name(class_id):
    """Get class name from class ID"""
    return CLASS_NAMES.get(class_id, f"Unknown-{class_id}")

def run_inference(image_path):
    """
    Run inference on an image and save annotated version with bounding boxes
    
    Args:
        image_path (str): Path to the image file
        
    Returns:
        tuple: (all_detections, boxed_filename)
            - all_detections (list): List of all detections with details
            - boxed_filename (str): Filename of the annotated image
    """
    global model
    
    # Load model if not already loaded
    if model is None:
        load_model()
    
    try:
        print(f"[ML MODEL] Running inference on: {image_path}")
        
        # Run inference with 25% confidence threshold
        # Higher threshold reduces false positives from backgrounds/patterns
        results = model(image_path, conf=0.25, verbose=False)
        
        # Get the first result (single image)
        result = results[0]
        
        # Debug logging
        print(f"[ML MODEL] Raw detections found: {len(result.boxes)}")
        
        # Generate annotated image with bounding boxes
        import cv2
        from ..config import ANNOTATED_DIR
        
        boxed_name = "boxed_" + os.path.basename(image_path)
        boxed_path = os.path.join(ANNOTATED_DIR, boxed_name)
        
        # Save image with bounding boxes using YOLO's plot method
        annotated = result.plot()
        cv2.imwrite(boxed_path, annotated)
        print(f"[ML MODEL] Saved annotated image to: {boxed_path}")
        
        # Extract all detections
        all_detections = []
        for box in result.boxes:
            class_id = int(box.cls[0])
            confidence = float(box.conf[0])
            bbox = box.xyxy[0].tolist()  # [x1, y1, x2, y2]
            
            detection = {
                "class": CLASS_NAMES.get(class_id, f"Unknown-{class_id}"),
                "class_id": class_id,
                "confidence": round(confidence, 4),
                "bbox": [round(coord, 2) for coord in bbox]
            }
            all_detections.append(detection)
        
        # Sort by confidence (highest first)
        all_detections.sort(key=lambda x: x["confidence"], reverse=True)
        
        print(f"[ML MODEL] Total detections: {len(all_detections)}")
        if all_detections:
            print(f"[ML MODEL] Primary detection: {all_detections[0]['class']} ({all_detections[0]['confidence']:.2%})")
        
        # Return just the filename (not full path) for consistency
        return all_detections, boxed_name
        
    except Exception as e:
        print(f"[ML MODEL ERROR] Inference failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise e

def get_model_info():
    """Get information about the loaded model"""
    global model
    
    if model is None:
        return {"status": "not_loaded"}
    
    return {
        "status": "loaded",
        "model_path": MODEL_PATH,
        "num_classes": len(CLASS_NAMES),
        "classes": CLASS_NAMES
    }
