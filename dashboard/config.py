import os
from dotenv import load_dotenv
from pathlib import Path

_dir = Path(__file__).resolve().parent

# Load dashboard-local .env only
load_dotenv(_dir / ".env")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/LibreChat")
DB_NAME = os.getenv("DASHBOARD_DB_NAME") or MONGO_URI.rsplit("/", 1)[-1]

DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin123")
JWT_SECRET = os.getenv("DASHBOARD_JWT_SECRET", DASHBOARD_PASSWORD + "-jwt-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
PORT = int(os.getenv("DASHBOARD_PORT", "8088"))

# S3 / R2 / MinIO storage configuration
AWS_REGION = os.getenv("AWS_REGION", "")
AWS_BUCKET_NAME = os.getenv("AWS_BUCKET_NAME", "")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_ENDPOINT_URL = os.getenv("AWS_ENDPOINT_URL", "")
AWS_FORCE_PATH_STYLE = os.getenv("AWS_FORCE_PATH_STYLE", "").lower() in ("true", "1", "yes")
