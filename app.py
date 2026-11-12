import streamlit as st
from datetime import datetime, date
import random
import pandas as pd
from textblob import TextBlob
from deep_translator import GoogleTranslator
import os

# Configuración de la página
st.set_page_config(
    page_title="MARGEN - Asistente de Lectura Multimodal",
    page_icon="📚",
    layout="wide"
)

# Inicializar el traductor
translator = GoogleTranslator(source='es', target='en')

# -------------------------------------------------------------------------
# INICIALIZACIÓN DE ESTADOS (MEMORIA DE LA APLICACIÓN)
# -------------------------------------------------------------------------
if "books" not in st.session_state:
    st.session_state.books = {
        "Cien años de soledad": {"total_pages": 400, "current_page": 180, "rating": 5, "review": "Una obra maestra absoluta llena de realismo mágico."},
        "El Principito": {"total_pages": 90, "current_page": 90, "rating": 4, "review": "Muy reflexivo, ideal para todas las edades."},
        "1984": {"total_pages": 328, "current_page": 210, "rating": 5, "review": "Una distopía escalofriante y sumamente vigente."},
        "Crimen y Castigo": {"total_pages": 500, "current_page": 140, "rating": 4, "review": "Profundo análisis psicológico y moral."}
    }

if "reading_sessions" not in st.session_state:
    st.session_state.reading_sessions = ["2026-05-08", "2026-05-10", "2026-05-11", "2026-05-12", "2026-05-13"]

if "time_log" not in st.session_state:
    # Historial de tiempos en minutos por sesión/fecha
    st.session_state.time_log = [
        {"fecha": "2026-05-10", "libro": "Cien años de soledad", "minutos": 45},
        {"fecha": "2026-05-11", "libro": "1984", "minutos": 30},
        {"fecha": "2026-05-12", "libro": "El Principito", "minutos": 20},
        {"fecha": "2026-05-13", "libro": "Crimen y Castigo", "minutos": 60}
    ]

if "start_time" not in st.session_state:
    st.session_state.start_time = None

if "vocab_list" not in st.session_state:
    st.session_state.vocab_list = [
        "fascinante", "resiliencia", "epifanía", "nostalgia", "introspección", 
        "melancolía", "efímero", "serendipia", "paradigma", "inefable", 
        "pragmático", "catarsis", "utopía", "cognitivo", "multimodal", "heurística",
        "impredecible", "asombro", "soledad", "distopía", "imaginación",
        "trascendencia", "esencia", "misterio", "horizonte", "contemplación"
    ]

