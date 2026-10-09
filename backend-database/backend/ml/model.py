"""
YOLOv8 Garbage Detection Model
Handles loading and inference for the trained garbage classification model.

Class names are read from the loaded weights (model.names) instead of a
hardcoded dict, so 5-class and 8-class checkpoints both work without code
changes. A hardcoded fallback is kept only for when no weights are present.

Script-side quality tuning (no retraining needed):
- PER_CLASS_CONF: per-class confidence bars. Plastic gets a high bar because
  validation showed 42% of background predicted as plastic; reliable classes
  (Metal/Glass/Styrofoam) keep low bars to preserve recall.
- IOU_THRESHOLD: NMS setting; lower merges double-boxes more aggressively.
- MIN_BOX_AREA_FRAC: drops tiny noise boxes (background-FP source).
"""
import logging
import os

# Set environment variable BEFORE importing torch/ultralytics
os.environ.setdefault("TORCH_ALLOW_UNSAFE_LOADING", "1")

from ultralytics import YOLO

from ..config import (
    ANNOTATED_DIR,
    CONFIDENCE_THRESHOLD,
    IOU_THRESHOLD,
    MIN_BOX_AREA_FRAC,
    MODEL_PATH,
    PER_CLASS_CONF,
)

logger = logging.getLogger(__name__)

# Global model instance
model = None

# Fallback class names used only if the weights file is missing/unreadable.
# The real names always come from model.names after load.
FALLBACK_CLASS_NAMES = {
    0: "Cardboard_Paper",
    1: "Glass Waste",
    2: "Metal Waste",
    3: "Plastic Waste",
    4: "Styrofoam",
}


def _current_class_names():
    """Return class names from the loaded model, falling back to defaults."""
    global model
    if model is not None:
        try:
            names = getattr(model, "names", None)
            if isinstance(names, dict) and names:
                return {int(k): str(v) for k, v in names.items()}
        except Exception:
            pass
    return dict(FALLBACK_CLASS_NAMES)


def load_model():
    """Load the YOLOv8 model from the specified path."""
    global model

    if model is not None:
        logger.debug("Model already loaded")
        return model

    try:
        logger.info("Loading model from: %s", MODEL_PATH)

        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Model file not found at: {MODEL_PATH}")

        import torch
        import warnings
        warnings.filterwarnings("ignore", category=FutureWarning)

        # Monkey-patch torch.load to use weights_only=False for older checkpoints
        original_load = torch.load

        def patched_load(*args, **kwargs):
            kwargs["weights_only"] = False
            return original_load(*args, **kwargs)

        torch.load = patched_load
        try:
            model = YOLO(MODEL_PATH)
        finally:
            torch.load = original_load

        names = _current_class_names()
        logger.info("Model loaded. %d classes: %s", len(names), sorted(names.values()))
        return model

    except Exception as e:
        logger.exception("Failed to load model: %s", e)
        return None


def _run_model(image_path):
    """Run YOLO with the floor threshold; per-class filtering happens after."""
    global model
    if model is None:
        load_model()
    if model is None:
        raise RuntimeError(f"Model not loaded (MODEL_PATH={MODEL_PATH})")

    # Floor = lowest bar, so no detection above its own class threshold is cut.
    floor = min([CONFIDENCE_THRESHOLD, *PER_CLASS_CONF.values()])
    logger.debug("Inference on %s (conf floor=%s, iou=%s)", image_path, floor, IOU_THRESHOLD)
    results = model(image_path, conf=floor, iou=IOU_THRESHOLD, verbose=False)
    return results[0]


def _extract_detections(result):
    """Convert a YOLO result into a sorted, filtered list of detection dicts.

    Filters (script-side quality tuning):
    1. Per-class confidence bar (Plastic 0.45 default — background-FP guard).
    2. Minimum box-area fraction (drops tiny noise boxes).
    """
    names = _current_class_names()
    try:
        h, w = result.orig_shape
        img_area = float(h * w)
    except Exception:
        img_area = 0.0

    all_detections = []
    for box in result.boxes:
        class_id = int(box.cls[0])
        confidence = float(box.conf[0])
        label = names.get(class_id, f"Unknown-{class_id}")

        bar = PER_CLASS_CONF.get(label, CONFIDENCE_THRESHOLD)
        if confidence < bar:
            continue

        x1, y1, x2, y2 = (round(float(c), 2) for c in box.xyxy[0].tolist())
        if img_area > 0:
            area_frac = max(0.0, x2 - x1) * max(0.0, y2 - y1) / img_area
            if area_frac < MIN_BOX_AREA_FRAC:
                continue
        else:
            area_frac = 0.0

        all_detections.append({
            "class": label,
            "class_id": class_id,
            "confidence": round(confidence, 4),
            "bbox": [x1, y1, x2, y2],
            "area_frac": round(area_frac, 5),
        })
    all_detections.sort(key=lambda x: x["confidence"], reverse=True)
    return all_detections


def _save_annotated(image_path, detections):
    """Draw only the kept (filtered) detections and save the boxed image."""
    import cv2

    boxed_name = "boxed_" + os.path.basename(image_path)
    boxed_path = os.path.join(ANNOTATED_DIR, boxed_name)

    img = cv2.imread(image_path)
    if img is None:
        logger.warning("Could not read image for annotation: %s", image_path)
        return None

    for d in detections:
        x1, y1, x2, y2 = (int(c) for c in d["bbox"])
        cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 255), 2)
        label = f"{d['class']} {d['confidence']:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
        cv2.rectangle(img, (x1, y1 - th - 8), (x1 + tw + 4, y1), (0, 255, 255), -1)
        cv2.putText(img, label, (x1 + 2, y1 - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)

    cv2.imwrite(boxed_path, img)
    logger.debug("Saved annotated image to: %s", boxed_path)
    return boxed_name


def predict(image_path):
    """
    Run inference on an image and return predictions.

    Returns:
        tuple: (primary_class, confidence, all_detections)
    """
    result = _run_model(image_path)
    logger.debug("Raw detections found: %d", len(result.boxes))
    all_detections = _extract_detections(result)

    if not all_detections:
        logger.debug("No detections kept after filtering")
        return "No Waste Detected", 0.0, []

    primary = all_detections[0]
    logger.info("Primary detection: %s (%.2f%%), total=%d",
                primary["class"], primary["confidence"] * 100, len(all_detections))
    return primary["class"], primary["confidence"], all_detections


def get_class_name(class_id):
    """Get class name from class ID (prefers loaded model names)."""
    return _current_class_names().get(int(class_id), f"Unknown-{class_id}")


def run_inference(image_path):
    """
    Run inference on an image and save annotated version with bounding boxes
    (only filtered/kept detections are drawn).

    Returns:
        tuple: (all_detections, boxed_filename)
    """
    result = _run_model(image_path)
    logger.debug("Raw detections found: %d", len(result.boxes))
    all_detections = _extract_detections(result)
    logger.info("Total detections kept: %d", len(all_detections))

    boxed_name = _save_annotated(image_path, all_detections)
    return all_detections, boxed_name


def get_model_info():
    """Get information about the loaded model."""
    global model
    if model is None:
        return {"status": "not_loaded", "model_path": MODEL_PATH}
    names = _current_class_names()
    return {
        "status": "loaded",
        "model_path": MODEL_PATH,
        "confidence_threshold": CONFIDENCE_THRESHOLD,
        "per_class_thresholds": dict(PER_CLASS_CONF),
        "iou_threshold": IOU_THRESHOLD,
        "min_box_area_frac": MIN_BOX_AREA_FRAC,
        "num_classes": len(names),
        "classes": names,
    }
