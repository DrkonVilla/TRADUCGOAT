from typing import TypedDict, List, Optional

class TranslationState(TypedDict):
    file_path: str
    texto_original: str
    idioma_origen: str
    idioma_destino: str
    chunks: List[str]
    texto_traducido: str
    revision_aprobada: bool
    intento_revision: int
    logs: List[str]
    warnings: List[str]
    error: Optional[str]
