import streamlit as st
from datetime import date
import random

# Configuración de la página
st.set_page_config(
    page_title="MARGEN - Asistente de Lectura Multimodal",
    page_icon="📚",
    layout="wide"
)

# Inicializar variables en st.session_state para mantener la memoria de la app
if "reading_sessions" not in st.session_state:
    st.session_state.reading_sessions = [] # Fechas en que se leyó

if "vocab_list" not in st.session_state:
    st.session_state.vocab_list = ["fascinante", "resiliencia", "epifanía", "nostalgia", "introspección"]

if "current_page" not in st.session_state:
    st.session_state.current_page = 0

if "total_pages" not in st.session_state:
    st.session_state.total_pages = 300

# Menú lateral de navegación unificado
st.sidebar.title("📚 MARGEN (Panel de Navegación)")
menu = st.sidebar.radio(
    "Selecciona una sección:",
    ["🏠 Inicio y Presentación", "🌌 1. Universo y Control Ambiental", "🛋️ 2. Espacio Cognitivo y Análisis"]
)

# -------------------------------------------------------------------------
# MÓDULO 1: INICIO Y PRESENTACIÓN
# -------------------------------------------------------------------------
if menu == "🏠 Inicio y Presentación":
    st.title("📚 MARGEN: Tu Compañero Inteligente de Lectura")
    st.markdown("""
    **MARGEN** es un sistema interactivo enfocado en potenciar la experiencia literaria mediante 
    interfaces multimodales. Este proyecto fusiona el control ambiental, el seguimiento de hábitos de lectura 
    y el procesamiento de lenguaje natural (NLP).
    """)
    
    st.info("👈 Utiliza el menú lateral izquierdo para explorar los módulos interactivos de la aplicación.")

    st.subheader("💡 Aspectos Clave del Proyecto")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### ¿Qué problema resuelve?")
        st.write("Ayuda a los lectores a mantener constancia en sus hábitos, controlar su ritmo de páginas, "
                 "generar un vocabulario activo y procesar el impacto emocional de sus lecturas.")
    with col2:
        st.markdown("### Innovación Tecnológica")
        st.write("Integra control de sesiones, ambientes sonoros relajantes inmersivos, generación visual de "
                 "nubes de palabras y análisis automatizado de sentimientos en una interfaz web moderna.")

# -------------------------------------------------------------------------
# MÓDULO 2: UNIVERSO Y CONTROL AMBIENTAL (Sesiones, Páginas, Sonidos)
# -------------------------------------------------------------------------
elif menu == "🌌 1. Universo y Control Ambiental":
    st.title("🌌 Mi Universo de Lectura")
    st.markdown("Administra tu libro actual, controla las horas de lectura, consulta tu calendario de hábitos y ambienta tu espacio.")

    col_ctrl_1, col_ctrl_2 = st.columns(2)

    with col_ctrl_1:
        st.subheader("📖 Control de Páginas del Libro")
        book_name = st.text_input("Título del libro actual:", "Cien años de soledad")
        st.session_state.total_pages = st.number_input("Número total de páginas:", min_value=10, max_value=2000, value=350)
        
        # Guardar página actual
        st.session_state.current_page = st.number_input(
            "¿En qué página vas?", 
            min_value=0, 
            max_value=st.session_state.total_pages, 
            value=st.session_state.current_page
        )
        
        # Barra de progreso visual
        progress_pct = int((st.session_state.current_page / st.session_state.total_pages) * 100)
        st.progress(progress_pct / 100, text=f"Progreso de lectura: {progress_pct}% completado")

    with col_ctrl_2:
        st.subheader("⏱️ Registro de Tiempo y Calendario")
        # Botón para registrar sesión de lectura del día de hoy
        today = date.today()
        if st.button("💾 Registrar sesión de lectura de hoy"):
            if str(today) not in st.session_state.reading_sessions:
                st.session_state.reading_sessions.append(str(today))
                st.success(f"¡Sesión registrada para el día {today}!")
            else:
                st.info("Ya habías registrado una sesión el día de hoy.")

        st.markdown("#### 📅 Días con Actividad de Lectura")
        # Mostramos de forma creativa los días registrados
        if st.session_state.reading_sessions:
            st.write("Días activos registrados:", ", ".join(st.session_state.reading_sessions))
        else:
            st.info("Aún no hay días registrados. ¡Haz clic en el botón de arriba para registrar tu lectura de hoy!")

    st.divider()

    st.subheader("🎧 Ambiente Sonoro No Invasivo (Audio)")
    st.markdown("Activa sonidos ambientales de fondo para mejorar tu concentración mientras lees:")
    
    sound_choice = st.radio(
        "Elige un sonido ambiental:",
        ["Silencio", "🔥 Fogata Nocturna", "🌧️ Lluvia Suave en Ventana", "🌲 Brisa de Bosque"],
        horizontal=True
    )

    if sound_choice == "🔥 Fogata Nocturna":
        st.audio("https://actions.google.com/sounds/v1/ambiences/campfire.ogg")
        st.info("💡 Reproduciendo sonido de fogata sutil y relajante.")
    elif sound_choice == "🌧️ Lluvia Suave en Ventana":
        st.audio("https://actions.google.com/sounds/v1/weather/rain_heavy.ogg")
        st.info("💡 Reproduciendo sonido de lluvia ligera.")
    elif sound_choice == "🌲 Brisa de Bosque":
        st.audio("https://actions.google.com/sounds/v1/ambiences/forest_birds.ogg")
        st.info("💡 Reproduciendo sonido ambiental de naturaleza.")
    else:
        st.write("Modo silencio activo.")

