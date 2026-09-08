import os
from backend.agents.state import TranslationState
from backend.tools.file_tools import extract_file_content, detect_language

def extractor_node(state: TranslationState) -> TranslationState:
    """
    Nodo del Agente Extractor y Analizador Estructural.
    Herramientas: extract_file_content (read_pdf, read_docx, read_txt) y detect_language.
    """
    logs = list(state.get("logs", []))
    file_path = state.get("file_path", "")
    filename = os.path.basename(file_path)

    logs.append(f"🔍 [Agente Extractor]: Leyendo y analizando estructura de '{filename}'...")

    try:
        texto = state.get("texto_original", "")
        if not texto:
            texto = extract_file_content(file_path)
            
        # Detectar idioma si está en auto
        idioma_origen = state.get("idioma_origen", "auto")
        if not idioma_origen or idioma_origen == "auto":
            idioma_origen = detect_language(texto)
            logs.append(f"🌐 [Agente Extractor]: Idioma detectado automáticamente: {idioma_origen}")
        else:
            logs.append(f"🌐 [Agente Extractor]: Idioma de origen especificado: {idioma_origen}")

        logs.append(f"📄 [Agente Extractor]: Extracción exitosa. {len(texto)} caracteres procesados.")

        return {
            **state,
            "texto_original": texto,
            "idioma_origen": idioma_origen,
            "logs": logs
        }
    except Exception as e:
        error_msg = f"❌ [Agente Extractor]: Error extrayendo archivo: {str(e)}"
        logs.append(error_msg)
        return {
            **state,
            "error": error_msg,
            "logs": logs
        }
