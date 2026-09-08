from backend.agents.state import TranslationState
from backend.tools.formatting_tools import fix_formatting, validate_translation

def reviewer_node(state: TranslationState) -> TranslationState:
    """
    Nodo del Agente Revisor y Ensamblador de Calidad.
    Examina la traducción, corrige formato y decide si aprueba o solicita re-intento.
    """
    logs = list(state.get("logs", []))
    texto_original = state.get("texto_original", "")
    texto_traducido = state.get("texto_traducido", "")
    intento = state.get("intento_revision", 0) + 1

    logs.append(f"🔎 [Agente Revisor]: Inspeccionando calidad y formato (Intento {intento})...")

    # Corregir formato
    texto_corregido = fix_formatting(texto_traducido)

    # Validar
    val = validate_translation(texto_original, texto_corregido)
    warnings = val.get("warnings", [])

    logs.append(f"📊 [Agente Revisor]: Citas detectadas en original: {val.get('citas_originales')}, en traducción: {val.get('citas_traducidas')}.")

    for w in warnings:
        logs.append(f"⚠️ [Agente Revisor]: Advertencia: {w}")

    # Criterio de aprobación: es válido o ha alcanzado el límite de intentos (recursividad controlada)
    revision_aprobada = val.get("is_valid", True) or intento >= 2

    if revision_aprobada:
        logs.append(f"✨ [Agente Revisor]: Traducción APROBADA y ensamblada correctamente.")
    else:
        logs.append(f"🔄 [Agente Revisor]: Calidad insuficiente. Solicitando re-intento de traducción...")

    return {
        **state,
        "texto_traducido": texto_corregido,
        "revision_aprobada": revision_aprobada,
        "intento_revision": intento,
        "warnings": warnings,
        "logs": logs
    }
