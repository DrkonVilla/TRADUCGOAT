import os
from pathlib import Path

def read_txt(file_path: str) -> str:
    """Lee el contenido de un archivo .txt probando codificaciones UTF-8 y Latin-1."""
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except UnicodeDecodeError:
        with open(file_path, "r", encoding="latin-1") as f:
            return f.read()

def read_pdf(file_path: str) -> str:
    """Extrae el texto de un archivo PDF usando pdfplumber con respaldo en pypdf."""
    text_content = []
    
    # Intento 1: pdfplumber (mejor para preservar estructura y párrafos)
    try:
        import pdfplumber
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_content.append(page_text)
        if text_content:
            return "\n\n".join(text_content)
    except Exception:
        pass

    # Intento 2: pypdf (respaldo rápido)
    try:
        from pypdf import PdfReader
        reader = PdfReader(file_path)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text_content.append(page_text)
        return "\n\n".join(text_content)
    except Exception as e:
        raise ValueError(f"Error al leer el PDF: {str(e)}")

def read_docx(file_path: str) -> str:
    """Extrae el texto de un archivo DOCX usando python-docx."""
    try:
        import docx
        doc = docx.Document(file_path)
        full_text = [paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()]
        return "\n\n".join(full_text)
    except Exception as e:
        raise ValueError(f"Error al leer el archivo DOCX: {str(e)}")

def extract_file_content(file_path: str) -> str:
    """Detecta la extensión del archivo y llama al extractor correspondiente."""
    ext = Path(file_path).suffix.lower()
    if ext == ".txt":
        return read_txt(file_path)
    elif ext == ".pdf":
        return read_pdf(file_path)
    elif ext == ".docx":
        return read_docx(file_path)
    else:
        raise ValueError(f"Formato de archivo no soportado: {ext}")

def detect_language(text: str) -> str:
    """Detecta el idioma del texto usando langdetect o fallback simple."""
    if not text or len(text.strip()) < 10:
        return "Desconocido"
    try:
        from langdetect import detect
        code = detect(text[:2000])
        mapping = {
            "en": "Inglés",
            "es": "Español",
            "fr": "Francés",
            "de": "Alemán",
            "it": "Italiano",
            "pt": "Portugués",
            "zh": "Chino",
            "ja": "Japonés"
        }
        return mapping.get(code, code.upper())
    except Exception:
        return "Inglés"  # Fallback habitual para artículos científicos
