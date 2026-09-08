import os
import uuid
from pathlib import Path
from fastapi import UploadFile
from backend.config import settings

def save_uploaded_file(upload_file: UploadFile) -> str:
    """Guarda un archivo subido en el directorio temporal y retorna su ruta absoluta."""
    ext = Path(upload_file.filename).suffix
    unique_filename = f"{uuid.uuid4().hex}_{upload_file.filename}"
    file_path = settings.UPLOAD_DIR / unique_filename

    with open(file_path, "wb") as buffer:
        buffer.write(upload_file.file.read())

    return str(file_path)
