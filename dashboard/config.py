import os
from dotenv import load_dotenv
from pathlib import Path

_dir = Path(__file__).resolve().parent
_project_root = _dir.parent.parent.parent

# Load dashboard-local .env first, then fall back to LibreChat project root
load_dotenv(_dir / ".env", override=False)
load_dotenv(_project_root / ".env")

MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017/LibreChat")
DB_NAME = os.getenv("DASHBOARD_DB_NAME") or MONGO_URI.rsplit("/", 1)[-1]

DASHBOARD_PASSWORD = os.getenv("DASHBOARD_PASSWORD", "admin123")
JWT_SECRET = os.getenv("DASHBOARD_JWT_SECRET", DASHBOARD_PASSWORD + "-jwt-secret")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

HOST = os.getenv("DASHBOARD_HOST", "0.0.0.0")
PORT = int(os.getenv("DASHBOARD_PORT", "8088"))
