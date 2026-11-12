import streamlit as st
from datetime import date
import random
from textblob import TextBlob
from googletrans import Translator

# Configuración de la página
st.set_page_config(
    page_title="MARGEN - Asistente de Lectura Multimodal",
    page_icon="📚",
    layout="wide"
)

# Inicializar el traductor para el análisis de texto de la Clase 8
translator = Translator()

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
    la gestión de páginas y el procesamiento de lenguaje natural (NLP) aprendido en la Clase 8.
    """)
    
    st.info("👈 Utiliza el menú lateral izquierdo para explorar los módulos interactivos de la aplicación.")

    st.subheader("💡 Características Principales")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📖 Gestión de Libros y Sesiones")
        st.write("Selecciona tu lectura actual, agrega nuevos libros, controla el número de páginas recorridas y registra tu tiempo de lectura diario con calendario de hábitos.")
    with col2:
        st.markdown("### 🧠 Análisis Cognitivo y Sensorial")
        st.write("Incorpora sonidos ambientales relajantes, genera tu nube de vocabulario y evalúa el sentimiento de tus reflexiones con TextBlob y traducción automática.")

# -------------------------------------------------------------------------
# MÓDULO 2: BIBLIOTECA Y SESIÓN DE LECTURA (Página 1)
# -------------------------------------------------------------------------
elif menu == "🌌 1. Biblioteca y Sesión de Lectura":
    st.title("🌌 Biblioteca y Sesión de Lectura Activa")
    st.markdown("Elige tu libro actual o agrega uno nuevo, configura tus páginas, ambienta tu espacio y registra tu sesión.")

    # Selector de libros con opción de agregar uno nuevo
    book_options = list(st.session_state.books.keys()) + ["➕ Agregar nuevo libro"]
    selected_option = st.selectbox("Selecciona un libro o agrega uno:", book_options)

    if selected_option == "➕ Agregar nuevo libro":
        st.subheader("📖 Registrar Nuevo Libro")
        new_title = st.text_input("Título del nuevo libro:")
        new_total_pages = st.number_input("Número total de páginas:", min_value=1, value=200)
        
        if st.button("Guardar y añadir a la biblioteca"):
            if new_title and new_title not in st.session_state.books:
                st.session_state.books[new_title] = {
                    "total_pages": new_total_pages,
                    "current_page": 0,
                    "rating": 3,
                    "review": "Libro recién añadido."
                }
                st.success(f"¡Libro '{new_title}' agregado con éxito! Vuelve a seleccionarlo arriba.")
                st.rerun()
            else:
                st.warning("El libro ya existe o el título está vacío.")
    else:
        selected_book = selected_option
        book_info = st.session_state.books[selected_book]
        
        col_info_1, col_info_2 = st.columns(2)
        with col_info_1:
            st.markdown(f"**📖 Libro seleccionado:** `{selected_book}`")
            st.markdown(f"**Páginas totales:** {book_info['total_pages']}")
            
            # Actualizar página actual del libro
            current_p = st.number_input(
                "¿En qué página vas actualmente?", 
                min_value=0, 
                max_value=book_info["total_pages"], 
                value=book_info["current_page"]
            )
            st.session_state.books[selected_book]["current_page"] = current_p
        
        with col_info_2:
            tot = book_info["total_pages"]
            prog_pct = int((current_p / tot) * 100) if tot > 0 else 0
            st.metric("Progreso del libro", f"{prog_pct}%")
            st.progress(prog_pct / 100, text=f"Vas en la página {current_p} de {tot}")

        st.divider()

        # Selector de Sonido Ambiental No Invasivo
        st.subheader("🎧 Ambiente Sonoro No Invasivo")
        sound_choice = st.radio(
            "Elige un sonido de fondo para tu lectura:",
            ["Silencio", "🔥 Fogata Nocturna", "🌧️ Lluvia Suave", "🌲 Brisa de Bosque"],
            horizontal=True
        )

        if sound_choice == "🔥 Fogata Nocturna":
            st.audio("https://actions.google.com/sounds/v1/ambiences/campfire.ogg")
            st.info("💡 Reproduciendo sonido sutil de fogata.")
        elif sound_choice == "🌧️ Lluvia Suave":
            st.audio("https://actions.google.com/sounds/v1/weather/rain_heavy.ogg")
            st.info("💡 Reproduciendo sonido de lluvia relajante.")
        elif sound_choice == "🌲 Brisa de Bosque":
            st.audio("https://actions.google.com/sounds/v1/ambiences/forest_birds.ogg")
            st.info("💡 Reproduciendo sonido natural del bosque.")

        st.divider()

        # Control de Sesión y Cierre de Sesión con TextBlob (Clase 8)
        st.subheader("⏱️ Temporizador y Control de Sesión")
        session_active = st.checkbox("🟢 Activar sesión de lectura en curso (Cronómetro activo)")

        if session_active:
            st.info("📖 Sesión en curso... El tiempo está corriendo. Disfruta tu lectura y actualiza tu página cuando termines.")
        else:
            st.markdown("### 📝 Cierre de Sesión (Evaluación con Análisis de Sentimiento)")
            st.write("Al finalizar tu tiempo de lectura, cuéntanos cómo te sentiste y deja tus comentarios:")
            
            closing_comment = st.text_area("¿Qué tal la lectura de hoy? Escribe tus reflexiones o notas:")
            
            if st.button("Finalizar sesión y analizar texto"):
                if closing_comment:
                    try:
                        translation = translator.translate(closing_comment, src="es", dest="en")
                        trans_text = translation.text
                        blob = TextBlob(trans_text)
                        
                        polarity = round(blob.sentiment.polarity, 2)
                        subjectivity = round(blob.sentiment.subjectivity, 2)
                        
                        st.write(f"**Polarity:** {polarity} | **Subjectivity:** {subjectivity}")
                        
                        if polarity > 0.0 and polarity <= 1.0:
                            sentimiento_str = "Positivo 😊"
                            st.success("Es un sentimiento Positivo 😊")
                        elif polarity >= -1 and polarity < 0:
                            sentimiento_str = "Negativo 😔"
                            st.error("Es un sentimiento Negativo 😔")
                        else:
                            sentimiento_str = "Neutral 😐"
                            st.info("Es un sentimiento Neutral 😐")
                            
                        today_str = str(date.today())
                        if today_str not in st.session_state.reading_sessions:
                            st.session_state.reading_sessions.append(today_str)
                            
                        st.session_state.feedback_log.append({
                            "libro": selected_book,
                            "fecha": today_str,
                            "comentario": closing_comment,
                            "sentimiento": sentimiento_str,
                            "polaridad": polarity
                        })
                        st.success("¡Sesión finalizada, guardada y analizada correctamente!")
                    except Exception as e:
                        st.error(f"Error al procesar el análisis de texto: {e}")
                else:
                    st.warning("Por favor escribe un comentario antes de finalizar la sesión.")

# -------------------------------------------------------------------------
# MÓDULO 3: DIARIO, VALORACIONES Y ANÁLISIS (Página 2)
# -------------------------------------------------------------------------
elif menu == "🛋️ 2. Diario, Valoraciones y Análisis":
    st.title("🛋️ Diario de Lectura, Valoraciones y Analítica")
    st.markdown("Consulta toda la información guardada de tus libros, calificaciones con estrellas, sesiones registradas y analítica completa.")

    tab_diario, tab_vocab, tab_sentim = st.tabs(["📖 Diario, Libros y Sesiones", "☁️ Nube de Vocabulario", "📊 Analizador de Sentimientos (Clase 8)"])

    # TAB 1: Diario completo con libros, sesiones guardadas, progreso y estrellas (1 a 5)
    with tab_diario:
        st.subheader("📚 Resumen y Analítica de Todos los Libros")
        
        if not st.session_state.books:
            st.info("No hay libros registrados.")
        else:
            for book_title, data in st.session_state.books.items():
                with st.expander(f"📖 {book_title} — Progreso: {data['current_page']}/{data['total_pages']} pág"):
                    new_rating = st.slider(
                        f"Calificación (Estrellas 1-5) para {book_title}:", 
                        min_value=1, 
                        max_value=5, 
                        value=data["rating"], 
                        key=f"star_{book_title}"
                    )
                    st.session_state.books[book_title]["rating"] = new_rating
                    st.write(f"**Puntuación:** {'⭐' * new_rating} ({new_rating}/5)")

                    new_review = st.text_area(
                        f"Comentarios y Reseña de {book_title}:", 
                        value=data["review"], 
                        key=f"rev_{book_title}"
                    )
                    st.session_state.books[book_title]["review"] = new_review

                    st.markdown("#### 🕒 Historial de Sesiones Guardadas:")
                    libro_sessions = [s for s in st.session_state.feedback_log if s["libro"] == book_title]
                    if libro_sessions:
                        for idx, s in enumerate(libro_sessions, 1):
                            st.write(f"{idx}. **Fecha:** {s['fecha']} | **Sentimiento:** {s['sentimiento']} (Polaridad: {s['polaridad']}) | *\"{s['comentario']}\"*")
                    else:
                        st.write("Aún no hay sesiones cerradas registradas para este libro específico.")

        st.markdown("---")
        st.subheader("📅 Calendario de Hábitos (Días de Lectura)")
        st.write("Fechas en las que se registró actividad:", st.session_state.reading_sessions)
        st.metric("Total de días leídos", len(st.session_state.reading_sessions))

    # TAB 2: Nube de Vocabulario
    with tab_vocab:
        st.subheader("Generador Visual de Vocabulario")
        st.write("Agrega palabras nuevas para construir tu nube visual de aprendizaje:")
        
        new_word = st.text_input("Añadir nueva palabra al vocabulario:")
        if st.button("Agregar palabra"):
            if new_word and new_word.strip() not in st.session_state.vocab_list:
                st.session_state.vocab_list.append(new_word.strip())
                st.success(f"Palabra '{new_word}' agregada con éxito.")
        
        st.markdown("#### Términos Registrados:")
        st.write(", ".join([f"`{w}`" for w in st.session_state.vocab_list]))
        
        cloud_html = " ".join([f"<span style='font-size: {random.randint(18, 32)}px; margin: 10px; color: #2E7D32; font-weight: bold;'>{w}</span>" for w in st.session_state.vocab_list])
        st.markdown(f"<div style='padding: 25px; background-color: #E8F5E9; border-radius: 12px; text-align: center;'>{cloud_html}</div>", unsafe_allow_html=True)

    # TAB 3: Analizador de Sentimientos basado en la Clase 8
    with tab_sentim:
        st.title('Análisis de Sentimiento (Clase 8)')
        st.subheader("Por favor escribe en el campo de texto la frase que deseas analizar")

        with st.sidebar:
            st.subheader("Polaridad y Subjetividad")
            st.markdown("""
            Polaridad: Indica si el sentimiento expresado en el texto es positivo, negativo o neutral. 
            Su valor oscila entre -1 (muy negativo) y 1 (muy positivo), con 0 representando un sentimiento neutral.
            
            Subjetividad: Mide cuánto del contenido es subjetivo (opiniones, emociones, creencias) frente a objetivo (hechos). Va de 0 a 1, donde 0 es completamente objetivo y 1 es completamente subjetivo.
            """)

        with st.expander('Analizar texto'):
            text = st.text_input('Escribe por favor: ')
            if text:
                translation = translator.translate(text, src="es", dest="en")
                trans_text = translation.text
                blob = TextBlob(trans_text)
                st.write('Polarity: ', round(blob.sentiment.polarity, 2))
                st.write('Subjectivity: ', round(blob.sentiment.subjectivity, 2))
                x = round(blob.sentiment.polarity, 2)
                if x > 0.0 and x <= 1.0:
                    st.write('Es un sentimiento Positivo 😊')
                elif x >= -1 and x <= 0:
                    st.write('Es un sentimiento Negativo 😔')
                else:
                    st.write('Es un sentimiento Neutral 😐')
