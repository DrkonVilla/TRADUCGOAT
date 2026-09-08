import json
import time
from backend.database import SessionLocal
from backend.models import Batch, Archivo
from backend.agents.orchestrator import orchestrator_pipeline

def process_batch_background(batch_id: str):
    """
    Función ejecutada en segundo plano por FastAPI BackgroundTasks.
    Recorre los archivos asignados al batch_id y ejecuta la orquestación de LangGraph con streaming de estado.
    """
    db = SessionLocal()
    try:
        batch = db.query(Batch).filter(Batch.id == batch_id).first()
        if not batch:
            return

        batch.estado = "EN_PROGRESO"
        db.commit()

        archivos = db.query(Archivo).filter(Archivo.batch_id == batch_id).all()
        all_success = True

        for archivo in archivos:
            archivo.estado = "PROCESANDO"
            archivo.logs_agente = json.dumps([
                "🚀 [Sistema]: Iniciando pipeline de agentes...",
                f"🔍 [Agente Extractor]: Leyendo y analizando estructura de '{archivo.nombre_original}'..."
            ])
            db.commit()

            start_time = time.time()
            
            # Estado inicial de LangGraph
            initial_state = {
                "file_path": archivo.nombre_traducido or "", # Ruta local temporal
                "texto_original": "",
                "idioma_origen": batch.idioma_origen,
                "idioma_destino": batch.idioma_destino,
                "chunks": [],
                "texto_traducido": "",
                "revision_aprobada": False,
                "intento_revision": 0,
                "logs": ["🚀 [Sistema]: Iniciando pipeline de agentes..."],
                "warnings": [],
                "error": None
            }

            try:
                final_state = initial_state
                
                # Ejecutar con streaming de nodos para guardar logs en vivo en la base de datos
                for output in orchestrator_pipeline.stream(initial_state):
                    for node_name, node_state in output.items():
                        final_state = node_state
                        current_logs = node_state.get("logs", [])
                        archivo.logs_agente = json.dumps(current_logs)
                        db.commit()
                
                elapsed = round(time.time() - start_time, 2)
                
                if final_state.get("error"):
                    archivo.estado = "FALLIDO"
                    archivo.logs_agente = json.dumps(final_state.get("logs", []))
                    all_success = False
                else:
                    archivo.estado = "COMPLETADO"
                    archivo.texto_original = final_state.get("texto_original", "")
                    archivo.texto_traducido = final_state.get("texto_traducido", "")
                    archivo.tiempo_procesamiento = elapsed
                    archivo.num_caracteres = len(final_state.get("texto_traducido", ""))
                    archivo.logs_agente = json.dumps(final_state.get("logs", []))

            except Exception as e:
                elapsed = round(time.time() - start_time, 2)
                archivo.estado = "FALLIDO"
                archivo.tiempo_procesamiento = elapsed
                logs = json.loads(archivo.logs_agente or "[]")
                logs.append(f"❌ [Error Fatal]: Excepción no controlada: {str(e)}")
                archivo.logs_agente = json.dumps(logs)
                all_success = False

            db.commit()

        batch.estado = "COMPLETADO" if all_success else "COMPLETADO_CON_ERRORES"
        db.commit()

    except Exception as e:
        print(f"Error procesando batch {batch_id}: {e}")
    finally:
        db.close()

def inspect_file_lines(file_path: str, start_line: int = 1, end_line: int = 200, search_query: str = ""):
    """Extrae el contenido por líneas (indexadas desde 1) y permite búsqueda (grep_search style)."""
    from backend.tools.file_tools import extract_file_content
    full_text = extract_file_content(file_path)
    lines = full_text.splitlines()
    total_lines = len(lines)

    search_matches = []
    if search_query.strip():
        q = search_query.lower()
        for idx, line in enumerate(lines, 1):
            if q in line.lower():
                search_matches.append({
                    "line_number": idx,
                    "content": line.strip()
                })

    start_idx = max(1, start_line)
    end_idx = min(total_lines, max(start_idx, end_line))

    slice_lines = []
    for idx in range(start_idx, end_idx + 1):
        slice_lines.append({
            "line_number": idx,
            "content": lines[idx - 1]
        })

    return {
        "total_lines": total_lines,
        "start_line": start_idx,
        "end_line": end_idx,
        "lines": slice_lines,
        "search_matches": search_matches[:50]
    }

def process_file_range_background(file_id: str, start_line: int, end_line: int):
    """Procesa y traduce únicamente un rango focalizado de líneas de un archivo (replace_file_content / view_file style)."""
    db = SessionLocal()
    try:
        archivo = db.query(Archivo).filter(Archivo.id == file_id).first()
        if not archivo:
            return
        batch = archivo.batch

        file_path = archivo.nombre_traducido
        from backend.tools.file_tools import extract_file_content
        full_text = extract_file_content(file_path)
        lines = full_text.splitlines()

        start_idx = max(1, start_line)
        end_idx = min(len(lines), max(start_idx, end_line))
        target_lines = lines[start_idx - 1:end_idx]
        target_text = "\n".join(target_lines)

        archivo.estado = "PROCESANDO"
        archivo.logs_agente = json.dumps([
            "🚀 [Sistema]: Iniciando pipeline de agentes para rango focalizado...",
            f"🎯 [Rango de Selección]: Líneas {start_idx} a {end_idx} ({len(target_text)} caracteres)"
        ])
        db.commit()

        start_time = time.time()
        initial_state = {
            "file_path": file_path,
            "texto_original": target_text,
            "idioma_origen": batch.idioma_origen,
            "idioma_destino": batch.idioma_destino,
            "chunks": [],
            "texto_traducido": "",
            "revision_aprobada": False,
            "intento_revision": 0,
            "logs": [
                "🚀 [Sistema]: Iniciando pipeline de agentes...",
                f"🎯 [Rango de Selección]: Líneas {start_idx} a {end_idx} ({len(target_text)} caracteres)"
            ],
            "warnings": [],
            "error": None
        }

        final_state = initial_state
        for output in orchestrator_pipeline.stream(initial_state):
            for node_name, node_state in output.items():
                final_state = node_state
                current_logs = node_state.get("logs", [])
                archivo.logs_agente = json.dumps(current_logs)
                db.commit()

        elapsed = round(time.time() - start_time, 2)
        if final_state.get("error"):
            archivo.estado = "FALLIDO"
            archivo.logs_agente = json.dumps(final_state.get("logs", []))
        else:
            archivo.estado = "COMPLETADO"
            archivo.texto_original = target_text
            archivo.texto_traducido = final_state.get("texto_traducido", "")
            archivo.tiempo_procesamiento = elapsed
            archivo.num_caracteres = len(final_state.get("texto_traducido", ""))
            archivo.logs_agente = json.dumps(final_state.get("logs", []))

        db.commit()
    except Exception as e:
        print(f"Error procesando rango {file_id}: {e}")
    finally:
        db.close()