# -------------------------------------------------------------------------
# MÓDULO 3: ESPACIO COGNITIVO Y ANÁLISIS (WordCloud, Sentimientos, NLP)
# -------------------------------------------------------------------------
elif menu == "🛋️ 2. Espacio Cognitivo y Análisis":
    st.title("🛋️ Mi Espacio Cognitivo y Análisis Textual")
    st.markdown("Analiza tus reflexiones, evalúa los sentimientos del texto y genera recursos visuales con tu vocabulario.")

    tab_nlp_1, tab_nlp_2, tab_nlp_3 = st.tabs(["☁️ Nube de Vocabulario", "📊 Analizador de Sentimientos", "🔍 Analizador de Texto (NLP)"])

    # TAB 1: Nube de palabras con el vocabulario agregado
    with tab_nlp_1:
        st.subheader("Generador Visual de Vocabulario (WordCloud Simulado)")
        st.write("Agrega palabras nuevas que encuentres en tus lecturas para construir tu nube visual de aprendizaje:")
        
        new_word = st.text_input("Añadir nueva palabra al vocabulario:")
        if st.button("Agregar palabra"):
            if new_word and new_word.strip() not in st.session_state.vocab_list:
                st.session_state.vocab_list.append(new_word.strip())
                st.success(f"Palabra '{new_word}' agregada exitosamente.")
        
        st.markdown("#### Vocabulario Registrado:")
        st.write(", ".join([f"`{w}`" for w in st.session_state.vocab_list]))
        
        # Simulación visual atractiva de nube de palabras con Streamlit y Markdown de tamaños
        st.markdown("---")
        st.markdown("### Visualización de Términos Clave")
        cloud_html = " ".join([f"<span style='font-size: {random.randint(16, 32)}px; margin: 8px; color: #4CAF50;'>{w}</span>" for w in st.session_state.vocab_list])
        st.markdown(f"<div style='padding: 20px; background-color: #f0f2f6; border-radius: 10px; text-align: center;'>{cloud_html}</div>", unsafe_allow_html=True)

    # TAB 2: Análisis de sentimientos según lo que el usuario escriba
    with tab_nlp_2:
        st.subheader("Analizador de Sentimientos de tus Reflexiones")
        user_text = st.text_area("Escribe tu opinión, reseña o lo que sentiste al leer el capítulo:", placeholder="Ej: Me pareció un libro extraordinario, aunque el final me dejó muy triste y melancólico...")
        
        if st.button("Analizar Sentimiento"):
            if user_text:
                text_lower = user_text.lower()
                # Lógica heurística sencilla para la práctica de la clase
                palabras_positivas = ["excelente", "maravilloso", "feliz", "extraordinario", "hermoso", "genial", "gusta", "emocionante"]
                palabras_negativas = ["triste", "aburrido", "mal", "pesado", "tedioso", "confuso", "decepcionante", "melancólico"]
                
                score_pos = sum(1 for p in palabras_positivas if p in text_lower)
                score_neg = sum(1 for p in palabras_negativas if p in text_lower)
                
                st.markdown("### Resultados del Análisis:")
                if score_pos > score_neg:
                    st.success("😊 Sentimiento Detectado: **POSITIVO** (Tu texto refleja entusiasmo o agrado hacia la lectura).")
                elif score_neg > score_pos:
                    st.error("😞 Sentimiento Detectado: **NEGATIVO** (Tu texto refleja tensión, tristeza o insatisfacción).")
                else:
                    st.warning("😐 Sentimiento Detectado: **NEUTRAL / REFLEXIVO** (Un análisis equilibrado o descriptivo).")
            else:
                st.warning("Por favor escribe un texto para analizar.")

    # TAB 3: Analizador de texto general (conteo de palabras, caracteres, etc.)
    with tab_nlp_3:
        st.subheader("Estadísticas y Métricas del Texto")
        analysis_text = st.text_area("Pega un fragmento de texto para analizar sus métricas:", placeholder="Escribe o pega texto aquí...")
        
        if analysis_text:
            words = analysis_text.split()
            num_words = len(words)
            num_chars = len(analysis_text)
            num_sentences = analysis_text.count('.') + analysis_text.count('!') + analysis_text.count('?')
            
            col_m1, col_m2, col_m3 = st.columns(3)
            col_m1.metric("Total de Palabras", num_words)
            col_m2.metric("Total de Caracteres", num_chars)
            col_m3.metric("Oraciones Estimadas", max(1, num_sentences))
            
            st.markdown("#### Palabras más frecuentes (Top 3 simulado):")
            if num_words > 0:
                unique_words = list(set(words))
                sample_top = unique_words[:min(3, len(unique_words))]
                for idx, sw in enumerate(sample_top, 1):
                    st.write(f"{idx}. `{sw}` (Frecuencia detectada)")
