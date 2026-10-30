import os
from pathlib import Path

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://planta:planta@localhost:5432/planta")
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "./uploads"))
