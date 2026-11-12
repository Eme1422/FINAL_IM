import json
import os
import queue
import time
import uuid
from datetime import datetime, date

import pandas as pd
import streamlit as st
import paho.mqtt.client as mqtt
from textblob import TextBlob
from deep_translator import GoogleTranslator
from streamlit_autorefresh import st_autorefresh


# ============================================================
# CONFIGURACIÓN GENERAL
# ============================================================
st.set_page_config(
    page_title="MARGEN - Asistente de Lectura Multimodal",
    page_icon="📚",
    layout="wide"
)

# IMPORTANTE:
# Usa tópicos propios. El broker público HiveMQ no ofrece privacidad.
# Para una demostración puedes dejar estos valores o cambiarlos.
MQTT_BROKER = "broker.hivemq.com"
MQTT_PORT = 1883
MQTT_TOPIC_BASE = "margen/proyecto_lectura_demo_2026"
TOPIC_COMMANDS = f"{MQTT_TOPIC_BASE}/commands"
TOPIC_EVENTS = f"{MQTT_TOPIC_BASE}/events"

# El cliente MQTT se crea una sola vez por proceso de Streamlit.
# Los mensajes recibidos se depositan en una cola para procesarlos
# desde el hilo principal de Streamlit.
@st.cache_resource
def create_mqtt_connection():
    incoming_messages = queue.Queue()
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"margen-streamlit-{uuid.uuid4().hex[:8]}"
    )

    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            client.subscribe(TOPIC_EVENTS)
        else:
            print(f"Error de conexión MQTT: {reason_code}")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            incoming_messages.put(payload)
        except Exception as error:
            print(f"Mensaje MQTT no válido: {error}")

    client.on_connect = on_connect
    client.on_message = on_message

    try:
        client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
    except Exception as error:
        print(f"No fue posible iniciar MQTT: {error}")

    return client, incoming_messages


mqtt_client, mqtt_queue = create_mqtt_connection()


def publish_command(action, **extra_data):
    """Envía una orden desde Streamlit hacia el ESP32."""
    if not mqtt_client.is_connected():
        st.warning("No hay conexión MQTT. Revisa el broker y vuelve a intentar.")
        return False

    payload = {"action": action, **extra_data}
    result = mqtt_client.publish(
        TOPIC_COMMANDS,
        json.dumps(payload, ensure_ascii=False)
    )
    return result.rc == mqtt.MQTT_ERR_SUCCESS


