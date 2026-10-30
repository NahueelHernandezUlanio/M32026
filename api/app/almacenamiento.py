import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from app.config import UPLOAD_DIR


def guardar_archivo(archivo: UploadFile, carpeta: str) -> str:
    destino = UPLOAD_DIR / carpeta
    destino.mkdir(parents=True, exist_ok=True)
    nombre = f"{uuid4().hex}{Path(archivo.filename or '').suffix.lower()}"
    with (destino / nombre).open("wb") as salida:
        shutil.copyfileobj(archivo.file, salida)
    return f"{carpeta}/{nombre}"
