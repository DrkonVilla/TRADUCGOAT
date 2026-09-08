import re

# Patrones de expresiones regulares para citas bibliográficas científicas
CITATION_PATTERNS = [
    # Citas numéricas entre corchetes: [1], [2, 3], [4-7], [12,15-18]
    r'\[\d+(?:\s*[\,,\-–]\s*\d+)*\]',
    # Citas tipo (Autor et al., Año) o (Autor & Autor, Año) o (Autor, Año)
    r'\((?:[A-Z][a-zA-CÀ-ÿa-z]+(?:\s+et\s+al\.?|\s+\&\s+[A-Z][a-zA-CÀ-ÿa-z]+|\s+and\s+[A-Z][a-zA-CÀ-ÿa-z]+)?\,\s*(?:19|20)\d{2}[a-z]?)\)',
    # Citas tipo [Autor et al., Año]
    r'\[(?:[A-Z][a-zA-CÀ-ÿa-z]+(?:\s+et\s+al\.?|\s+\&\s+[A-Z][a-zA-CÀ-ÿa-z]+|\s+and\s+[A-Z][a-zA-CÀ-ÿa-z]+)?\,\s*(?:19|20)\d{2}[a-z]?)\]',
]

COMPILED_PATTERN = re.compile("|".join(CITATION_PATTERNS))

def extract_citations(text: str) -> list[str]:
    """Extrae todas las citas bibliográficas encontradas en el texto."""
    if not text:
        return []
    return COMPILED_PATTERN.findall(text)

def highlight_citations_html(text: str) -> tuple[str, int]:
    """
    Sustituye las citas bibliográficas encontradas por una etiqueta HTML
    resaltada en tono azul elegante. Retorna el texto modificado y el número de citas.
    """
    if not text:
        return "", 0

    citations = extract_citations(text)
    count = len(citations)

    def replace_match(match):
        citation_text = match.group(0)
        # Estilo HTML moderno y elegante (azul translúcido con borde y negrita)
        return (
            f'<span style="background-color: rgba(37, 99, 235, 0.15); '
            f'color: #1d4ed8; font-weight: 600; padding: 2px 6px; '
            f'border-radius: 4px; border: 1px solid rgba(37, 99, 235, 0.3); '
            f'display: inline-block; margin: 0 1px;" title="Referencia Bibliográfica">{citation_text}</span>'
        )

    highlighted_text = COMPILED_PATTERN.sub(replace_match, text)
    return highlighted_text, count
