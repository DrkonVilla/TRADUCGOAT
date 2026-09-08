import sys
from pathlib import Path

# Garantizar que el directorio raíz del proyecto esté en sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import json
from typing import List
from fastapi import FastAPI, Depends, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy.orm import Session

from backend.config import settings
from backend.database import engine, Base, get_db
from backend.models import Batch, Archivo
from backend.services.file_service import save_uploaded_file
from backend.services.translation_service import process_batch_background
from backend.utils.zip_utils import create_zip_from_files

# Inicializar tablas en la BD al cargar
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="API Backend para sistema multi-agente de traducción de artículos científicos con LangChain, LangGraph y Gemini",
    version="1.0.0"
)

# Configuración CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {
        "status": "ok",
        "app": settings.PROJECT_NAME,
        "docs_url": "/docs"
    }

@app.post("/api/upload")
def upload_files(
    files: List[UploadFile] = File(...),
    idioma_origen: str = Form("auto"),
    idioma_destino: str = Form("Español"),
    db: Session = Depends(get_db)
):
    """Carga múltiple de archivos, crea el registro de Batch y guarda los metadatos."""
    if not files:
        raise HTTPException(status_code=400, detail="No se enviaron archivos.")

    valid_extensions = {".pdf", ".docx", ".txt"}
    
    new_batch = Batch(
        idioma_origen=idioma_origen,
        idioma_destino=idioma_destino,
        estado="PENDIENTE"
    )
    db.add(new_batch)
    db.commit()
    db.refresh(new_batch)

    archivos_guardados = []
    for file in files:
        ext = "." + file.filename.split(".")[-1].lower() if "." in file.filename else ""
        if ext not in valid_extensions:
            continue
        
        # Guardar temporalmente en servidor
        saved_path = save_uploaded_file(file)

        nuevo_archivo = Archivo(
            batch_id=new_batch.id,
            nombre_original=file.filename,
            nombre_traducido=saved_path,  # Ruta temporal inicial
            estado="PENDIENTE"
        )
        db.add(nuevo_archivo)
        archivos_guardados.append(file.filename)

    db.commit()

    if not archivos_guardados:
        db.delete(new_batch)
        db.commit()
        raise HTTPException(status_code=400, detail="Ninguno de los archivos enviados tiene un formato válido (.pdf, .docx, .txt).")

    return {
        "batch_id": new_batch.id,
        "archivos_cargados": archivos_guardados,
        "total_archivos": len(archivos_guardados),
        "estado": new_batch.estado
    }

@app.post("/api/translate/{batch_id}")
def start_translation(
    batch_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Dispara el pipeline de traducción en segundo plano usando los agentes de LangGraph."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch no encontrado.")

    background_tasks.add_task(process_batch_background, batch_id)

    return {
        "message": "Traducción iniciada exitosamente en segundo plano.",
        "batch_id": batch_id,
        "estado": "EN_PROGRESO"
    }

@app.get("/api/status/{batch_id}")
def get_batch_status(batch_id: str, db: Session = Depends(get_db)):
    """Obtiene el estado general del lote y el detalle individual con logs en vivo por cada agente."""
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Batch no encontrado.")

    archivos = db.query(Archivo).filter(Archivo.batch_id == batch_id).all()
    
    archivos_detalle = []
    completados = 0
    
    for a in archivos:
        if a.estado in ["COMPLETADO", "FALLIDO"]:
            completados += 1
        
        archivos_detalle.append({
            "id": a.id,
            "nombre_original": a.nombre_original,
            "estado": a.estado,
            "tiempo_procesamiento": a.tiempo_procesamiento,
            "num_caracteres": a.num_caracteres,
            "texto_original": a.texto_original or "",
            "texto_traducido": a.texto_traducido or "",
            "logs": json.loads(a.logs_agente or "[]")
        })

    progreso_porcentaje = int((completados / len(archivos)) * 100) if archivos else 0

    return {
        "batch_id": batch.id,
        "fecha_creacion": batch.fecha_creacion.isoformat(),
        "idioma_origen": batch.idioma_origen,
        "idioma_destino": batch.idioma_destino,
        "estado": batch.estado,
        "progreso_porcentaje": progreso_porcentaje,
        "total_archivos": len(archivos),
        "archivos_completados": completados,
        "archivos": archivos_detalle
    }