# ============================================================
# ESTADOS DE STREAMLIT
# ============================================================
defaults = {
    "books": {
        "Cien años de soledad": {
            "total_pages": 400, "current_page": 180,
            "rating": 5,
            "review": "Una obra maestra absoluta llena de realismo mágico."
        },
        "El Principito": {
            "total_pages": 90, "current_page": 90,
            "rating": 4,
            "review": "Muy reflexivo, ideal para todas las edades."
        },
        "1984": {
            "total_pages": 328, "current_page": 210,
            "rating": 5,
            "review": "Una distopía escalofriante y sumamente vigente."
        },
        "Crimen y Castigo": {
            "total_pages": 500, "current_page": 140,
            "rating": 4,
            "review": "Profundo análisis psicológico y moral."
        }
    },
    "reading_sessions": [
        "2026-05-08", "2026-05-10", "2026-05-11",
        "2026-05-12", "2026-05-13"
    ],
    "time_log": [
        {"fecha": "2026-05-10", "libro": "Cien años de soledad", "minutos": 45,
         "pagina_inicial": 160, "pagina_final": 180, "paginas_leidas": 20},
        {"fecha": "2026-05-11", "libro": "1984", "minutos": 30,
         "pagina_inicial": 190, "pagina_final": 210, "paginas_leidas": 20},
        {"fecha": "2026-05-12", "libro": "El Principito", "minutos": 20,
         "pagina_inicial": 70, "pagina_final": 90, "paginas_leidas": 20},
        {"fecha": "2026-05-13", "libro": "Crimen y Castigo", "minutos": 60,
         "pagina_inicial": 120, "pagina_final": 140, "paginas_leidas": 20}
    ],
    "vocab_list": [
        "fascinante", "resiliencia", "epifanía", "nostalgia",
        "introspección", "melancolía", "efímero", "serendipia",
        "paradigma", "inefable", "pragmático", "catarsis",
        "utopía", "cognitivo", "multimodal", "heurística",
        "impredecible", "asombro", "soledad", "distopía",
        "imaginación", "trascendencia", "esencia", "misterio",
        "horizonte", "contemplación"
    ],
    "feedback_log": [
        {"libro": "Cien años de soledad", "fecha": "2026-05-10",
         "comentario": "Me encantó el capítulo de los gitanos, muy emocionante y mágico.",
         "sentimiento": "Positivo 😊"},
        {"libro": "1984", "fecha": "2026-05-11",
         "comentario": "El ambiente del libro se siente muy tenso, oscuro y agobiante.",
         "sentimiento": "Negativo 😔"},
        {"libro": "El Principito", "fecha": "2026-05-12",
         "comentario": "Una lectura bastante tranquila y reflexiva sobre la vida.",
         "sentimiento": "Neutral 😐"},
        {"libro": "Crimen y Castigo", "fecha": "2026-05-13",
         "comentario": "La culpa del personaje principal es agobiante pero brillante.",
         "sentimiento": "Positivo 😊"}
    ],
    "start_time": None,
    "elapsed_before_pause": 0.0,
    "session_active": False,
    "session_paused": False,
    "session_book": None,
    "session_start_page": 0,
    "device_events": [],
    "pending_device_finish": False,
    "selected_ambience": "Silencio"
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value.copy() if isinstance(value, (dict, list)) else value

# Asegurar claves nuevas cuando se actualice una versión previa de la app.
for key, value in {
    "elapsed_before_pause": 0.0,
    "session_active": False,
    "session_paused": False,
    "session_book": None,
    "session_start_page": 0,
    "device_events": [],
    "pending_device_finish": False,
    "selected_ambience": "Silencio"
}.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# FUNCIONES DE SESIÓN
# ============================================================
def start_reading(book, start_page, source="streamlit"):
    if st.session_state.session_active:
        st.warning("Ya hay una sesión activa. Finalízala o páusala antes de iniciar otra.")
        return

    st.session_state.session_book = book
    st.session_state.session_start_page = int(start_page)
    st.session_state.start_time = time.time()
    st.session_state.elapsed_before_pause = 0.0
    st.session_state.session_active = True
    st.session_state.session_paused = False

    publish_command(
        "start",
        book=book,
        page=int(start_page),
        source=source
    )


def pause_reading(source="streamlit"):
    if not st.session_state.session_active or st.session_state.session_paused:
        return

    if st.session_state.start_time is not None:
        st.session_state.elapsed_before_pause += time.time() - st.session_state.start_time

    st.session_state.start_time = None
    st.session_state.session_paused = True
    publish_command("pause", source=source)


def resume_reading(source="streamlit"):
    if not st.session_state.session_active or not st.session_state.session_paused:
        return

    st.session_state.start_time = time.time()
    st.session_state.session_paused = False
    publish_command("resume", source=source)


def elapsed_seconds():
    total = st.session_state.elapsed_before_pause
    if st.session_state.session_active and not st.session_state.session_paused:
        if st.session_state.start_time is not None:
            total += time.time() - st.session_state.start_time
    return max(0, int(total))


def analyze_sentiment(comment):
    if not comment.strip():
        return "Neutral 😐"

    try:
        translated = GoogleTranslator(source="es", target="en").translate(comment)
        polarity = TextBlob(translated).sentiment.polarity
    except Exception:
        # Si falla la traducción, TextBlob puede no interpretar bien el español.
        # Se conserva una salida neutral en lugar de inventar un resultado.
        polarity = 0

    if polarity > 0.05:
        return "Positivo 😊"
    if polarity < -0.05:
        return "Negativo 😔"
    return "Neutral 😐"


def save_reading_session(final_page, comment="", source="streamlit"):
    if not st.session_state.session_active:
        st.warning("No hay una sesión activa para finalizar.")
        return

    book = st.session_state.session_book
    if book not in st.session_state.books:
        st.error("No se encontró el libro asociado a esta sesión.")
        return

    book_data = st.session_state.books[book]
    final_page = int(final_page)
    start_page = int(st.session_state.session_start_page)

    if final_page < start_page:
        st.error("La página final no puede ser menor que la página inicial.")
        return
    if final_page > book_data["total_pages"]:
        st.error("La página final supera el total de páginas del libro.")
        return

    seconds = elapsed_seconds()
    minutes = max(1, round(seconds / 60))
    today_str = str(date.today())
    sentiment = analyze_sentiment(comment)

    session_record = {
        "fecha": today_str,
        "libro": book,
        "minutos": minutes,
        "pagina_inicial": start_page,
        "pagina_final": final_page,
        "paginas_leidas": final_page - start_page,
        "origen": source
    }

    st.session_state.time_log.append(session_record)
    if today_str not in st.session_state.reading_sessions:
        st.session_state.reading_sessions.append(today_str)

    st.session_state.feedback_log.append({
        "libro": book,
        "fecha": today_str,
        "comentario": comment.strip() if comment.strip() else "Sin comentarios",
        "sentimiento": sentiment
    })

    book_data["current_page"] = final_page

    st.session_state.session_active = False
    st.session_state.session_paused = False
    st.session_state.start_time = None
    st.session_state.elapsed_before_pause = 0.0
    st.session_state.session_book = None
    st.session_state.session_start_page = 0
    st.session_state.pending_device_finish = False

    publish_command("session_saved", page=final_page)


def process_device_events():
    """Procesa los mensajes recibidos desde Wokwi en el hilo principal."""
    while True:
        try:
            event = mqtt_queue.get_nowait()
        except queue.Empty:
            break

        st.session_state.device_events.append({
            "hora": datetime.now().strftime("%H:%M:%S"),
            "mensaje": event
        })
        st.session_state.device_events = st.session_state.device_events[-30:]

        event_name = event.get("event", "")

        if event_name == "start":
            if not st.session_state.session_active:
                requested_book = event.get("book")
                if requested_book in st.session_state.books:
                    book = requested_book
                else:
                    book = st.session_state.get("selected_book", list(st.session_state.books.keys())[0])

                page = event.get(
                    "page",
                    st.session_state.books[book]["current_page"]
                )
                page = max(0, min(int(page), st.session_state.books[book]["total_pages"]))
                start_reading(book, page, source="wokwi")
            else:
                st.info("El dispositivo solicitó iniciar, pero ya existe una sesión activa.")

        elif event_name == "pause":
            pause_reading(source="wokwi")

        elif event_name == "resume":
            resume_reading(source="wokwi")

        elif event_name == "finish":
            if st.session_state.session_active:
                st.session_state.pending_device_finish = True
                st.session_state.session_paused = True
                if st.session_state.start_time is not None:
                    st.session_state.elapsed_before_pause += time.time() - st.session_state.start_time
                st.session_state.start_time = None
            else:
                st.session_state.device_events.append({
                    "hora": datetime.now().strftime("%H:%M:%S"),
                    "mensaje": {"info": "Se recibió finish, pero no había sesión activa."}
                })

        elif event_name == "ambience":
            ambience = event.get("value", "Silencio")
            st.session_state.selected_ambience = ambience

        elif event_name in ("fire", "rain", "wind", "silence"):
            mapping = {
                "fire": "🔥 Fogata Relajante",
                "rain": "🌧️ Lluvia y Truenos",
                "wind": "💨 Sonido de Viento",
                "silence": "Silencio"
            }
            st.session_state.selected_ambience = mapping[event_name]


process_device_events()


# ============================================================
# ENCABEZADO Y NAVEGACIÓN
# ============================================================
st.sidebar.title("📚 MARGEN")
st.sidebar.caption("Tu compañero multimodal de lectura")
menu = st.sidebar.radio(
    "Navegación:",
    [
        "🏠 Inicio y Presentación",
        "🌌 1. Biblioteca y Sesión de Lectura",
        "🛋️ 2. Diario, Valoraciones y Análisis",
        "🔌 3. Dispositivo Wokwi"
    ]
)

connected = mqtt_client.is_connected()
st.sidebar.markdown("---")
st.sidebar.write("**Conexión con Wokwi**")
if connected:
    st.sidebar.success("Broker MQTT conectado")
else:
    st.sidebar.error("Broker MQTT desconectado")
st.sidebar.caption(f"Tópico: {MQTT_TOPIC_BASE}")


# ============================================================
# PÁGINA 0: INICIO
# ============================================================
if menu == "🏠 Inicio y Presentación":
    st.title("📚 MARGEN: Tu compañero inteligente de lectura")
    st.markdown("""
    **MARGEN** potencia la experiencia de lectura mediante una interfaz multimodal.
    Combina seguimiento de hábitos, registro del progreso de libros, ambientes sonoros,
    procesamiento de lenguaje natural y comunicación con un dispositivo físico simulado
    en Wokwi.
    """)

    st.info("Utiliza el menú lateral para explorar los módulos de MARGEN.")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### 📖 Gestión de libros y sesiones")
        st.write("Registra libros, páginas, duración de lectura y sesiones desde la aplicación o el dispositivo.")
    with col2:
        st.markdown("### 🧠 Análisis y experiencia sensorial")
        st.write("Explora vocabulario, reflexiones, análisis de sentimientos y ambientes de lectura.")

    st.markdown("### 📊 Tu actividad")
    total_minutes = sum(item["minutos"] for item in st.session_state.time_log)
    total_pages = sum(item.get("paginas_leidas", 0) for item in st.session_state.time_log)
    c1, c2, c3 = st.columns(3)
    c1.metric("Tiempo registrado", f"{total_minutes // 60} h {total_minutes % 60} min")
    c2.metric("Sesiones", len(st.session_state.time_log))
    c3.metric("Páginas registradas", total_pages)


# ============================================================
# PÁGINA 1: BIBLIOTECA Y SESIÓN
# ============================================================
elif menu == "🌌 1. Biblioteca y Sesión de Lectura":
    st.title("🌌 Biblioteca y sesión de lectura")
    st.write("Selecciona un libro, configura las páginas y comienza una sesión desde Streamlit o desde el dispositivo.")

    book_options = list(st.session_state.books.keys()) + ["➕ Agregar nuevo libro"]
    selected_option = st.selectbox("Selecciona un libro:", book_options)

    if selected_option == "➕ Agregar nuevo libro":
        st.subheader("📖 Registrar nuevo libro")
        new_title = st.text_input("Título del libro")
        new_total_pages = st.number_input("Número total de páginas", min_value=1, value=200, step=1)

        if st.button("Guardar libro"):
            if new_title.strip() and new_title not in st.session_state.books:
                st.session_state.books[new_title.strip()] = {
                    "total_pages": int(new_total_pages),
                    "current_page": 0,
                    "rating": 3,
                    "review": "Libro recién añadido."
                }
                st.success("Libro agregado.")
                st.rerun()
            else:
                st.warning("Escribe un título nuevo.")

    else:
        selected_book = selected_option
        st.session_state.selected_book = selected_book
        book_info = st.session_state.books[selected_book]

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Libro seleccionado:** {selected_book}")
            st.write(f"Total de páginas: {book_info['total_pages']}")
            current_page = st.number_input(
                "Página actual / página donde comenzar",
                min_value=0,
                max_value=int(book_info["total_pages"]),
                value=int(book_info["current_page"]),
                step=1,
                key=f"current_page_{selected_book}"
            )
            if not st.session_state.session_active:
                book_info["current_page"] = int(current_page)

        with col2:
            progress = book_info["current_page"] / book_info["total_pages"]
            st.metric("Progreso del libro", f"{progress * 100:.1f}%")
            st.progress(progress, text=f"Página {book_info['current_page']} de {book_info['total_pages']}")

        st.divider()
        st.subheader("🎧 Ambiente sonoro")
        ambience_options = [
            "Silencio",
            "🔥 Fogata Relajante",
            "🌧️ Lluvia y Truenos",
            "💨 Sonido de Viento"
        ]
        current_ambience = st.session_state.selected_ambience
        if current_ambience not in ambience_options:
            current_ambience = "Silencio"

        sound_choice = st.radio(
            "Selecciona un ambiente:",
            ambience_options,
            index=ambience_options.index(current_ambience),
            horizontal=True
        )
        st.session_state.selected_ambience = sound_choice

        ambience_command = {
            "Silencio": "silence",
            "🔥 Fogata Relajante": "fire",
            "🌧️ Lluvia y Truenos": "rain",
            "💨 Sonido de Viento": "wind"
        }[sound_choice]

        if st.button("Enviar ambiente al dispositivo"):
            publish_command("ambience", value=ambience_command)
            st.success("Orden de ambiente enviada al dispositivo.")

        if sound_choice == "🔥 Fogata Relajante":
            if os.path.exists("Fogata Relajante.mp3"):
                st.audio("Fogata Relajante.mp3")
            else:
                st.caption("Agrega 'Fogata Relajante.mp3' a la carpeta para reproducir este audio.")
        elif sound_choice == "🌧️ Lluvia y Truenos":
            if os.path.exists("Sonido de Lluvia y Truenos Distantes.mp3"):
                st.audio("Sonido de Lluvia y Truenos Distantes.mp3")
            else:
                st.caption("Agrega 'Sonido de Lluvia y Truenos Distantes.mp3' a la carpeta.")
        elif sound_choice == "💨 Sonido de Viento":
            if os.path.exists("Sonido de viento.mp3"):
                st.audio("Sonido de viento.mp3")
            else:
                st.caption("Agrega 'Sonido de viento.mp3' a la carpeta.")

        st.divider()
        st.subheader("⏱️ Control de sesión")

        if st.session_state.session_active:
            st.info(f"Sesión activa: {st.session_state.session_book}")
            seconds = elapsed_seconds()
            st.metric("Tiempo transcurrido", f"{seconds // 60:02d}:{seconds % 60:02d}")
            st.write(f"Página inicial: {st.session_state.session_start_page}")

            if st.session_state.session_paused:
                if st.button("▶ Reanudar sesión"):
                    resume_reading()
                    st.rerun()
            else:
                if st.button("⏸ Pausar sesión"):
                    pause_reading()
                    st.rerun()

            st.caption("También puedes pausar o finalizar desde los botones físicos de Wokwi.")
            st_autorefresh(interval=1000, key="active_session_refresh")

            if st.session_state.pending_device_finish:
                st.warning("El dispositivo solicitó finalizar la sesión. Indica la página en la que quedaste.")
                final_page = st.number_input(
                    "Página final",
                    min_value=int(st.session_state.session_start_page),
                    max_value=int(st.session_state.books[st.session_state.session_book]["total_pages"]),
                    value=int(st.session_state.books[st.session_state.session_book]["current_page"]),
                    step=1,
                    key="device_final_page"
                )
                final_comment = st.text_area(
                    "Reflexión de esta sesión (opcional)",
                    key="device_final_comment"
                )
                if st.button("Guardar sesión finalizada desde Wokwi", type="primary"):
                    save_reading_session(final_page, final_comment, source="wokwi")
                    st.success("Sesión guardada correctamente.")
                    st.rerun()

            else:
                manual_final_page = st.number_input(
                    "Página en la que quedaste",
                    min_value=int(st.session_state.session_start_page),
                    max_value=int(st.session_state.books[st.session_state.session_book]["total_pages"]),
                    value=int(st.session_state.books[st.session_state.session_book]["current_page"]),
                    step=1,
                    key="manual_final_page"
                )
                manual_comment = st.text_area(
                    "¿Qué tal la lectura de hoy? Escribe una reflexión:",
                    key="manual_final_comment"
                )
                if st.button("⏹ Finalizar y guardar sesión", type="primary"):
                    save_reading_session(manual_final_page, manual_comment)
                    st.success("Sesión finalizada y guardada.")
                    st.rerun()

        else:
            st.write("Puedes iniciar la sesión desde aquí o presionar el botón de inicio del dispositivo.")
            if st.button("▶ Iniciar cronómetro desde Streamlit", type="primary"):
                start_reading(selected_book, current_page)
                st.success("Sesión iniciada.")
                st.rerun()


# ============================================================
# PÁGINA 2: DIARIO Y ANÁLISIS
# ============================================================
elif menu == "🛋️ 2. Diario, Valoraciones y Análisis":
    st.title("🛋️ Diario de lectura, valoraciones y analítica")
    tab_diario, tab_vocab, tab_sentim = st.tabs([
        "📖 Diario y estadísticas",
        "☁️ Nube de vocabulario",
        "📊 Analizador de sentimientos"
    ])

    with tab_diario:
        st.subheader("📈 Tiempo de lectura por sesión")
        if st.session_state.time_log:
            df_time = pd.DataFrame(st.session_state.time_log)
            st.bar_chart(df_time, x="fecha", y="minutos", color="libro")
            st.dataframe(df_time, use_container_width=True)
        else:
            st.info("Aún no hay registros de tiempo.")

        total_minutes = sum(item["minutos"] for item in st.session_state.time_log)
        total_pages = sum(item.get("paginas_leidas", 0) for item in st.session_state.time_log)
        c1, c2, c3 = st.columns(3)
        c1.metric("Horas de lectura", f"{total_minutes / 60:.1f} h")
        c2.metric("Páginas leídas", total_pages)
        c3.metric("Días de lectura", len(set(st.session_state.reading_sessions)))

        st.subheader("📚 Biblioteca y progreso")
        for book_title, data in st.session_state.books.items():
            with st.expander(f"📖 {book_title} — {data['current_page']}/{data['total_pages']} páginas"):
                st.progress(data["current_page"] / data["total_pages"])
                st.write(f"Progreso: {data['current_page'] / data['total_pages'] * 100:.1f}%")
                new_rating = st.slider(
                    f"Calificación de {book_title}",
                    min_value=1, max_value=5,
                    value=int(data["rating"]),
                    key=f"rating_{book_title}"
                )
                data["rating"] = new_rating
                st.write(f"Puntuación: {'⭐' * new_rating}")
                data["review"] = st.text_area(
                    f"Reseña de {book_title}",
                    value=data["review"],
                    key=f"review_{book_title}"
                )

                st.markdown("**Historial de sesiones**")
                sessions = [s for s in st.session_state.time_log if s["libro"] == book_title]
                if sessions:
                    st.dataframe(pd.DataFrame(sessions), use_container_width=True)
                else:
                    st.caption("Todavía no hay sesiones registradas para este libro.")

        st.subheader("📅 Calendario de días de lectura")
        dates = sorted(set(st.session_state.reading_sessions))
        if dates:
            st.write("Días registrados:", ", ".join(dates))
            st.metric("Total de días leídos", len(dates))
        else:
            st.info("Aún no hay días registrados.")

    with tab_vocab:
        st.subheader("Generador visual de vocabulario")
        new_word = st.text_input("Añadir una palabra nueva")
        if st.button("Agregar palabra"):
            word = new_word.strip()
            if word and word not in st.session_state.vocab_list:
                st.session_state.vocab_list.append(word)
                st.success(f"'{word}' se agregó al vocabulario.")
                st.rerun()
            elif word:
                st.info("Esa palabra ya está registrada.")

        st.write("Palabras registradas:")
        st.write(", ".join(st.session_state.vocab_list))

        # Nube visual sencilla; el tamaño varía de manera ilustrativa.
        import random
        cloud_html = " ".join(
            f"<span style='font-size:{random.randint(16, 32)}px; margin:8px; "
            f"color:#2E7D32; font-weight:bold; display:inline-block;'>{word}</span>"
            for word in st.session_state.vocab_list
        )
        st.markdown(
            f"<div style='padding:25px; background-color:#E8F5E9; "
            f"border-radius:12px; text-align:center;'>{cloud_html}</div>",
            unsafe_allow_html=True
        )

    with tab_sentim:
        st.subheader("📊 Analizador de sentimientos")
        st.caption("El resultado es una aproximación automática, no una interpretación definitiva de emociones complejas.")
        if not st.session_state.feedback_log:
            st.info("Aún no hay reflexiones registradas.")
        else:
            for idx, item in enumerate(reversed(st.session_state.feedback_log), 1):
                with st.container(border=True):
                    st.markdown(f"**Reflexión {idx} — {item['libro']}** · {item['fecha']}")
                    st.write(item["comentario"])
                    st.info(f"Sentimiento estimado: {item['sentimiento']}")


# ============================================================
# PÁGINA 3: DISPOSITIVO WOKWI
# ============================================================
elif menu == "🔌 3. Dispositivo Wokwi":
    st.title("🔌 Conexión con el compañero físico")
    st.write("Esta sección permite comprobar la comunicación entre Streamlit y el ESP32 simulado en Wokwi.")

    if mqtt_client.is_connected():
        st.success("Streamlit está conectado al broker MQTT.")
    else:
        st.error("Streamlit no está conectado al broker MQTT. Reinicia la app y revisa tu conexión.")

    st.markdown("**Tópicos de comunicación**")
    st.code(f"Órdenes: {TOPIC_COMMANDS}\nEventos: {TOPIC_EVENTS}")

    st.subheader("Enviar órdenes al dispositivo")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("▶ Iniciar", use_container_width=True):
            book = st.session_state.get("selected_book", list(st.session_state.books.keys())[0])
            page = st.session_state.books[book]["current_page"]
            publish_command("start", book=book, page=page)
            st.success("Orden enviada.")
    with col2:
        if st.button("⏸ Pausar", use_container_width=True):
            publish_command("pause")
            st.success("Orden enviada.")
    with col3:
        if st.button("⏹ Finalizar", use_container_width=True):
            publish_command("finish")
            st.success("Orden enviada.")

    st.subheader("Cambiar ambiente del dispositivo")
    col1, col2, col3, col4 = st.columns(4)
    for col, label, value in [
        (col1, "Silencio", "silence"),
        (col2, "Fogata", "fire"),
        (col3, "Lluvia", "rain"),
        (col4, "Viento", "wind")
    ]:
        with col:
            if st.button(label, use_container_width=True):
                publish_command("ambience", value=value)
                st.success(f"Ambiente enviado: {label}")

    st.subheader("Eventos recibidos desde Wokwi")
    if st.session_state.device_events:
        for item in reversed(st.session_state.device_events[-10:]):
            st.write(f"**{item['hora']}** · `{json.dumps(item['mensaje'], ensure_ascii=False)}`")
    else:
        st.info("Todavía no se han recibido eventos del dispositivo.")

    st.caption("Deja esta página abierta para observar los eventos entrantes. La página se actualiza periódicamente.")
    st_autorefresh(interval=1500, key="device_events_refresh")
