from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
import logging
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

load_dotenv()

try:
    from .firebase_client import get_db, is_configured
except Exception:
    from firebase_client import get_db, is_configured

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg"}
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "10"))


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_UPLOAD_MB * 1024 * 1024
    CORS(app)

    @app.before_request
    def _log_request():
        logger.info(f"{request.method} {request.path}")

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": f"File too large. Limit is {MAX_UPLOAD_MB} MB"}), 413

    @app.get("/health")
    def health():
        return {"status": "ok"}, 200

    @app.get("/uploads/<path:filename>")
    def get_uploaded_file(filename: str):
        return send_from_directory(UPLOAD_DIR, filename, as_attachment=False)

    @app.get("/reports")
    def list_reports():
        db = get_db()
        if db is None or not is_configured():
            return jsonify({"reports": []}), 200
        try:
            ref = db.reference("reports")
            data = ref.get() or {}
            reports = list(data.values())
            return jsonify({"reports": reports}), 200
        except Exception as err:
            logger.warning(f"Failed to fetch reports: {err}")
            return jsonify({"reports": []}), 200

    @app.post("/predict")
    def predict():
        if "image" not in request.files:
            return jsonify({"error": "No image file provided as 'image'"}), 400

        image_file = request.files["image"]
        if image_file.filename == "":
            return jsonify({"error": "Empty filename"}), 400

        filename = secure_filename(image_file.filename)
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        if ext and ext not in ALLOWED_EXTENSIONS:
            return jsonify({"error": f"Unsupported file type: {ext}"}), 400

        report_id = str(uuid.uuid4())
        saved_filename = f"{report_id}.{ext or 'jpg'}"
        save_path = os.path.join(UPLOAD_DIR, saved_filename)
        image_file.save(save_path)

        lat = request.form.get("lat")
        lng = request.form.get("lng")

        try:
            latitude = float(lat) if lat is not None else None
            longitude = float(lng) if lng is not None else None
        except ValueError:
            return jsonify({"error": "Invalid coordinates"}), 400

        detections = []
        predicted_labels = ["unsorted_waste"] if os.path.getsize(save_path) > 0 else []

        record = {
            "id": report_id,
            "image_filename": saved_filename,
            "latitude": latitude,
            "longitude": longitude,
            "detections": detections,
            "labels": predicted_labels,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        db = get_db()
        if db is not None and is_configured():
            try:
                ref = db.reference("reports")
                ref.child(report_id).set(record)
            except Exception as firebase_err:
                logger.warning(f"Failed to write to Firebase: {firebase_err}")

        image_url = f"/uploads/{saved_filename}"
        return jsonify({
            "success": True,
            "id": report_id,
            "labels": predicted_labels,
            "image": saved_filename,
            "image_url": image_url,
            "latitude": latitude,
            "longitude": longitude,
        }), 200

    return app


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app = create_app()
    app.run(host="0.0.0.0", port=port, debug=True)
