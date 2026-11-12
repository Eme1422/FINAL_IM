import streamlit as st
from datetime import date
import random

# Configuración de la página
st.set_page_config(
    page_title="MARGEN - Asistente de Lectura Multimodal",
    page_icon="📚",
    layout="wide"
)

# -------------------------------------------------------------------------
# INICIALIZACIÓN DE ESTADOS (MEMORIA DE LA APLICACIÓN)
# -------------------------------------------------------------------------
if "books" not in st.session_state:
    # Lista inicial de libros con sus datos
    st.session_state.books = {
        "Cien años de soledad": {"total_pages": 400, "current_page": 120, "rating": 5, "review": "Una obra maestra absoluta."},
        "El Principito": {"total_pages": 90, "current_page": 90, "rating": 4, "review": "Muy reflexivo y corto."},
        "1984": {"total_pages": 328, "current_page": 150, "rating": 4, "review": "Distopía fascinante."}
    }

if "reading_sessions" not in st.session_state:
    st.session_state.reading_sessions = ["2026-05-10", "2026-05-11", "2026-05-13"]

if "vocab_list" not in st.session_state:
    st.session_state.vocab_list = ["fascinante", "resiliencia", "epifanía", "nostalgia", "introspección"]

if "feedback_log" not in st.session_state:
    st.session_state.feedback_log = []

# -------------------------------------------------------------------------
# MENÚ DE NAVEGACIÓN LATERAL
# -------------------------------------------------------------------------
st.sidebar.title("📚 MARGEN (Panel Principal)")
menu = st.sidebar.radio(
    "Navegación:",
    ["🏠 Inicio y Presentación", "🌌 1. Biblioteca y Sesión de Lectura", "🛋️ 2. Diario, Valoraciones y Análisis"]
)

# -------------------------------------------------------------------------
# MÓDULO 1: INICIO Y PRESENTACIÓN
# -------------------------------------------------------------------------
if menu == "🏠 Inicio y Presentación":
    st.title("📚 MARGEN: Tu Compañero Inteligente de Lectura")
    st.markdown("""
    **MARGEN** es un sistema interactivo enfocado en potenciar la experiencia literaria mediante 
    interfaces multimodales. Esta plataforma fusiona el control ambiental, el seguimiento de hábitos de lectura, 
    la gestión de páginas y el procesamiento de lenguaje natural (NLP).
    """)
    
    st.info("👈 Utiliza el menú lateral izquierdo para explorar los módulos interactivos de la aplicación.")

    st.subheader("💡 Características Principales")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📖 Gestión de Libros y Sesiones")
        st.write("Selecciona tu lectura actual, controla en tiempo real el número de páginas recorridas y registra tu tiempo de lectura diario con calendario de hábitos.")
    with col2:
        st.markdown("### 🧠 Análisis Cognitivo y Sensorial")
        st.write("Incorpora sonidos ambientales relajantes, genera dinámicamente tu nube de vocabulario y evalúa el sentimiento y estadísticas de tus reflexiones.")

# -------------------------------------------------------------------------
# MÓDULO 2: UNIVERSO Y CONTROL AMBIENTAL (Sesión, Páginas, Sonidos)
# -------------------------------------------------------------------------
elif menu == "🌌 1. Biblioteca y Sesión de Lectura":
    st.title("🌌 Selección de Libro y Sesión Activa")
    st.markdown("Elige el libro que vas a leer hoy, configura tus páginas y ambienta tu espacio con sonidos no invasivos.")

    # 1. Zona para seleccionar el libro de la lista o agregar uno nuevo
    st.subheader("📚 Tus Libros Actuales")
    book_names = list(st.session_state.books.keys())
    selected_book = st.selectbox("Elige un libro para iniciar tu sesión:", book_names)

    # Mostrar información del libro seleccionado
    if selected_book:
        book_info = st.session_state.books[selected_book]
        
        col_info_1, col_info_2 = st.columns(2)
        with col_info_1:
            st.markdown(f"**Título:** {selected_book}")
            st.markdown(f"**Páginas totales:** {book_info['total_pages']}")
            st.session_state.books[selected_book]["current_page"] = st.number_input(
                "Página en la que vas actualmente:", 
                min_value=0, 
                max_value=book_info["total_pages"], 
                value=book_info["current_page"]
            )
        
        with col_info_2:
            # Cálculo del progreso
            curr = st.session_state.books[selected_book]["current_page"]
            tot = book_info["total_pages"]
            prog_pct = int((curr / tot) * 100) if tot > 0 else 0
            st.metric("Progreso del libro", f"{prog_pct}%")
            st.progress(prog_pct / 100, text=f"Vas en la página {curr} de {tot}")

    st.divider()

    # 2. Control de sesión y preguntas de cierre obligatorias (sentimientos y comentarios)
    st.subheader("⏱️ Control del Tiempo de Lectura")
    
    # Simulamos el inicio/final de sesión
    session_active = st.checkbox("🟢 Activar modo de sesión de lectura en curso")
    
    if session_active:
        st.info("📖 Sesión en curso... Lee con calma y disfruta tu libro.")
        
        # Sonido ambiental opcional durante la sesión
        st.markdown("#### 🎧 Sonidos Ambientales No Invasivos")
        sound_choice = st.radio(
            "Elige un sonido de fondo:",
            ["Silencio", "🔥 Fogata Suave", "🌧️ Lluvia en Ventana", "🌲 Brisa de Bosque"],
            horizontal=True
        )

        if sound_choice == "🔥 Fogata Suave":
            st.audio("https://actions.google.com/sounds/v1/ambiences/campfire.ogg")
        elif sound_choice == "🌧️ Lluvia en Ventana":
            st.audio("https://actions.google.com/sounds/v1/weather/rain_heavy.ogg")
        elif sound_choice == "🌲 Brisa de Bosque":
            st.audio("https://actions.google.com/sounds/v1/ambiences/forest_birds.ogg")
            
    else:
        # Al finalizar la sesión, preguntamos obligatoriamente cómo se sintió y comentarios
        st.markdown("### 📝 Cierre de Sesión (Evaluación de Experiencia)")
        st.write("Has finalizado o pausado tu tiempo de lectura. Cuéntanos tu experiencia:")
        
        closing_mood = st.selectbox(
            "¿Cómo te sentiste durante esta sesión de lectura?",
            ["😊 Muy inspirado y enfocado", "😐 Tranquilo y neutral", "🥱 Cansado o
