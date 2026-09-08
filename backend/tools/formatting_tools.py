import re
from backend.utils.citation_utils import extract_citations

def fix_formatting(text: str) -> str:
    """Normaliza saltos de línea y espacios en blanco del texto traducido."""
    if not text:
        return ""
    # Reemplazar múltiples saltos de línea continuos por máximo 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Eliminar espacios sobrantes al final de cada línea
    lines = [line.rstrip() for line in text.split('\n')]
    return '\n'.join(lines).strip()

def validate_translation(original_text: str, translated_text: str) -> dict:
    """
    Valida la calidad de la traducción:
    - Verifica que el texto traducido no esté vacío.
    - Compara el número de citas originales y traducidas.
    - Retorna dict con estado de validación y lista de advertencias.
    """
    warnings = []
    is_valid = True

    if not translated_text or len(translated_text.strip()) == 0:
        return {"is_valid": False, "warnings": ["La traducción devuelta está vacía."]}

    # Comprobación de longitud
    orig_len = len(original_text.strip())
    trans_len = len(translated_text.strip())
    
    if orig_len > 100 and trans_len < (orig_len * 0.3):
        warnings.append("El texto traducido es significativamente más corto que el original.")
        is_valid = False

    # Comprobación de preservación de citas
    orig_citations = extract_citations(original_text)
    trans_citations = extract_citations(translated_text)

    if len(orig_citations) > 0 and len(trans_citations) == 0:
        warnings.append(f"Se detectaron {len(orig_citations)} citas en el original pero ninguna en la traducción.")

    return {
        "is_valid": is_valid,
        "warnings": warnings,
        "citas_originales": len(orig_citations),
        "citas_traducidas": len(trans_citations)
    }
