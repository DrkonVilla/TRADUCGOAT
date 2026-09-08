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

import time
import urllib.request
import urllib.parse
import json

def translate_with_free_google(text: str, target_lang: str) -> str:
    """
    Traductor automático de respaldo (fallback) usando deep_translator (Google + MyMemory).
    Agrupa el texto en bloques para evitar sobrecargar los servidores y prevenir errores HTTP 429.
    """
    if not text or not text.strip():
        return text

    lang_map = {
        "español": "es", "spanish": "es", "es": "es",
        "inglés": "en", "english": "en", "en": "en",
        "francés": "fr", "french": "fr", "fr": "fr",
        "alemán": "de", "german": "de", "de": "de",
        "italiano": "it", "italian": "it", "it": "it",
        "portugués": "pt", "portuguese": "pt", "pt": "pt",
        "chino": "zh-CN", "chinese": "zh-CN",
        "japonés": "ja", "japanese": "ja"
    }
    
    tl = lang_map.get(target_lang.lower(), "es")
    
    # Dividir líneas y agruparlas en bloques de ~1800 caracteres para hacer muy pocas solicitudes HTTP
    lines = text.split("\n")
    blocks = []
    current_block = []
    current_len = 0

    for line in lines:
        if current_len + len(line) + 1 > 1800 and current_block:
            blocks.append("\n".join(current_block))
            current_block = [line]
            current_len = len(line)
        else:
            current_block.append(line)
            current_len += len(line) + 1
            
    if current_block:
        blocks.append("\n".join(current_block))

    # Intento 1: GoogleTranslator de deep_translator
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source="auto", target=tl)
        translated_blocks = []
        for b in blocks:
            if not b.strip():
                translated_blocks.append(b)
                continue
            try:
                trans = translator.translate(b)
                translated_blocks.append(trans if trans else b)
            except Exception as e:
                print(f"[ERROR deep_translator Google]: {e}")
                # Intentar respaldo por línea con URL directa
                translated_blocks.append(b)
            time.sleep(0.15)
        return "\n".join(translated_blocks)
    except Exception as e:
        print(f"[ERROR Inicialización GoogleTranslator]: {e}")

    # Intento 2: MyMemoryTranslator de respaldo
    try:
        from deep_translator import MyMemoryTranslator
        mymemory_lang = "es-ES" if tl == "es" else tl
        translator = MyMemoryTranslator(source="auto", target=mymemory_lang)
        translated_blocks = []
        for b in blocks:
            if not b.strip():
                translated_blocks.append(b)
                continue
            try:
                trans = translator.translate(b)
                translated_blocks.append(trans if trans else b)
            except Exception:
                translated_blocks.append(b)
            time.sleep(0.2)
        return "\n".join(translated_blocks)
    except Exception:
        pass

    # Intento 3: HTTP directo a API pública de Google Translate
    translated_blocks = []
    for b in blocks:
        if not b.strip():
            translated_blocks.append(b)
            continue
        try:
            url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl={tl}&dt=t&q=" + urllib.parse.quote(b)
            req = urllib.request.Request(
                url, 
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res = json.loads(response.read().decode('utf-8'))
                sentences = [item[0] for item in res[0] if item and item[0]]
                translated_blocks.append(''.join(sentences))
        except Exception:
            translated_blocks.append(b)
        time.sleep(0.2)

    return "\n".join(translated_blocks)

def translate_chunk_with_gemini(chunk: str, target_lang: str, source_lang: str = "auto") -> str:
    """
    Traduce un fragmento de texto usando Google Gemini vía google.genai o langchain-google-genai.
    Si la clave no es válida o hay un fallo de API, utiliza la traducción de respaldo automática.
    """
    api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
    
    # Si la clave no está configurada o tiene un formato no válido (ej. AQ...), ir directo a fallback
    if not api_key or api_key.startswith("AQ.") or "YOUR_API_KEY" in api_key:
        print(f"[INFO]: Clave Gemini ausente o no válida. Usando motor de traducción automático de respaldo...")
        return translate_with_free_google(chunk, target_lang)

    prompt_template = f"""Eres un traductor científico profesional de altísima precisión. Traduce el siguiente texto académico al idioma '{target_lang}'.

REGLAS CRÍTICAS E INVIOLABLES:
1. Conserva TODAS las citas bibliográficas y referencias exactamente en su formato original (ejemplo: (Apellido, 2020), (Author et al., 2021), [1], [2, 3], etc.). NO traduzcas nombres de autores, años ni números de referencia.
2. Mantén la terminología técnica apropiada para artículos de investigación.
3. Devuelve ÚNICAMENTE el texto traducido, sin preámbulos, saludos ni notas adicionales.

Texto a traducir:
{chunk}"""

    # Intento 1: google.genai Client (Recomendado oficial para Gemini)
    models_to_try = [settings.GEMINI_MODEL, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
        for m in models_to_try:
            try:
                res = client.models.generate_content(model=m, contents=prompt_template)
                if res and res.text:
                    return res.text.strip()
            except Exception as e:
                print(f"[ERROR Gemini SDK - modelo {m}]: {e}")
                continue
    except Exception as e:
        print(f"[ERROR Inicialización google.genai Client]: {e}")

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
            except Exception as e:
                print(f"[ERROR LangChain Gemini - modelo {m}]: {e}")
                continue
    except Exception as e:
        print(f"[ERROR Inicialización LangChain ChatGoogleGenerativeAI]: {e}")

    # Fallback automático si ninguna llamada remota a Gemini tuvo éxito
    print(f"[INFO]: Activando motor de traducción de respaldo...")
    return translate_with_free_google(chunk, target_lang)

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
