import io
import zipfile
from typing import List, Tuple

def create_zip_from_files(file_tuples: List[Tuple[str, str]]) -> bytes:
    """
    Recibe una lista de tuplas (nombre_archivo, contenido_texto)
    y genera un buffer de bytes conteniendo un archivo .zip.
    """
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename, content in file_tuples:
            zip_file.writestr(filename, content.encode("utf-8"))
    zip_buffer.seek(0)
    return zip_buffer.getvalue()
