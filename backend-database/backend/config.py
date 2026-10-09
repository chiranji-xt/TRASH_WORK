import os
import urllib.parse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Database Configuration (no hardcoded secrets) ---
# All values must come from the environment / .env file.
# See backend-database/.env.example for required keys.
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "garbage_detection_db")

if not DB_PASSWORD:
    raise RuntimeError(
        "DB_PASSWORD is not set. Copy backend-database/.env.example to "
        "backend-database/.env and set a strong password. "
        "The previously committed dev password has been revoked — do not reuse it."
    )

# Encode password for URL
password = urllib.parse.quote_plus(DB_PASSWORD)
DATABASE_URL = f"postgresql://{DB_USER}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# --- Uploads directories ---
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "uploads"))

# Annotated images directory (for YOLO boxed images)
ANNOTATED_DIR = os.path.join(UPLOAD_DIR, "annotated")

# Create directories if they don't exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(ANNOTATED_DIR, exist_ok=True)

# --- ML Model ---
# No hardcoded absolute path. Point MODEL_PATH at your weights file.
# e.g. MODEL_PATH=./backend/ml/best.pt
_default_model = os.path.join(os.path.dirname(__file__), "ml", "best.pt")
MODEL_PATH = os.getenv("MODEL_PATH", _default_model)

# Single tunable confidence threshold (was 0.25 in one backend, 0.1 in another).
# Pick via the PR curve; override with CONFIDENCE_THRESHOLD env var.
# Used as the global default; PER_CLASS_CONF below can override per class.
try:
    CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.25"))
except ValueError:
    CONFIDENCE_THRESHOLD = 0.25

# Per-class confidence thresholds (JSON), tuned from validation curves.
# Plastic gets a high bar (42% of background was predicted as plastic);
# Metal/Glass/Styrofoam are reliable so they keep low bars to preserve recall.
# Keys must match model.names exactly, e.g.:
#   PER_CLASS_CONF={"Plastic Waste": 0.45, "Cardboard_Paper": 0.25}
import json as _json

_PER_CLASS_DEFAULTS = {
    "Cardboard_Paper": 0.25,
    "Glass Waste": 0.20,
    "Metal Waste": 0.15,
    "Plastic Waste": 0.45,
    "Styrofoam": 0.20,
}
try:
    _overrides = _json.loads(os.getenv("PER_CLASS_CONF", "{}") or "{}")
    for _k, _v in dict(_overrides).items():
        _PER_CLASS_DEFAULTS[str(_k)] = float(_v)
except (ValueError, AttributeError):
    pass
PER_CLASS_CONF = _PER_CLASS_DEFAULTS

# NMS IoU threshold (lower = merges overlapping boxes more aggressively;
# fixes double-boxes seen in validation samples). Ultralytics default is 0.7.
try:
    IOU_THRESHOLD = float(os.getenv("IOU_THRESHOLD", "0.5"))
except ValueError:
    IOU_THRESHOLD = 0.5

# Minimum box area as a fraction of image area — kills tiny noise boxes
# (a common background-false-positive source). 0.0008 ≈ 25x25px on 640x640.
try:
    MIN_BOX_AREA_FRAC = float(os.getenv("MIN_BOX_AREA_FRAC", "0.0008"))
except ValueError:
    MIN_BOX_AREA_FRAC = 0.0008

# Max upload size in MB (validated in app.py)
try:
    MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "10"))
except ValueError:
    MAX_UPLOAD_MB = 10

# --- CORS ---
# Comma-separated list of allowed dashboard origins.
# e.g. ALLOWED_ORIGINS=http://localhost:5173,https://my-dashboard.example.com
# Falls back to FRONTEND_ORIGIN for backwards compatibility.
_raw_origins = os.getenv("ALLOWED_ORIGINS") or os.getenv("FRONTEND_ORIGIN", "http://localhost:5173")
ALLOWED_ORIGINS = [o.strip().rstrip("/") for o in _raw_origins.split(",") if o.strip()]

# --- Admin auth ---
# Simple API key protecting PATCH /reports/{id}/status and other admin endpoints.
# Set ADMIN_API_KEY in .env and send it as `X-API-Key` header from the dashboard.
# If unset, admin endpoints return 503 with a clear message (fail closed is
# handled in app.py via get_admin_key dependency).
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
