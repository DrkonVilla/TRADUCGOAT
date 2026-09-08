# TRADUGOAT 🐐 - Sistema Multi-Agente para Traducción y Resaltado de Referencias Científicas

TRADUGOAT es una aplicación web profesional para la traducción de artículos científicos (.pdf, .docx, .txt) por lotes, impulsada por un equipo de agentes autónomos orquestados con **LangGraph** y **LangChain**, potenciados por el motor **Google Gemini** y presentados a través de una interfaz interactiva con **Streamlit** y un servidor backend en **FastAPI**.

---

## 🎯 Características Principales

1. **Gestión Masiva por Lotes**: Carga mediante Drag & Drop de múltiples archivos (.pdf, .docx, .txt).
2. **Orquestación Multi-Agente con LangGraph**:
   - 🔍 **Agente Extractor**: Extrae el texto manteniendo la estructura de párrafos y detecta el idioma de origen.
   - ⚡ **Agente Traductor (Gemini)**: Divide el texto en fragmentos (chunks) y los traduce contextualmente al idioma deseado sin alterar ni traducir citas bibliográficas `(Autor, Año)` o `[1]`.
   - 🔎 **Agente Revisor**: Evalúa la calidad, corrige el formato de saltos de línea y realiza re-intentos si la validación falla.
3. **Resaltado Visual de Referencias**: Muestra las citas bibliográficas con un distintivo visual azul en la vista previa comparativa lado a lado.
4. **Persistencia en Base de Datos**: SQLite + SQLAlchemy registran cada lote, archivo, métricas de procesamiento y logs detallados en tiempo real.
5. **Descargas Masivas e Individuales**: Descarga de traducciones en archivo individual `.txt` o el lote completo comprimido en `.zip`.

---

## 🏗️ Estructura del Proyecto

```text
TRADUGOAT/
├── backend/
│   ├── main.py                 # FastAPI endpoints REST
│   ├── config.py               # Configuración del entorno
│   ├── database.py             # SQLAlchemy Session y Engine
│   ├── models.py               # Modelos ORM (Batch, Archivo)
│   ├── agents/
│   │   ├── state.py            # Estado global (TranslationState)
│   │   ├── extractor_agent.py  # Agente de extracción e idioma
│   │   ├── translator_agent.py # Agente de traducción con Gemini
│   │   ├── reviewer_agent.py   # Agente de revisión y calidad
│   │   └── orchestrator.py     # StateGraph de LangGraph
│   ├── tools/
│   │   ├── file_tools.py       # Lectura de PDF, DOCX, TXT
│   │   ├── translation_tools.py# Chunking y llamada a Gemini
│   │   └── formatting_tools.py # Validación y corrección de formato
│   ├── services/
│   │   ├── file_service.py     # Guardado de archivos subidos
│   │   └── translation_service.py # Procesador de lotes en segundo plano
│   ├── utils/
│   │   ├── zip_utils.py        # Compresión ZIP
│   │   └── citation_utils.py   # Resaltado regex de citas
│   └── requirements.txt
├── frontend/
│   ├── app.py                  # Aplicación Streamlit interactiva
│   └── requirements.txt
├── .env.example
└── README.md
```

---

## ⚙️ Instalación y Configuración

### 1. Requisitos Previos
- Python 3.11 o superior.
- Clave de API de Google Gemini (`GEMINI_API_KEY`).

### 2. Instalación de Dependencias

```bash
# Crear entorno virtual (opcional pero recomendado)
python -m venv venv
# Activar en Windows:
venv\Scripts\activate
# Activar en Linux/macOS:
source venv/bin/activate

# Instalar dependencias del backend y frontend
pip install -r backend/requirements.txt
pip install -r frontend/requirements.txt
```

### 3. Configuración de Variables de Entorno
Copia `.env.example` a `.env` e ingresa tu clave API de Gemini:

```env
GEMINI_API_KEY=tu_api_key_de_gemini_aqui
GEMINI_MODEL=gemini-1.5-flash
DATABASE_URL=sqlite:///./tradugoat.db
```

---

## 🚀 Ejecución del Sistema

### 1. Iniciar el Backend (FastAPI)

En una terminal ejecuta:

```bash
uvicorn backend.main:app --reload --port 8000
```
La documentación interactiva OpenAPI/Swagger estará disponible en `http://localhost:8000/docs`.

### 2. Iniciar el Frontend (Streamlit)

En otra terminal ejecuta:

```bash
streamlit run frontend/app.py
```
La interfaz de usuario se abrirá automáticamente en tu navegador en `http://localhost:8501`.
