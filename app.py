import streamlit as st

# Configuración inicial de la página
st.set_page_config(
    page_title="MARGEN - Asistente de Lectura",
    page_icon="📚",
    layout="wide"
)

# Inicializar variables de estado global en Streamlit
if "session_active" not in st.session_state:
    st.session_state.session_active = False

if "current_env" not in st.session_state:
    st.session_state.current_env = "Neutral"

# Menú de navegación lateral (Estilo unificado de una sola app)
st.sidebar.title("📚 Menú MARGEN")
menu = st.sidebar.radio(
    "Selecciona el módulo:",
    ["🏠 Inicio", "🌌 Mi Universo (Ambiente y Sesión)", "🛋️ Mi Espacio (Bitácora y Notas)"]
)

# ---------------------------------------------------------
# MÓDULO 1: INICIO / BIENVENIDA
# ---------------------------------------------------------
if menu == "🏠 Inicio":
    st.title("📚 MARGEN: Tu Compañero Inteligente de Lectura")
    st.markdown("""
    Bienvenido a **MARGEN**, un sistema interactivo enfocado en potenciar la experiencia literaria 
    mediante interfaces multimodales. Esta plataforma fusiona el control de ambientes inmersivos, 
    el seguimiento de hábitos de lectura y la gestión de la memoria personal.
    """)
    
    st.info("👈 Utiliza el menú lateral izquierdo para cambiar entre los dos ambientes de la aplicación.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 🌌 Mi Universo de Lectura")
        st.write("Gestiona tus sesiones de lectura y personaliza la atmósfera del espacio mediante simulación de luces y sonidos ambientales.")
    with col2:
        st.markdown("### 🛋️ Mi Espacio de Lectura")
        st.write("Construye tu bitácora personal, registra reflexiones sobre fragmentos clave y supervisa tus estadísticas de lectura.")

# ---------------------------------------------------------
# MÓDULO 2: MI UNIVERSO (Control y Ambiente)
# ---------------------------------------------------------
elif menu == "🌌 Mi Universo (Ambiente y Sesión)":
    st.title("🌌 Mi Universo de Lectura")
    st.markdown("Panel de control interactivo para administrar tus sesiones literarias y configurar la atmósfera ideal del entorno.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("🕹️ Control de Sesión")
        if not st.session_state.session_active:
            if st.button("▶ Iniciar Sesión de Lectura", type="primary"):
                st.session_state.session_active = True
                st.success("¡Sesión iniciada con éxito! Disfruta tu lectura.")
                st.rerun()
        else:
            if st.button("⏹ Finalizar Sesión", type="secondary"):
                st.session_state.session_active = False
                st.warning("Sesión finalizada y guardada en el historial.")
                st.rerun()

    with col2:
        st.subheader("📊 Estado del Sistema")
        if st.session_state.session_active:
            st.markdown("🟢 **Estado:** Lectura Activa")
            st.metric(label="Cronómetro de sesión", value="En curso...")
        else:
            st.markdown("🔴 **Estado:** En Pausa / Reposo")
            st.metric(label="Cronómetro de sesión", value="0 min")

    st.divider()

    st.subheader("🎨 Configuración de Atmósfera Sensorial")
    env_option = st.selectbox(
        "Selecciona el ambiente lumínico y sonoro para acompañar tu lectura:",
        ["Neutral", "☕ Café Literario (Luz Ámbar)", "🌧️ Lluvia Nocturna (Ambiente Azulado)", "🌲 Bosque Profundo (Tonos Verdes)"]
    )

    if env_option != st.session_state.current_env:
        st.session_state.current_env = env_option
        st.toast(f"Atmósfera actualizada a: {env_option}", icon="✨")

    # Retroalimentación visual interactiva
    if "Café" in st.session_state.current_env:
        st.info("💡 **Efecto Visual:** Iluminación cálida y relajante simulada para lectura nocturna.")
    elif "Lluvia" in st.session_state.current_env:
        st.info("💧 **Efecto Visual:** Tonos azules tenues orientados a la máxima concentración y tranquilidad.")
    elif "Bosque" in st.session_state.current_env:
        st.info("🌿 **Efecto Visual:** Atmósfera verde suave para evitar la fatiga visual prolongada.")
    else:
        st.info("⚪ **Efecto Visual:** Iluminación estándar de trabajo y lectura.")

# ---------------------------------------------------------
# MÓDULO 3: MI ESPACIO (Bitácora y Métricas)
# ---------------------------------------------------------
elif menu == "🛋️ Mi Espacio (Bitácora y Notas)":
    st.title("🛋️ Mi Espacio de Lectura")
    st.markdown("Espacio dedicado a la construcción de memoria personal, anotación de fragmentos y revisión de tu progreso literario.")

    tab1, tab2 = st.tabs(["📝 Bitácora de Reflexiones", "📈 Progreso y Métricas"])

    with tab1:
        st.subheader("Registro de Notas y Opiniones")
        book_title = st.text_input("Título del libro actual:")
        user_thought = st.text_area("¿Qué te dejó este fragmento o capítulo? Escribe tu reflexión:")
        
        if st.button("Guardar en la Bitácora"):
            if book_title and user_thought:
                st.success(f"¡Reflexión registrada con éxito para el libro: *{book_title}*!")
                st.markdown(f"> *\"{user_thought}\"*")
            else:
                st.warning("Por favor completa el título y la reflexión antes de guardar.")

    with tab2:
        st.subheader("Tu Huella de Lectura")
        col_a, col_b = st.columns(2)
        with col_a:
            st.metric(label="Libros leídos este mes", value="3")
        with col_b:
            st.metric(label="Páginas totales recorritas", value="512")
        
        st.progress(70, text="Meta de lectura anual (70% completado)")
