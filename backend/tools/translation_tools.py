import os
from backend.config import settings

def chunk_text(text: str, max_chunk_chars: int = 2500) -> list[str]:
    """
    Divide el texto en fragmentos (chunks) respetando los párrafos (\n\n)
    para no cortar oraciones a la mitad.
    """
    if not text:
        return []
    
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = []
    current_len = 0

    for p in paragraphs:
        p_clean = p.strip()
        if not p_clean:
            continue
        p_len = len(p_clean)
        
        if current_len + p_len + 2 > max_chunk_chars and current_chunk:
            chunks.append("\n\n".join(current_chunk))
            current_chunk = [p_clean]
            current_len = p_len
        else:
            current_chunk.append(p_clean)
            current_len += p_len + 2
            
    if current_chunk:
        chunks.append("\n\n".join(current_chunk))
        
    return chunks if chunks else [text]

def translate_chunk_with_gemini(chunk: str, target_lang: str, source_lang: str = "auto") -> str:
    """
    Traduce un fragmento de texto usando Google Gemini vía google.genai o langchain-google-genai.
    """
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    
    prompt_template = f"""Eres un traductor científico profesional de altísima precisión. Traduce el siguiente texto académico al idioma '{target_lang}'.

REGLAS CRÍTICAS E INVIOLABLES:
1. Conserva TODAS las citas bibliográficas y referencias exactamente en su formato original (ejemplo: (Apellido, 2020), (Author et al., 2021), [1], [2, 3], etc.). NO traduzcas nombres de autores, años ni números de referencia.
2. Mantén la terminología técnica apropiada para artículos de investigación.
3. Devuelve ÚNICAMENTE el texto traducido, sin preámbulos, saludos ni notas adicionales.

Texto a traducir:
{chunk}"""

    if not api_key:
        # Modo simulación / fallback si no hay clave de API configurada
        return f"[Simulación de traducción al {target_lang}]\n{chunk}"

    # Intento 1: google.genai Client (Recomendado oficial para Gemini)
    models_to_try = [settings.GEMINI_MODEL, "gemini-3.5-flash", "gemini-flash-latest", "gemini-3.1-flash-lite"]
    
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        for m in models_to_try:
            try:
                res = client.models.generate_content(model=m, contents=prompt_template)
                if res and res.text:
                    return res.text.strip()
            except Exception:
                continue
    except Exception:
        pass

    # Intento 2: LangChain ChatGoogleGenerativeAI
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        for m in models_to_try:
            try:
                llm = ChatGoogleGenerativeAI(
                    model=m,
                    google_api_key=api_key,
                    temperature=0.2
                )
                response = llm.invoke(prompt_template)
                if response and response.content:
                    return response.content.strip()
            except Exception:
                continue
    except Exception:
        pass

    # Fallback si ninguna llamada remota respondió
    return f"[Traducción con Fallback al {target_lang}]\n{chunk}"

def translate_text_pipeline(text: str, target_lang: str, source_lang: str = "auto", log_callback=None) -> str:
    """
    Orquesta la división en chunks y traducción secuencial de todo el texto.
    """
    chunks = chunk_text(text)
    if log_callback:
        log_callback(f"Dividiendo el texto en {len(chunks)} fragmento(s) para procesamiento.")
        
    translated_chunks = []
    for i, chunk in enumerate(chunks, 1):
        if log_callback:
            log_callback(f"Traduciendo fragmento {i}/{len(chunks)} con Gemini...")
        trans = translate_chunk_with_gemini(chunk, target_lang, source_lang)
        translated_chunks.append(trans)
        
    return "\n\n".join(translated_chunks)
