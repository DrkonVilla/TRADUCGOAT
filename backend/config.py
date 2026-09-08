import os
from pathlib import Path
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# Cargar variables de entorno desde el archivo .env
load_dotenv(override=True)

# Directorio raíz del backend
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
UPLOAD_DIR = ROOT_DIR / "temp_uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "TRADUGOAT - Traductor Científico Multi-Agente"
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite:///{ROOT_DIR / 'tradugoat.db'}")
    UPLOAD_DIR: Path = UPLOAD_DIR

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
