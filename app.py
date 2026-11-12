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

    st.subheader("📚 Tus Libros Actuales")
    book_names = list(st.session_state.books.keys())
    selected_book = st.selectbox("Elige un libro para iniciar tu sesión:", book_names)

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
            curr = st.session_state.books[selected_book]["current_page"]
            tot = book_info["total_pages"]
            prog_pct = int((curr / tot) * 100) if tot > 0 else 0
            st.metric("Progreso del libro", f"{prog_pct}%")
            st.progress(prog_pct / 100, text=f"Vas en la página {curr} de {tot}")

    st.divider()

    st.subheader("⏱️ Control del Tiempo de Lectura")
    session_active = st.checkbox("🟢 Activar modo de sesión de lectura en curso")
    
    if session_active:
        st.info("📖 Sesión en curso... Lee con calma y disfruta tu libro.")
        
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
        st.markdown("### 📝 Cierre de Sesión (Evaluación de Experiencia)")
        st.write("Has finalizado o pausado tu tiempo de lectura. Cuéntanos tu experiencia:")
        
        closing_mood = st.selectbox(
            "¿Cómo te sentiste durante esta sesión de lectura?",
            ["😊 Muy inspirado y enfocado", "😐 Tranquilo y neutral", "🥱 Cansado o distraído", "🤔 Pensativo y reflexivo"]
        )
        closing_comment = st.text_area("Comentario o nota rápida sobre lo que leíste hoy:")
        
        today_str = str(date.today())
        if st.button("Guardar cierre de sesión y registrar día"):
            if today_str not in st.session_state.reading_sessions:
                st.session_state.reading_sessions.append(today_str)
            
            st.session_state.feedback_log.append({
                "libro": selected_book,
                "fecha": today_str,
                "estado_animo": closing_mood,
                "comentario": closing_comment
            })
            st.success("¡Sesión finalizada y registrada correctamente en tu calendario de hábitos!")

# -------------------------------------------------------------------------
# MÓDULO 3: DIARIO, VALORACIONES Y ANÁLISIS COGNITIVO
# -------------------------------------------------------------------------
elif menu == "🛋️ 2. Espacio, Diario y Análisis":
    st.title("🛋️ Mi Diario de Lectura y Análisis Textual")
    st.markdown("Consulta el historial de todos tus libros, califícalos con estrellas, gestiona tu vocabulario y analiza tus textos.")

    # Creación de pestañas para organizar correctamente el contenido
    tab_diario, tab_vocab, tab_sentim = st.tabs(["📖 Diario y Calificaciones", "☁️ Nube de Vocabulario", "📊 Analizador de Sentimientos"])

    with tab_diario:
        st.subheader("Califica y Revisa tus Libros")
        
        if len(st.session_state.books) == 0:
            st.info("No hay libros registrados aún.")
        else:
            for book_title, data in st.session_state.books.items():
                with st.expander(f"📖 {book_title} (Progreso: {data['current_page']}/{data['total_pages']} pág)"):
                    new_rating = st.slider(
                        f"Calificación para {book_title}:", 
                        min_value=1, 
                        max_value=5, 
                        value=data["rating"], 
                        key=f"star_{book_title}"
                    )
                    st.session_state.books[book_title]["rating"] = new_rating
                    
                    stars_str = "⭐" * new_rating
                    st.write(f"**Puntuación:** {stars_str} ({new_rating}/5)")

                    new_review = st.text_area(
                        f"Comentarios / Reseña personal de {book_title}:", 
                        value=data["review"], 
                        key=f"rev_{book_title}"
                    )
                    st.session_state.books[book_title]["review"] = new_review

        st.markdown("---")
        st.subheader("📅 Historial de Días Leídos (Calendario de Hábitos)")
        st.write("Fechas en las que has registrado actividad de lectura:", st.session_state.reading_sessions)
        st.metric("Total de días con hábito de lectura", len(st.session_state.reading_sessions))

    with tab_vocab:
        st.subheader("Generador Visual de Vocabulario")
        st.write("Agrega palabras
