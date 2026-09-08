from backend.agents.state import TranslationState
from backend.tools.translation_tools import chunk_text, translate_chunk_with_gemini

def translator_node(state: TranslationState) -> TranslationState:
    """
    Nodo del Agente Traductor Contextual de Precisión.
    Divide el texto en chunks y los traduce secuencialmente con Gemini.
    """
    logs = list(state.get("logs", []))
    texto_original = state.get("texto_original", "")
    idioma_destino = state.get("idioma_destino", "Español")
    idioma_origen = state.get("idioma_origen", "auto")

    if not texto_original or state.get("error"):
        return state

    logs.append(f"🤖 [Agente Traductor]: Iniciando fragmentación del texto para traducción al {idioma_destino}...")

    chunks = chunk_text(texto_original, max_chunk_chars=2500)
    logs.append(f"🧩 [Agente Traductor]: Texto dividido en {len(chunks)} fragmento(s). Traduciendo en paralelo con Gemini...")

    from concurrent.futures import ThreadPoolExecutor

    def translate_single(item):
        idx, chunk = item
        try:
            trans = translate_chunk_with_gemini(chunk, target_lang=idioma_destino, source_lang=idioma_origen)
            return idx, trans, None
        except Exception as e:
            return idx, f"[Error en traducción de fragmento {idx+1}: {str(e)}]\n{chunk}", str(e)

    translated_chunks = [None] * len(chunks)
    
    # Procesar fragmentos con hilos concurrentes para multiplicar la velocidad por 4x
    max_workers = min(5, len(chunks))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(translate_single, (i, chunk)) for i, chunk in enumerate(chunks)]
        for future in futures:
            idx, result_text, err = future.result()
            translated_chunks[idx] = result_text
            if err:
                logs.append(f"⚠️ [Agente Traductor]: Error en chunk {idx+1}/{len(chunks)}: {err}")
            else:
                logs.append(f"⚡ [Agente Traductor]: Chunk {idx+1}/{len(chunks)} traducido con éxito con Gemini.")

    texto_traducido = "\n\n".join(translated_chunks)
    logs.append(f"✅ [Agente Traductor]: Traducción de los {len(chunks)} fragmentos finalizada.")

    return {
        **state,
        "chunks": chunks,
        "texto_traducido": texto_traducido,
        "logs": logs
    }