if "feedback_log" not in st.session_state:
    st.session_state.feedback_log = [
        {"libro": "Cien años de soledad", "fecha": "2026-05-10", "comentario": "Me encantó el capítulo de los gitanos, muy emocionante y mágico.", "sentimiento": "Positivo 😊"},
        {"libro": "1984", "fecha": "2026-05-11", "comentario": "El ambiente del libro se siente muy tenso, oscuro y agobiante.", "sentimiento": "Negativo 😔"},
        {"libro": "El Principito", "fecha": "2026-05-12", "comentario": "Una lectura bastante tranquila y reflexiva sobre la vida.", "sentimiento": "Neutral 😐"},
        {"libro": "Crimen y Castigo", "fecha": "2026-05-13", "comentario": "La culpa del personaje principal es agobiante pero brillante.", "sentimiento": "Positivo 😊"}
    ]

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
    interfaces multimodales. Esta plataforma fusiona el control ambiental con archivos de audio locales, 
    el seguimiento real del tiempo de lectura, hábitos, gestión de páginas y procesamiento de lenguaje natural (NLP).
    """)
    
    st.info("👈 Utiliza el menú lateral izquierdo para explorar los módulos interactivos de la aplicación.")

    st.subheader("💡 Características Principales")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📖 Gestión de Libros y Sesiones")
        st.write("Selecciona tu lectura actual, agrega nuevos libros, controla el número de páginas recorridas y mide el tiempo real de lectura con cronómetro de sistema.")
    with col2:
        st.markdown("### 🧠 Análisis Cognitivo y Sensorial")
        st.write("Reproduce tus audios ambientales locales, genera tu nube de vocaburidad enriquecida, evalúa automáticamente tus reflexiones y consulta gráficas de tus tiempos de lectura.")

# -------------------------------------------------------------------------
# MÓDULO 2: BIBLIOTECA Y SESIÓN DE LECTURA (Página 1)
# -------------------------------------------------------------------------
elif menu == "🌌 1. Biblioteca y Sesión de Lectura":
    st.title("🌌 Biblioteca y Sesión de Lectura Activa")
    st.markdown("Elige tu libro actual o agrega uno nuevo, configura tus páginas, ambienta tu espacio con tus audios y toma el tiempo real de tu sesión.")

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

        # Selector de Sonidos Ambientales Locales
        st.subheader("🎧 Ambiente Sonoro Local No Invasivo")
        sound_choice = st.radio(
            "Elige un sonido ambiental para acompañar tu lectura:",
            ["Silencio", "🔥 Fogata Relajante", "🌧️ Lluvia y Truenos", "💨 Sonido de Viento"],
            horizontal=True
        )

        if sound_choice == "🔥 Fogata Relajante":
            if os.path.exists("Fogata Relajante.mp3"):
                st.audio("Fogata Relajante.mp3")
            else:
                st.warning("No se encontró el archivo local 'Fogata Relajante.mp3' en la carpeta.")
        elif sound_choice == "🌧️ Lluvia y Truenos":
            if os.path.exists("Sonido de Lluvia y Truenos Distantes.mp3"):
                st.audio("Sonido de Lluvia y Truenos Distantes.mp3")
            else:
                st.warning("No se encontró el archivo 'Sonido de Lluvia y Truenos Distantes.mp3'.")
        elif sound_choice == "💨 Sonido de Viento":
            if os.path.exists("Sonido de viento.mp3"):
                st.audio("Sonido de viento.mp3")
            else:
                st.warning("No se encontró el archivo local 'Sonido de viento.mp3' en la carpeta.")

        st.divider()

        # Cronómetro Real basado en system timestamp
        st.subheader("⏱️ Control Real de Tiempo de Sesión")
        
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            if st.button("▶ Iniciar Cronómetro de Lectura", type="primary"):
                st.session_state.start_time = datetime.now()
                st.success(f"¡Cronómetro iniciado a las {st.session_state.start_time.strftime('%H:%M:%S')}!")

        with col_t2:
            if st.session_state.start_time:
                st.info(f"⏳ Sesión en curso iniciada a las {st.session_state.start_time.strftime('%H:%M:%S')}")
            else:
                st.warning("El cronómetro está detenido. Presiona iniciar cuando comiences a leer.")

        st.markdown("---")
        st.markdown("### 📝 Cierre de Sesión y Evaluación")
        closing_comment = st.text_area("¿Qué tal la lectura de hoy? Escribe tus reflexiones o notas:", placeholder="Ej: Me pareció un capítulo excelente...")

        if st.button("⏹ Finalizar Sesión y Guardar Tiempos"):
            if st.session_state.start_time is not None:
                # Calcular el tiempo real transcurrido en minutos
                end_time = datetime.now()
                elapsed_seconds = (end_time - st.session_state.start_time).total_seconds()
                elapsed_minutes = max(1, int(elapsed_seconds / 60)) # Mínimo 1 minuto para pruebas
                
                # Análisis de sentimiento con TextBlob
                try:
                    trans_text = GoogleTranslator(source='es', target='en').translate(closing_comment) if closing_comment else "Neutral reading session"
                except Exception:
                    trans_text = closing_comment if closing_comment else "Neutral"
                    
                blob = TextBlob(trans_text)
                polarity = round(blob.sentiment.polarity, 2)
                
                if polarity > 0.0:
                    sentimiento_str = "Positivo 😊"
                elif polarity < 0:
                    sentimiento_str = "Negativo 😔"
                else:
                    sentimiento_str = "Neutral 😐"
                    
                today_str = str(date.today())
                if today_str not in st.session_state.reading_sessions:
                    st.session_state.reading_sessions.append(today_str)
                
                # Guardar en el registro de tiempos para la gráfica
                st.session_state.time_log.append({
                    "fecha": today_str,
                    "libro": selected_book,
                    "minutos": elapsed_minutes
                })

                # Guardar en el historial de comentarios
                st.session_state.feedback_log.append({
                    "libro": selected_book,
                    "fecha": today_str,
                    "comentario": closing_comment if closing_comment else "Sin comentarios",
                    "sentimiento": sentimiento_str
                })

                # Reiniciar cronómetro
                st.session_state.start_time = None
                st.success(f"¡Sesión finalizada con éxito! Tiempo registrado: {elapsed_minutes} minutos.")
                st.rerun()
            else:
                st.warning("Debes iniciar el cronómetro primero antes de poder finalizar la sesión.")

# -------------------------------------------------------------------------
# MÓDULO 3: DIARIO, VALORACIONES Y ANÁLISIS (Página 2)
# -------------------------------------------------------------------------
elif menu == "🛋️ 2. Diario, Valoraciones y Análisis":
    st.title("🛋️ Diario de Lectura, Valoraciones y Analítica")
    st.markdown("Consulta toda la información guardada de tus libros, calificaciones con estrellas, sesiones, nube de vocabulario, gráfica de tiempos y análisis de sentimientos.")

    tab_diario, tab_vocab, tab_sentim = st.tabs(["📖 Diario, Tiempos y Sesiones", "☁️ Nube de Vocabulario", "📊 Analizador de Sentimientos"])

    # TAB 1: Diario completo con gráfica de tiempos y sesiones
    with tab_diario:
        st.subheader("📈 Gráfica de Tiempos de Lectura por Sesión")
        if st.session_state.time_log:
            df_time = pd.DataFrame(st.session_state.time_log)
            # Mostrar gráfico de barras usando los minutos leídos
            st.bar_chart(df_time, x="fecha", y="minutos", color="libro")
        else:
            st.info("Aún no hay registros de tiempo.")

        st.markdown("---")
        st.subheader("📚 Resumen y Analítica de Todos los Libros")
        
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

                st.markdown("#### 🕒 Historial de Sesiones y Tiempos:")
                libro_sessions = [s for s in st.session_state.feedback_log if s["libro"] == book_title]
                libro_times = [t for t in st.session_state.time_log if t["libro"] == book_title]
                
                if libro_sessions:
                    for idx, s in enumerate(libro_sessions, 1):
                        mins = libro_times[idx-1]["minutos"] if idx-1 < len(libro_times) else "N/A"
                        st.write(f"{idx}. **Fecha:** {s['fecha']} | **Tiempo:** {mins} min | **Sentimiento:** {s['sentimiento']} | *\"{s['comentario']}\"*")
                else:
                    st.write("Aún no hay sesiones guardadas para este libro.")

        st.markdown("---")
        st.subheader("📅 Calendario de Hábitos (Días de Lectura)")
        st.write("Fechas activas:", st.session_state.reading_sessions)
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
        
        cloud_html = " ".join([f"<span style='font-size: {random.randint(16, 32)}px; margin: 8px; color: #2E7D32; font-weight: bold; display: inline-block;'>{w}</span>" for w in st.session_state.vocab_list])
        st.markdown(f"<div style='padding: 25px; background-color: #E8F5E9; border-radius: 12px; text-align: center;'>{cloud_html}</div>", unsafe_allow_html=True)

    # TAB 3: Analizador de Sentimientos (Comentarios de sesiones)
    with tab_sentim:
        st.title('📊 Analizador de Sentimientos (Comentarios de Sesiones)')
        st.subheader("Aquí se analizan y muestran automáticamente las reflexiones que dejas al finalizar cada sesión:")

        if not st.session_state.feedback_log:
            st.info("Aún no hay comentarios de sesiones registradas.")
        else:
            for idx, item in enumerate(st.session_state.feedback_log, 1):
                with st.container():
                    st.markdown(f"**Sesión {idx} — Libro:** `{item['libro']}` *(Fecha: {item['fecha']})*")
                    st.info(f"💬 **Comentario:** \"{item['comentario']}\"\n\n**Sentimiento Evaluado:** {item['sentimiento']}")
                    st.markdown("---")
