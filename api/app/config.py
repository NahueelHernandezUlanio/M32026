import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./planta.db")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
