import os
import urllib.parse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Configuration
# Get credentials from environment variables with fallback defaults
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "Edi_G11$01")  # Default for local dev only
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "garbage_detection_db")

# Encode password for URL
password = urllib.parse.quote_plus(DB_PASSWORD)
DATABASE_URL = f"postgresql://{DB_USER}:{password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Uploads directory
UPLOAD_DIR = os.getenv("UPLOAD_DIR", os.path.join(os.path.dirname(__file__), "uploads"))

# Annotated images directory (for YOLO boxed images)
ANNOTATED_DIR = os.path.join(UPLOAD_DIR, "annotated")

# Create directories if they don't exist
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)

if not os.path.exists(ANNOTATED_DIR):
    os.makedirs(ANNOTATED_DIR)

# ML Model path
MODEL_PATH = os.getenv("MODEL_PATH", r"E:\SY\EDI\Smart Garbage Detection\best.pt")
