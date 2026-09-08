import os
import sys
from pathlib import Path

# Garantizar que el directorio raíz del proyecto esté en sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import time
import requests
import pandas as pd
import streamlit as st
from backend.utils.citation_utils import highlight_citations_html, extract_citations

# Configuración de página Streamlit
st.set_page_config(
    page_title="TRADUGOAT - Traductor Científico Multi-Agente",
    page_icon="🐐",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para una estética moderna y profesional
st.markdown("""
<style>
    /* Estilos globales */
    .main-header {
        font-family: 'Inter', sans-serif;
        background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
        padding: 24px;
        border-radius: 12px;
        color: #f8fafc;
        margin-bottom: 24px;
        border: 1px solid #334155;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }
    .main-header h1 {
        color: #38bdf8;
        font-size: 2.2rem;
        margin: 0;
        font-weight: 700;
    }
    .main-header p {
        color: #94a3b8;
        font-size: 1.05rem;
        margin-top: 6px;
        margin-bottom: 0;
    }
    
    /* Target de estado de los agentes */
    .agent-card {
        background-color: #1e293b;
        border-radius: 8px;
        padding: 14px;
        margin-bottom: 12px;
        border-left: 4px solid #3b82f6;
    }
    .agent-log {
        font-family: 'Courier New', Courier, monospace;
        background-color: #0f172a;
        color: #38bdf8;
        padding: 10px;
        border-radius: 6px;
        font-size: 0.88rem;
        max-height: 180px;
        overflow-y: auto;
    }

    /* Caja de vista comparativa de texto */
    .text-box {
        background-color: #ffffff;
        color: #1e293b;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 18px;
        font-size: 0.95rem;
        line-height: 1.6;
        min-height: 400px;
        max-height: 600px;
        overflow-y: auto;
        white-space: pre-wrap;
        box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.05);
    }

    /* Badge de métricas */
    .metric-badge {
        display: inline-block;
        background: #e0f2fe;
        color: #0369a1;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 600;
        margin-right: 8px;
    }
</style>
""", unsafe_allow_html=True)

# Dirección del Backend API
BACKEND_URL = "http://localhost:8000"

def check_backend_health():
    try:
        res = requests.get(f"{BACKEND_URL}/", timeout=3)
        return res.status_code == 200
    except Exception:
        return False

# --- BARRA LATERAL DE CONFIGURACIÓN ---
with st.sidebar:
    st.image("https://img.icons8.com/isometric/96/translation.png", width=64)
    st.title("⚙️ Configuración")
    
    backend_online = check_backend_health()
    if backend_online:
        st.success("🟢 Backend FastAPI: Conectado")
    else:
        st.error("🔴 Backend FastAPI: Desconectado")
        st.caption("Asegúrate de ejecutar: `uvicorn backend.main:app --port 8000`")

    st.markdown("---")
    st.subheader("🌐 Parámetros de Traducción")
    
    idioma_origen = st.selectbox(
        "Idioma de Origen:",
        options=["auto", "Inglés", "Español", "Francés", "Alemán", "Italiano", "Portugués", "Chino"],
        index=0,
        help="Selecciona 'auto' para autodetección de idioma mediante el Agente Extractor."
    )

    idioma_destino = st.selectbox(
        "Idioma de Destino:",
        options=["Español", "Inglés", "Francés", "Alemán", "Italiano", "Portugués", "Chino"],
        index=0,
        help="Idioma al cual se traducirán los documentos."
    )

    st.markdown("---")
    st.info("💡 **Sistema Multi-Agente con LangGraph**\n- **Extractor**: Analiza estructura e idioma\n- **Traductor**: Gemini contextual sin alterar citas\n- **Revisor**: Control de formato y calidad")

# --- ENCABEZADO PRINCIPAL ---
st.markdown("""
<div class="main-header">
    <h1>TRADUGOAT 🐐</h1>
    <p>Sistema Multi-Agente Inteligente para Traducción de Artículos Científicos con Resaltado de Citas Bibliográficas</p>
</div>
""", unsafe_allow_html=True)

# Inicializar Estado de Sesión en Streamlit
if "current_batch_id" not in st.session_state:
    st.session_state.current_batch_id = None
if "batch_completed" not in st.session_state:
    st.session_state.batch_completed = False

# Creación de Pestañas
tab_upload, tab_inspector, tab_preview, tab_history = st.tabs([
    "📥 Carga y Procesamiento en Lote",
    "🎯 Selección por Rangos y Búsqueda",
    "🔍 Previsualización Comparativa y Citas",
    "📜 Historial de Lotes"
])

# --- PESTAÑA 1: CARGA Y PROCESAMIENTO EN LOTE ---
with tab_upload:
    st.subheader("1. Selección y Carga de Archivos")
    uploaded_files = st.file_uploader(
        "Arrastra y suelta o selecciona tus artículos científicos (.pdf, .docx, .txt)",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True
    )

    if uploaded_files:
        st.write(f"📁 **{len(uploaded_files)} archivo(s) seleccionado(s):**")
        for f in uploaded_files:
            st.caption(f"- {f.name} ({round(f.size / 1024, 1)} KB)")

        if st.button("🚀 Iniciar Traducción del Lote Completo", type="primary", use_container_width=True):
            if not backend_online:
                st.error("No se puede iniciar el proceso porque el Backend no responde.")
            else:
                files_payload = [("files", (f.name, f.getvalue(), f.type)) for f in uploaded_files]
                data_payload = {
                    "idioma_origen": idioma_origen,
                    "idioma_destino": idioma_destino
                }
                
                with st.spinner("Creando lote y subiendo archivos al servidor..."):
                    try:
                        res = requests.post(f"{BACKEND_URL}/api/upload", files=files_payload, data=data_payload)
                        if res.status_code == 200:
                            batch_data = res.json()
                            batch_id = batch_data["batch_id"]
                            st.session_state.current_batch_id = batch_id
                            st.session_state.batch_completed = False
                            
                            # Disparar traducción
                            res_trans = requests.post(f"{BACKEND_URL}/api/translate/{batch_id}")
                            if res_trans.status_code == 200:
                                st.success(f"¡Lote creado exitosamente! ID: `{batch_id}`")
                            else:
                                st.error("Error iniciando la traducción en el servidor.")
                        else:
                            st.error(f"Error en la carga: {res.text}")
                    except Exception as e:
                        st.error(f"Error de conexión al cargar: {str(e)}")

    # Monitoreo en vivo si existe un lote activo
    if st.session_state.current_batch_id:
        st.markdown("---")
        st.subheader("2. Monitoreo en Tiempo Real del Pipeline de Agentes")
        
        batch_id = st.session_state.current_batch_id
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        # Placeholder único para evitar la duplicación iterativa de elementos visuales
        logs_placeholder = st.empty()

        # Bucle de Monitoreo Polling
        while True:
            try:
                res = requests.get(f"{BACKEND_URL}/api/status/{batch_id}")
                if res.status_code == 200:
                    data = res.json()
                    progreso = data.get("progreso_porcentaje", 0)
                    estado_batch = data.get("estado", "")
                    
                    progress_bar.progress(progreso / 100)
                    status_text.markdown(f"**Estado General del Lote:** `{estado_batch}` ({progreso}%)")

                    # Limpiar el placeholder antes de renderizar para evitar la duplicación de elementos
                    logs_placeholder.empty()
                    with logs_placeholder.container():
                        st.markdown("### Estado Individual y Logs de los Agentes:")
                        for file_info in data.get("archivos", []):
                            icon = "⏳" if file_info["estado"] == "PENDIENTE" else ("🔄" if file_info["estado"] == "PROCESANDO" else ("✅" if file_info["estado"] == "COMPLETADO" else "❌"))
                            
                            with st.expander(f"{icon} **{file_info['nombre_original']}** - Estado: `{file_info['estado']}`", expanded=True):
                                logs = file_info.get("logs", [])
                                if logs:
                                    st.markdown(f"<div class='agent-log'>{'<br>'.join(logs)}</div>", unsafe_allow_html=True)
                                else:
                                    st.caption("En espera de los agentes...")

                    if estado_batch in ["COMPLETADO", "COMPLETADO_CON_ERRORES", "FALLIDO"]:
                        st.session_state.batch_completed = True
                        if estado_batch == "COMPLETADO":
                            st.balloons()
                            st.success("🎉 ¡Todos los documentos del lote han sido traducidos exitosamente!")
                        break
                time.sleep(3)
            except Exception as e:
                st.warning(f"Esperando respuesta del servidor... ({str(e)})")
                break

# --- PESTAÑA 2: SELECCIÓN POR RANGOS Y BÚSQUEDA ---
with tab_inspector:
    st.subheader("🎯 Inspección y Traducción Focalizada por Rangos de Líneas")
    st.markdown("""
    *Esta herramienta te permite buscar palabras clave (estilo `grep_search`), indexar el documento por líneas (estilo `view_file`) 
    y traducir únicamente el fragmento o sección que desees sin necesidad de procesar todo el artículo.*
    """)
    
    current_batch = st.session_state.current_batch_id
    if not current_batch:
        st.info("Carga un archivo en la pestaña 1 o selecciona un lote del Historial para inspeccionar sus documentos.")
    else:
        try:
            res = requests.get(f"{BACKEND_URL}/api/status/{current_batch}")
            if res.status_code == 200:
                archivos = res.json().get("archivos", [])
                if not archivos:
                    st.warning("No hay archivos disponibles en este lote.")
                else:
                    file_map = {f["nombre_original"]: f["id"] for f in archivos}
                    selected_name = st.selectbox("Selecciona un documento para inspeccionar:", options=list(file_map.keys()))
                    selected_file_id = file_map[selected_name]
                    
                    st.markdown("---")
                    col_search, col_range = st.columns([1, 1])
                    
                    with col_search:
                        st.markdown("### 🔍 2. Búsqueda Focalizada (`grep_search`)")
                        query = st.text_input("Buscar término o sección (ej. Abstract, Methodology, Conclusion):")
                        
                    # Inspección preliminar
                    insp_res = requests.get(f"{BACKEND_URL}/api/inspect/{selected_file_id}?start_line=1&end_line=200&search_query={query}")
                    if insp_res.status_code == 200:
                        insp_data = insp_res.json()
                        total_lines = insp_data.get("total_lines", 0)
                        matches = insp_data.get("search_matches", [])
                        
                        if query and matches:
                            st.success(f"Se encontraron {len(matches)} coincidencia(s) en las líneas:")
                            for m in matches[:10]:
                                st.caption(f"📍 **Línea {m['line_number']}**: `{m['content'][:90]}...`")
                        elif query:
                            st.warning("No se encontraron coincidencias para la búsqueda.")
                            
                        with col_range:
                            st.markdown("### 📄 1. Lectura por Rangos (`view_file`)")
                            st.info(f"Total de Líneas en Documento: `{total_lines}` líneas")
                            col_l1, col_l2 = st.columns(2)
                            start_l = col_l1.number_input("Línea Inicio (StartLine):", min_value=1, max_value=max(1, total_lines), value=1)
                            end_l = col_l2.number_input("Línea Fin (EndLine):", min_value=int(start_l), max_value=max(int(start_l), total_lines), value=min(total_lines, int(start_l) + 100))

                        # Re-inspeccionar con el rango de líneas seleccionado
                        insp_range_res = requests.get(f"{BACKEND_URL}/api/inspect/{selected_file_id}?start_line={start_l}&end_line={end_l}")
                        if insp_range_res.status_code == 200:
                            range_lines = insp_range_res.json().get("lines", [])
                            preview_text = "\n".join([f"{l['line_number']}: {l['content']}" for l in range_lines])
                            
                            st.markdown(f"### 🎯 3. Coincidencia Exacta y Vista Previa del Bloque ({len(range_lines)} líneas / {len(preview_text)} caracteres)")
                            st.text_area("Texto objetivo seleccionado para traducir:", value=preview_text, height=220, disabled=True)
                            
                            if st.button(f"🚀 Traducir Únicamente Líneas {start_l} a {end_l}", type="primary", use_container_width=True):
                                range_payload = {"start_line": int(start_l), "end_line": int(end_l)}
                                t_res = requests.post(f"{BACKEND_URL}/api/translate-range/{selected_file_id}", json=range_payload)
                                if t_res.status_code == 200:
                                    st.success(f"¡Traducción iniciada para el rango de líneas {start_l} a {end_l}! Revisa el progreso en la pestaña 1.")
                                else:
                                    st.error("Error al iniciar la traducción del rango.")
        except Exception as e:
            st.error(f"Error cargando inspector de líneas: {str(e)}")

# --- PESTAÑA 2: PREVISUALIZACIÓN COMPARATIVA Y CITAS ---
with tab_preview:
    st.subheader("Previsualización Comparativa Lado a Lado")
    
    batch_id_to_view = st.session_state.current_batch_id
    
    if not batch_id_to_view:
        st.info("No hay ningún lote seleccionado. Procesa un nuevo lote o selecciona uno del Historial.")
    else:
        try:
            res = requests.get(f"{BACKEND_URL}/api/status/{batch_id_to_view}")
            if res.status_code == 200:
                batch_data = res.json()
                archivos = batch_data.get("archivos", [])
                
                # Filtro por archivo
                file_options = {f["nombre_original"]: f for f in archivos if f["estado"] == "COMPLETADO"}
                
                if not file_options:
                    st.warning("Aún no hay archivos completados en este lote para previsualizar.")
                else:
                    selected_filename = st.selectbox("Selecciona un documento para comparar:", options=list(file_options.keys()))
                    selected_file = file_options[selected_filename]

                    orig_text = selected_file.get("texto_original", "")
                    trans_text = selected_file.get("texto_traducido", "")

                    # Resaltado de citas
                    highlighted_trans, num_citas = highlight_citations_html(trans_text)

                    # Métricas de archivo
                    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
                    col_m1.metric("Tiempo de Procesamiento", f"{selected_file.get('tiempo_procesamiento', 0)} seg")
                    col_m2.metric("Total Caracteres Traducidos", f"{selected_file.get('num_caracteres', 0)}")
                    col_m3.metric("Citas Bibliográficas Resaltadas", f"{num_citas}")
                    with col_m4:
                        st.markdown("<div style='margin-top:28px;'></div>", unsafe_allow_html=True)
                        st.link_button("📦 Descargar Lote Completo (.ZIP)", f"{BACKEND_URL}/api/download-all/{batch_id_to_view}", type="primary", use_container_width=True)

                    st.markdown("---")
                    col_left, col_right = st.columns(2)

                    with col_left:
                        st.markdown("### 📄 Texto Original")
                        st.markdown(f"<div class='text-box'>{orig_text if orig_text else 'Texto no disponible'}</div>", unsafe_allow_html=True)
                    with col_right:
                        st.markdown("### 🌐 Texto Traducido (Citas en Azul)")
                        st.markdown(f"<div class='text-box'>{highlighted_trans if highlighted_trans else 'Traducción no disponible'}</div>", unsafe_allow_html=True)

                    st.markdown("---")
                    st.download_button(
                        label=f"📥 Descargar '{selected_filename}' Traducido (.txt)",
                        data=trans_text.encode("utf-8"),
                        file_name=f"{selected_filename.rsplit('.', 1)[0]}_traducido.txt",
                        mime="text/plain",
                        type="primary"
                    )

                    if selected_filename.lower().endswith('.pdf'):
                        st.markdown("---")
                        st.markdown("### 📄 Vista del PDF Original")
                        pdf_url = f"{BACKEND_URL}/api/file/{selected_file['id']}"
                        try:
                            import base64
                            pdf_res = requests.get(pdf_url)
                            if pdf_res.status_code == 200:
                                base64_pdf = base64.b64encode(pdf_res.content).decode('utf-8')
                                pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="800px" type="application/pdf" style="border: 1px solid #e2e8f0; border-radius: 8px;"></iframe>'
                                st.markdown(pdf_display, unsafe_allow_html=True)
                            else:
                                st.error("No se pudo cargar el PDF para previsualizar.")
                        except Exception as e:
                            st.error(f"Error cargando PDF: {str(e)}")

        except Exception as e:
            st.error(f"Error obteniendo previsualización: {str(e)}")

# --- PESTAÑA 3: HISTORIAL DE LOTES ---
with tab_history:
    st.subheader("Historial de Traducciones Realizadas")
    if st.button("🔄 Actualizar Historial"):
        st.rerun()

    try:
        res = requests.get(f"{BACKEND_URL}/api/history")
        if res.status_code == 200:
            history_data = res.json()
            if not history_data:
                st.info("No se han registrado lotes de traducción previos en la base de datos.")
            else:
                df = pd.DataFrame(history_data)
                df.columns = ["ID Lote", "Fecha de Creación", "Origen", "Destino", "Estado", "Total Archivos"]
                st.dataframe(df, use_container_width=True)

                st.markdown("### Cargar un Lote del Historial:")
                selected_batch_id = st.selectbox("Selecciona ID de Lote:", options=[b["id"] for b in history_data])
                if st.button("👁️ Ver Lote Seleccionado"):
                    st.session_state.current_batch_id = selected_batch_id
                    st.success(f"Lote `{selected_batch_id}` cargado. Revisa la pestaña 'Previsualización Comparativa y Citas'.")
        else:
            st.error("Error obteniendo el historial desde el servidor.")
    except Exception as e:
        st.error(f"Error conectando al servicio de historial: {str(e)}")