@app.get("/api/download/{batch_id}/{file_id}")
def download_single_file(batch_id: str, file_id: str, db: Session = Depends(get_db)):
    """Descarga un archivo traducido individual como .txt."""
    archivo = db.query(Archivo).filter(Archivo.id == file_id, Archivo.batch_id == batch_id).first()
    if not archivo or not archivo.texto_traducido:
        raise HTTPException(status_code=404, detail="Archivo traducido no encontrado o aún en proceso.")

    name_without_ext = archivo.nombre_original.rsplit(".", 1)[0]
    output_filename = f"{name_without_ext}_traducido.txt"

    return Response(
        content=archivo.texto_traducido.encode("utf-8"),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{output_filename}"'}
    )

@app.get("/api/download-all/{batch_id}")
def download_batch_zip(batch_id: str, db: Session = Depends(get_db)):
    """Descarga todo el lote de archivos traducidos comprimidos en un archivo .zip."""
    archivos = db.query(Archivo).filter(Archivo.batch_id == batch_id, Archivo.estado == "COMPLETADO").all()
    if not archivos:
        raise HTTPException(status_code=404, detail="No hay archivos traducidos completados en este lote.")

    file_tuples = []
    for a in archivos:
        name_without_ext = a.nombre_original.rsplit(".", 1)[0]
        output_filename = f"{name_without_ext}_traducido.txt"
        file_tuples.append((output_filename, a.texto_traducido or ""))

    zip_bytes = create_zip_from_files(file_tuples)

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="traducciones_batch_{batch_id[:8]}.zip"'}
    )

@app.get("/api/history")
def get_history(db: Session = Depends(get_db)):
    """Retorna el historial de lotes procesados previamente."""
    batches = db.query(Batch).order_by(Batch.fecha_creacion.desc()).limit(20).all()
    
    result = []
    for b in batches:
        result.append({
            "id": b.id,
            "fecha_creacion": b.fecha_creacion.isoformat(),
            "idioma_origen": b.idioma_origen,
            "idioma_destino": b.idioma_destino,
            "estado": b.estado,
            "total_archivos": len(b.archivos)
        })

    return result

from pydantic import BaseModel

class RangeRequest(BaseModel):
    start_line: int = 1
    end_line: int = 200

@app.get("/api/inspect/{file_id}")
def inspect_file_endpoint(
    file_id: str,
    start_line: int = 1,
    end_line: int = 200,
    search_query: str = "",
    db: Session = Depends(get_db)
):
    """Inspecciona las líneas de un archivo con soporte de búsqueda (estilo view_file / grep_search)."""
    archivo = db.query(Archivo).filter(Archivo.id == file_id).first()
    if not archivo or not archivo.nombre_traducido:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    from backend.services.translation_service import inspect_file_lines
    result = inspect_file_lines(archivo.nombre_traducido, start_line, end_line, search_query)
    result["filename"] = archivo.nombre_original
    result["file_id"] = file_id
    return result

@app.post("/api/translate-range/{file_id}")
def translate_range_endpoint(
    file_id: str,
    req: RangeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """Dispara la traducción de un rango focalizado de líneas en segundo plano."""
    archivo = db.query(Archivo).filter(Archivo.id == file_id).first()
    if not archivo:
        raise HTTPException(status_code=404, detail="Archivo no encontrado.")

    from backend.services.translation_service import process_file_range_background
    background_tasks.add_task(process_file_range_background, file_id, req.start_line, req.end_line)

    return {
        "message": f"Traducción iniciada para líneas {req.start_line} a {req.end_line}.",
        "file_id": file_id,
        "batch_id": archivo.batch_id
    }
