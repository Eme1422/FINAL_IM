"""MARGEN - Asistente de lectura multimodal (Streamlit + MQTT + Wokwi/ESP32)."""
import html
import json
import os
import queue
import time
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

import paho.mqtt.client as mqtt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="MARGEN - Asistente de Lectura", layout="wide")

# ============================================================
# ESTILO (tonalidades azules)
# ============================================================
BLUES = ["#0D47A1", "#1565C0", "#1E88E5", "#42A5F5", "#64B5F6", "#90CAF9"]

st.markdown("""
<style>
.stApp {background: linear-gradient(180deg, #F4F8FD 0%, #E6F0FB 100%);}

/* Barra lateral */
[data-testid="stSidebar"] {background: linear-gradient(180deg, #D6E8FA 0%, #9CC7F0 100%);}
[data-testid="stSidebar"] * {color: #0A2A52;}

/* Títulos */
h1, h2, h3 {color: #0D47A1 !important;}
h1 {border-bottom: 3px solid #90CAF9; padding-bottom: 6px;}

/* Métricas como tarjetas */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border-left: 5px solid #1E88E5;
    border-radius: 10px;
    padding: 12px 16px;
    box-shadow: 0 2px 8px rgba(21, 101, 192, 0.12);
}
[data-testid="stMetricLabel"] {color: #1565C0;}
[data-testid="stMetricValue"] {color: #0D47A1;}

/* Botones */
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button {
    border: 1px solid #1E88E5; color: #1565C0; background: #FFFFFF; border-radius: 8px;
}
.stButton > button:hover, .stDownloadButton > button:hover,
[data-testid="stFormSubmitButton"] > button:hover {
    background: #E3F2FD; border-color: #0D47A1; color: #0D47A1;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #1565C0 0%, #42A5F5 100%); color: #FFFFFF; border: none;
}
.stButton > button[kind="primary"]:hover {
    background: linear-gradient(90deg, #0D47A1 0%, #1E88E5 100%); color: #FFFFFF;
}

/* Pestañas, contenedores y expanders */
.stTabs [data-baseweb="tab"] {color: #1565C0;}
.stTabs [aria-selected="true"] {color: #0D47A1; font-weight: 700;}
[data-testid="stVerticalBlockBorderWrapper"] {border-color: #90CAF9 !important; background: #F8FBFF;}
[data-testid="stExpander"] {border-color: #90CAF9; background: #F8FBFF; border-radius: 8px;}
hr {border-color: #BBDEFB !important;}
</style>
""", unsafe_allow_html=True)

# ============================================================
# CONFIGURACIÓN (se puede sobrescribir con variables de entorno)
# ============================================================
MQTT_BROKER = os.getenv("MARGEN_BROKER", "broker.hivemq.com")
MQTT_PORT = int(os.getenv("MARGEN_PORT", "1883"))
MQTT_TOPIC_BASE = os.getenv("MARGEN_TOPIC", "margen/proyecto_lectura_demo_2026")
TOPIC_COMMANDS = f"{MQTT_TOPIC_BASE}/commands"
TOPIC_EVENTS = f"{MQTT_TOPIC_BASE}/events"
DATA_FILE = Path(os.getenv("MARGEN_DATA", "margen_data.json"))
LOGO_FILE = Path(__file__).parent / "MARGEN.png"

AMBIENCE = {
    "silence": "Silencio",
    "fire": "Fogata relajante",
    "rain": "Lluvia y truenos",
    "wind": "Sonido de viento",
}
AMBIENCE_CMD = {label: cmd for cmd, label in AMBIENCE.items()}
AUDIO_FILES = {
    "fire": "Fogata Relajante.mp3",
    "rain": "Sonido de Lluvia y Truenos Distantes.mp3",
    "wind": "Sonido de viento.mp3",
}
PAGES = [
    "Inicio",
    "Biblioteca y sesión",
    "Diario y análisis",
    "Dispositivo Wokwi",
]
ADD_NEW = "+ Agregar nuevo libro"

ICON_OK = ":material/check_circle:"
ICON_WARN = ":material/warning:"


# ============================================================
# MQTT (un único cliente por proceso)
# ============================================================
@st.cache_resource
def create_mqtt_connection():
    incoming = queue.Queue(maxsize=500)
    client = mqtt.Client(
        mqtt.CallbackAPIVersion.VERSION2,
        client_id=f"margen-streamlit-{uuid.uuid4().hex[:8]}",
    )
    client.reconnect_delay_set(min_delay=1, max_delay=30)

    def on_connect(client, userdata, flags, reason_code, properties):
        if not reason_code.is_failure:
            client.subscribe(TOPIC_EVENTS, qos=1)  # se re-suscribe tras cada reconexión
        else:
            print(f"Error de conexión MQTT: {reason_code}")

    def on_message(client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            if isinstance(payload, dict):
                incoming.put_nowait(payload)
        except queue.Full:
            pass
        except Exception as error:
            print(f"Mensaje MQTT no válido: {error}")

    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=60)  # no bloquea el arranque
        client.loop_start()
    except Exception as error:
        print(f"No fue posible iniciar MQTT: {error}")
    return client, incoming


mqtt_client, mqtt_queue = create_mqtt_connection()


def publish_command(action, **extra):
    """Envía una orden al ESP32. Devuelve True si se publicó."""
    if not mqtt_client.is_connected():
        return False
    payload = json.dumps({"action": action, **extra}, ensure_ascii=False)
    return mqtt_client.publish(TOPIC_COMMANDS, payload, qos=1).rc == mqtt.MQTT_ERR_SUCCESS


def send(action, **extra):
    extra.setdefault("source", "streamlit")
    ok = publish_command(action, **extra)
    st.toast("Orden enviada" if ok else "Sin conexión MQTT", icon=ICON_OK if ok else ICON_WARN)


# ============================================================
# DATOS PERSISTENTES (JSON local) Y ESTADO
# ============================================================
PERSISTED = ["books", "time_log", "vocab_list", "feedback_log", "quotes", "weekly_goal_min"]


def seed_data():
    return {
        "books": {
            "Cien años de soledad": {"total_pages": 400, "current_page": 180, "rating": 5,
                                     "review": "Una obra maestra absoluta llena de realismo mágico."},
            "El Principito": {"total_pages": 90, "current_page": 90, "rating": 4,
                              "review": "Muy reflexivo, ideal para todas las edades."},
            "1984": {"total_pages": 328, "current_page": 210, "rating": 5,
                     "review": "Una distopía escalofriante y sumamente vigente."},
            "Crimen y Castigo": {"total_pages": 500, "current_page": 140, "rating": 4,
                                 "review": "Profundo análisis psicológico y moral."},
        },
        "time_log": [
            {"fecha": "2026-05-10", "libro": "Cien años de soledad", "minutos": 45,
             "pagina_inicial": 160, "pagina_final": 180, "paginas_leidas": 20},
            {"fecha": "2026-05-11", "libro": "1984", "minutos": 30,
             "pagina_inicial": 190, "pagina_final": 210, "paginas_leidas": 20},
            {"fecha": "2026-05-12", "libro": "El Principito", "minutos": 20,
             "pagina_inicial": 70, "pagina_final": 90, "paginas_leidas": 20},
            {"fecha": "2026-05-13", "libro": "Crimen y Castigo", "minutos": 60,
             "pagina_inicial": 120, "pagina_final": 140, "paginas_leidas": 20},
        ],
        "vocab_list": [
            "fascinante", "resiliencia", "epifanía", "nostalgia", "introspección", "melancolía",
            "efímero", "serendipia", "paradigma", "inefable", "pragmático", "catarsis", "utopía",
            "cognitivo", "multimodal", "heurística", "impredecible", "asombro", "soledad",
            "distopía", "imaginación", "trascendencia", "esencia", "misterio", "horizonte",
            "contemplación",
        ],
        "feedback_log": [
            {"libro": "Cien años de soledad", "fecha": "2026-05-10",
             "comentario": "Me encantó el capítulo de los gitanos, muy emocionante y mágico.",
             "sentimiento": "Positivo"},
            {"libro": "1984", "fecha": "2026-05-11",
             "comentario": "El ambiente del libro se siente muy tenso, oscuro y agobiante.",
             "sentimiento": "Negativo"},
            {"libro": "El Principito", "fecha": "2026-05-12",
             "comentario": "Una lectura bastante tranquila y reflexiva sobre la vida.",
             "sentimiento": "Neutral"},
            {"libro": "Crimen y Castigo", "fecha": "2026-05-13",
             "comentario": "La culpa del personaje principal es agobiante pero brillante.",
             "sentimiento": "Positivo"},
        ],
        "quotes": [],
        "weekly_goal_min": 150,
    }


def load_data():
    data = seed_data()
    if DATA_FILE.exists():
        try:
            data.update(json.loads(DATA_FILE.read_text(encoding="utf-8")))
        except Exception as error:
            print(f"No se pudo leer {DATA_FILE}: {error}")
    return data


def save_data():
    """Guardado atómico para no corromper el archivo si la app se cierra a mitad."""
    try:
        payload = {k: st.session_state[k] for k in PERSISTED}
        tmp = DATA_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(DATA_FILE)
    except Exception as error:
        print(f"No se pudo guardar: {error}")


def runtime_defaults():
    return {
        "start_time": None, "elapsed_before_pause": 0.0, "session_active": False,
        "session_paused": False, "session_book": None, "session_start_page": 0,
        "device_events": [], "pending_device_finish": False,
        "ambience": "Silencio", "selected_book": None,
    }


if "initialized" not in st.session_state:
    st.session_state.update(load_data())
    st.session_state.update(runtime_defaults())
    st.session_state.initialized = True


# ============================================================
# LÓGICA DE SESIÓN
# ============================================================
def elapsed_seconds():
    total = st.session_state.elapsed_before_pause
    if st.session_state.session_active and not st.session_state.session_paused:
        if st.session_state.start_time is not None:
            total += time.time() - st.session_state.start_time
    return max(0, int(total))


def _freeze_timer():
    if st.session_state.start_time is not None:
        st.session_state.elapsed_before_pause += time.time() - st.session_state.start_time
    st.session_state.start_time = None
    st.session_state.session_paused = True


def _clear_finish_widgets():
    for key in ("final_page", "final_comment"):
        st.session_state.pop(key, None)


def start_reading(book, start_page, source="streamlit"):
    if st.session_state.session_active:
        st.toast("Ya hay una sesión activa.", icon=ICON_WARN)
        return False
    st.session_state.update(
        session_book=book, session_start_page=int(start_page), start_time=time.time(),
        elapsed_before_pause=0.0, session_active=True, session_paused=False,
        pending_device_finish=False,
    )
    _clear_finish_widgets()
    publish_command("start", book=book, page=int(start_page), source=source)
    return True


def pause_reading(source="streamlit"):
    if st.session_state.session_active and not st.session_state.session_paused:
        _freeze_timer()
        publish_command("pause", source=source)


def resume_reading(source="streamlit"):
    if st.session_state.session_active and st.session_state.session_paused:
        st.session_state.start_time = time.time()
        st.session_state.session_paused = False
        st.session_state.pending_device_finish = False
        publish_command("resume", source=source)


POS_WORDS = ("encant", "emocion", "magic", "brillante", "hermos", "maravill", "genial",
             "excelente", "disfrut", "fascin", "feliz", "inspir")
NEG_WORDS = ("aburr", "tenso", "oscur", "agobi", "triste", "horrible", "malo", "pesad",
             "angusti", "decepcion", "confus")


@st.cache_data(show_spinner=False, max_entries=256)
def _translate_es_en(text):
    from deep_translator import GoogleTranslator  # import perezoso: arranque más rápido
    return GoogleTranslator(source="es", target="en").translate(text)


def analyze_sentiment(comment):
    text = comment.strip()
    if not text:
        return "Neutral"
    try:
        from textblob import TextBlob
        polarity = TextBlob(_translate_es_en(text)).sentiment.polarity
    except Exception:
        # Sin red: respaldo con un pequeño léxico en español.
        low = text.lower()
        polarity = 0.2 * (sum(w in low for w in POS_WORDS) - sum(w in low for w in NEG_WORDS))
    if polarity > 0.05:
        return "Positivo"
    if polarity < -0.05:
        return "Negativo"
    return "Neutral"


def sentiment_label(value):
    """Quita emojis de registros guardados con versiones anteriores (p. ej. 'Positivo 😊')."""
    return str(value).split(" ")[0]


def save_reading_session(final_page, comment="", source="streamlit"):
    """Devuelve (ok, mensaje)."""
    if not st.session_state.session_active:
        return False, "No hay una sesión activa."
    book = st.session_state.session_book
    book_data = st.session_state.books.get(book)
    if book_data is None:
        return False, "No se encontró el libro de esta sesión."

    final_page, start_page = int(final_page), int(st.session_state.session_start_page)
    if final_page < start_page:
        return False, "La página final no puede ser menor que la inicial."
    if final_page > book_data["total_pages"]:
        return False, "La página final supera el total del libro."

    minutes = max(1, round(elapsed_seconds() / 60))
    today = str(date.today())
    st.session_state.time_log.append({
        "fecha": today, "libro": book, "minutos": minutes, "pagina_inicial": start_page,
        "pagina_final": final_page, "paginas_leidas": final_page - start_page, "origen": source,
    })
    if comment.strip():
        st.session_state.feedback_log.append({
            "libro": book, "fecha": today, "comentario": comment.strip(),
            "sentimiento": analyze_sentiment(comment),
        })
    book_data["current_page"] = final_page
    st.session_state[f"current_page_{book}"] = final_page  # sincroniza el number_input

    st.session_state.update(
        session_active=False, session_paused=False, start_time=None, elapsed_before_pause=0.0,
        session_book=None, session_start_page=0, pending_device_finish=False,
    )
    _clear_finish_widgets()
    save_data()
    publish_command("session_saved", page=final_page, minutes=minutes)
    return True, f"Sesión guardada: {minutes} min, {final_page - start_page} páginas."


def process_device_events():
    """Vacía la cola MQTT y aplica los eventos. Devuelve True si hubo alguno."""
    changed = False
    while True:
        try:
            event = mqtt_queue.get_nowait()
        except queue.Empty:
            break
        changed = True
        st.session_state.device_events.append({"hora": datetime.now().strftime("%H:%M:%S"), "mensaje": event})
        st.session_state.device_events = st.session_state.device_events[-30:]

        name = event.get("event", "")
        books = st.session_state.books

        if name == "start" and not st.session_state.session_active:
            book = event.get("book")
            if book not in books:
                book = st.session_state.selected_book or next(iter(books))
            try:
                page = int(event.get("page", books[book]["current_page"]))
            except (TypeError, ValueError):
                page = books[book]["current_page"]
            start_reading(book, max(0, min(page, books[book]["total_pages"])), source="wokwi")
        elif name == "pause":
            pause_reading(source="wokwi")
        elif name == "resume":
            resume_reading(source="wokwi")
        elif name == "finish" and st.session_state.session_active:
            if not st.session_state.session_paused:
                _freeze_timer()
            st.session_state.pending_device_finish = True
        elif name in AMBIENCE:
            st.session_state.ambience = AMBIENCE[name]
        elif name == "ambience":
            value = event.get("value", "silence")
            if value in AMBIENCE:
                st.session_state.ambience = AMBIENCE[value]
            elif value in AMBIENCE_CMD:
                st.session_state.ambience = value
    return changed


@st.fragment(run_every=1)
def device_sync():
    """Se ejecuta cada segundo SIN recargar toda la app; solo recarga si llegó un evento."""
    if mqtt_client.is_connected():
        st.success("Broker MQTT conectado", icon=":material/wifi:")
    else:
        st.error("Broker MQTT desconectado", icon=":material/wifi_off:")
    st.caption(f"Tópico: {MQTT_TOPIC_BASE}")
    if process_device_events():
        st.rerun()


# ============================================================
# ANALÍTICA
# ============================================================
def time_df():
    df = pd.DataFrame(st.session_state.time_log)
    for col in ("fecha", "libro", "minutos", "paginas_leidas"):
        if col not in df:
            df[col] = 0
    df["fecha"] = pd.to_datetime(df["fecha"])
    return df


def reading_streak(days):
    day = date.today()
    if day not in days:
        day -= timedelta(days=1)
    streak = 0
    while day in days:
        streak += 1
        day -= timedelta(days=1)
    return streak


def estimate_remaining(title, df):
    book = st.session_state.books[title]
    remaining = book["total_pages"] - book["current_page"]
    if remaining <= 0:
        return "Terminado"
    rows = df[df["libro"] == title]
    mins, pages = rows["minutos"].sum(), rows["paginas_leidas"].sum()
    if mins <= 0 or pages <= 0:
        return "Sin datos suficientes"
    return f"≈ {remaining * mins / pages / 60:.1f} h restantes ({pages / mins * 60:.0f} pág/h)"


# ============================================================
# CALLBACKS
# ============================================================
def cb_start():
    book = st.session_state.selected_book
    if not book:
        return
    page = st.session_state.get(f"current_page_{book}", st.session_state.books[book]["current_page"])
    if start_reading(book, page):
        st.toast("Sesión iniciada", icon=ICON_OK)


def cb_finish():
    pending = st.session_state.pending_device_finish
    ok, msg = save_reading_session(
        st.session_state.get("final_page", 0), st.session_state.get("final_comment", ""),
        source="wokwi" if pending else "streamlit",
    )
    st.toast(msg, icon=ICON_OK if ok else ICON_WARN)


def cb_save_goal():
    st.session_state.weekly_goal_min = int(st.session_state.goal_widget)
    save_data()


def cb_rating(title):
    st.session_state.books[title]["rating"] = int(st.session_state[f"rating_{title}"])
    save_data()


def cb_review(title):
    st.session_state.books[title]["review"] = st.session_state[f"review_{title}"]
    save_data()


# ============================================================
# PÁGINAS
# ============================================================
def page_home():
    st.title("MARGEN: Tu compañero inteligente de lectura")
    st.caption("Seguimiento de hábitos, ambientes sonoros, análisis de reflexiones y un dispositivo físico simulado.")

    df = time_df()
    days = set(df["fecha"].dt.date)
    total_min = int(df["minutos"].sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tiempo total", f"{total_min // 60} h {total_min % 60} min")
    c2.metric("Sesiones", len(df))
    c3.metric("Páginas leídas", int(df["paginas_leidas"].sum()))
    c4.metric("Racha", f"{reading_streak(days)} días")

    week_start = date.today() - timedelta(days=date.today().weekday())
    week_min = int(df.loc[df["fecha"].dt.date >= week_start, "minutos"].sum())
    goal = max(1, int(st.session_state.weekly_goal_min))
    st.progress(min(week_min / goal, 1.0), text=f"Meta semanal: {week_min} / {goal} min")
    with st.expander("Cambiar meta semanal"):
        st.number_input("Minutos por semana", 10, 3000, goal, 10, key="goal_widget", on_change=cb_save_goal)

    st.subheader("Últimos 14 días")
    idx = pd.date_range(end=date.today(), periods=14).date
    daily = df.groupby(df["fecha"].dt.date)["minutos"].sum().reindex(idx, fill_value=0)
    daily.index = pd.to_datetime(daily.index)
    st.bar_chart(daily, y_label="minutos", color="#1E88E5")

    if st.session_state.session_active:
        st.info(f"Sesión en curso: **{st.session_state.session_book}**. Ve a *Biblioteca y sesión*.")


def _timer_view():
    secs = elapsed_seconds()
    c1, c2, c3 = st.columns(3)
    c1.metric("Tiempo transcurrido", f"{secs // 60:02d}:{secs % 60:02d}")
    c2.metric("Estado", "En pausa" if st.session_state.session_paused else "Leyendo")
    c3.metric("Página inicial", st.session_state.session_start_page)


def page_library():
    st.title("Biblioteca y sesión de lectura")
    books = st.session_state.books
    active = st.session_state.session_active

    if active:
        selected_book = st.session_state.session_book
        st.info(f"Sesión en curso: **{selected_book}**")
    else:
        options = list(books) + [ADD_NEW]
        choice = st.selectbox("Selecciona un libro:", options)
        if choice == ADD_NEW:
            with st.form("new_book", clear_on_submit=True):
                title = st.text_input("Título del libro").strip()
                total = st.number_input("Número total de páginas", min_value=1, value=200)
                if st.form_submit_button("Guardar libro"):
                    if title and title not in books:
                        books[title] = {"total_pages": int(total), "current_page": 0,
                                        "rating": 3, "review": "Libro recién añadido."}
                        save_data()
                        st.rerun()
                    else:
                        st.warning("Escribe un título nuevo.")
            return
        selected_book = choice
        st.session_state.selected_book = choice

    info = books[selected_book]
    page_key = f"current_page_{selected_book}"
    st.session_state.setdefault(page_key, int(info["current_page"]))

    col1, col2 = st.columns(2)
    with col1:
        st.number_input("Página actual / donde comenzar", 0, int(info["total_pages"]),
                        step=1, key=page_key, disabled=active)
        if not active and int(st.session_state[page_key]) != info["current_page"]:
            info["current_page"] = int(st.session_state[page_key])
            save_data()
    with col2:
        progress = info["current_page"] / info["total_pages"]
        st.metric("Progreso del libro", f"{progress * 100:.1f}%")
        st.progress(progress, text=f"Página {info['current_page']} de {info['total_pages']}")

    # --- Ambiente sonoro (se envía al dispositivo automáticamente al cambiar) ---
    # El audio se reproduce desde la barra lateral (ver ambience_player), así suena en cualquier página.
    st.divider()
    st.subheader("Ambiente sonoro")
    labels = list(AMBIENCE.values())
    current = st.session_state.ambience if st.session_state.ambience in labels else "Silencio"
    choice = st.radio("Ambiente:", labels, index=labels.index(current), horizontal=True)
    if choice != st.session_state.ambience:
        st.session_state.ambience = choice
        send("ambience", value=AMBIENCE_CMD[choice])
    audio_file = AUDIO_FILES.get(AMBIENCE_CMD[choice])
    if audio_file and not os.path.exists(audio_file):
        st.caption(f"Agrega '{audio_file}' a la carpeta de la app para reproducir este audio.")

    # --- Sesión ---
    st.divider()
    st.subheader("Control de sesión")
    if not active:
        st.write("Inicia aquí o con el botón físico del dispositivo.")
        st.button("Iniciar sesión", type="primary", on_click=cb_start)
        return

    paused = st.session_state.session_paused
    # Solo se refresca este bloque cada segundo; si está en pausa no hay refresco.
    st.fragment(_timer_view, run_every=None if paused else 1)()

    if paused:
        st.button("Reanudar", on_click=resume_reading)
    else:
        st.button("Pausar", on_click=pause_reading)

    if st.session_state.pending_device_finish:
        st.warning("El dispositivo pidió finalizar. Indica en qué página quedaste.")

    start = int(st.session_state.session_start_page)
    total = int(books[st.session_state.session_book]["total_pages"])
    st.session_state.setdefault("final_page", min(max(start, info["current_page"]), total))
    st.number_input("Página en la que quedaste", start, total, step=1, key="final_page")
    st.text_area("Reflexión de la sesión (opcional)", key="final_comment")
    st.button("Finalizar y guardar", type="primary", on_click=cb_finish)


def page_diary():
    st.title("Diario, valoraciones y analítica")
    tab_diary, tab_vocab, tab_sent, tab_quotes = st.tabs(
        ["Diario y estadísticas", "Vocabulario", "Sentimientos", "Citas"])

    df = time_df()

    with tab_diary:
        if df.empty:
            st.info("Aún no hay sesiones registradas.")
        else:
            st.subheader("Minutos por día y libro")
            pivot = df.pivot_table(index="fecha", columns="libro", values="minutos",
                                   aggfunc="sum", fill_value=0)
            colors = [BLUES[i % len(BLUES)] for i in range(len(pivot.columns))]
            st.bar_chart(pivot, color=colors)
            raw = pd.DataFrame(st.session_state.time_log).sort_values("fecha", ascending=False)
            st.dataframe(raw.head(50), width="stretch")
            st.download_button("Exportar sesiones (CSV)", raw.to_csv(index=False).encode("utf-8"),
                               "margen_sesiones.csv", "text/csv")

        days = set(df["fecha"].dt.date)
        c1, c2, c3 = st.columns(3)
        c1.metric("Horas de lectura", f"{df['minutos'].sum() / 60:.1f} h")
        c2.metric("Páginas leídas", int(df["paginas_leidas"].sum()))
        c3.metric("Días de lectura", len(days))

        st.subheader("Detalle por libro")
        title = st.selectbox("Libro", list(st.session_state.books), key="diary_book")
        data = st.session_state.books[title]
        st.progress(data["current_page"] / data["total_pages"],
                    text=f"{data['current_page']}/{data['total_pages']} páginas")
        st.caption(f"Tiempo estimado para terminar: {estimate_remaining(title, df)}")
        st.slider(f"Calificación de {title}", 1, 5, int(data["rating"]),
                  key=f"rating_{title}", on_change=cb_rating, args=(title,))
        st.text_area("Reseña", data["review"], key=f"review_{title}",
                     on_change=cb_review, args=(title,))
        sessions = [s for s in st.session_state.time_log if s["libro"] == title]
        if sessions:
            st.dataframe(pd.DataFrame(sessions), width="stretch")

    with tab_vocab:
        st.subheader("Vocabulario")
        with st.form("vocab_form", clear_on_submit=True):
            word = st.text_input("Añadir una palabra nueva").strip()
            if st.form_submit_button("Agregar") and word:
                if word not in st.session_state.vocab_list:
                    st.session_state.vocab_list.append(word)
                    save_data()
                    st.rerun()
                st.info("Esa palabra ya está registrada.")
        # Tamaño y color deterministas (antes cambiaban aleatoriamente en cada recarga).
        cloud = " ".join(
            f"<span style='font-size:{16 + sum(map(ord, w)) % 17}px;margin:8px;"
            f"color:{BLUES[sum(map(ord, w)) % 4]};font-weight:bold;display:inline-block;'>"
            f"{html.escape(w)}</span>"
            for w in st.session_state.vocab_list
        )
        st.markdown(f"<div style='padding:25px;background:linear-gradient(135deg,#E3F2FD,#BBDEFB);"
                    f"border:1px solid #90CAF9;border-radius:12px;text-align:center;'>{cloud}</div>",
                    unsafe_allow_html=True)
        if st.session_state.vocab_list:
            to_remove = st.selectbox("Eliminar palabra", [""] + st.session_state.vocab_list)
            if to_remove and st.button("Eliminar"):
                st.session_state.vocab_list.remove(to_remove)
                save_data()
                st.rerun()

    with tab_sent:
        st.subheader("Analizador de sentimientos")
        st.caption("Aproximación automática; no sustituye una interpretación de emociones complejas.")
        test = st.text_area("Prueba un texto", key="sent_test")
        if st.button("Analizar") and test.strip():
            st.info(f"Sentimiento estimado: {analyze_sentiment(test)}")

        log = st.session_state.feedback_log
        if log:
            counts = pd.Series([sentiment_label(i["sentimiento"]) for i in log]).value_counts()
            st.bar_chart(counts, color="#1E88E5")
            for item in reversed(log[-10:]):
                with st.container(border=True):
                    st.markdown(f"**{item['libro']}** · {item['fecha']}")
                    st.write(item["comentario"])
                    st.caption(f"Sentimiento estimado: {sentiment_label(item['sentimiento'])}")
        else:
            st.info("Aún no hay reflexiones registradas.")

    with tab_quotes:
        st.subheader("Citas favoritas")
        with st.form("quote_form", clear_on_submit=True):
            book = st.selectbox("Libro", list(st.session_state.books))
            page = st.number_input("Página", min_value=0, value=0)
            quote = st.text_area("Cita")
            if st.form_submit_button("Guardar cita") and quote.strip():
                st.session_state.quotes.append({"libro": book, "pagina": int(page),
                                                "cita": quote.strip(), "fecha": str(date.today())})
                save_data()
                st.rerun()
        for q in reversed(st.session_state.quotes):
            with st.container(border=True):
                st.markdown(f"> {q['cita']}")
                st.caption(f"{q['libro']} · pág. {q['pagina']} · {q['fecha']}")


def page_device():
    st.title("Conexión con el compañero físico")

    # Imagen de la sección MQTT
    if LOGO_FILE.exists():
        st.image(str(LOGO_FILE), width=320)
    else:
        st.caption("Agrega 'MARGEN.png' a la carpeta de la app para mostrar la imagen.")

    st.code(f"Órdenes (app → ESP32): {TOPIC_COMMANDS}\nEventos (ESP32 → app): {TOPIC_EVENTS}")

    st.subheader("Enviar órdenes")
    c1, c2, c3, c4 = st.columns(4)
    book = st.session_state.selected_book or next(iter(st.session_state.books))
    if c1.button("Iniciar", width="stretch"):
        send("start", book=book, page=st.session_state.books[book]["current_page"])
    if c2.button("Pausar", width="stretch"):
        send("pause")
    if c3.button("Reanudar", width="stretch"):
        send("resume")
    if c4.button("Finalizar", width="stretch"):
        send("finish")

    st.subheader("Ambiente del dispositivo")
    cols = st.columns(4)
    for col, (cmd, label) in zip(cols, AMBIENCE.items()):
        if col.button(label, width="stretch", key=f"amb_{cmd}"):
            send("ambience", value=cmd)

    st.subheader("Eventos recibidos")
    if st.button("Limpiar eventos"):
        st.session_state.device_events = []
    events = st.session_state.device_events
    if events:
        for item in reversed(events[-10:]):
            st.write(f"**{item['hora']}** · `{json.dumps(item['mensaje'], ensure_ascii=False)}`")
    else:
        st.info("Todavía no se han recibido eventos del dispositivo.")

    with st.expander("Formato de mensajes"):
        st.markdown(
            "**ESP32 → app** (`events`): `{\"event\":\"start\",\"book\":\"1984\",\"page\":210}`, "
            "`{\"event\":\"pause\"}`, `{\"event\":\"resume\"}`, `{\"event\":\"finish\"}`, "
            "`{\"event\":\"ambience\",\"value\":\"rain\"}` (silence, fire, rain, wind).\n\n"
            "**App → ESP32** (`commands`): `{\"action\":\"start|pause|resume|finish|ambience|session_saved\", "
            "\"source\":\"streamlit|wokwi\", ...}`. Si `source` es `wokwi`, el ESP32 ya hizo el cambio "
            "y puede ignorar el comando para evitar bucles."
        )


# ============================================================
# AUDIO AMBIENTAL (suena en cualquier página)
# ============================================================
def ambience_player():
    cmd = AMBIENCE_CMD.get(st.session_state.ambience)
    audio_file = AUDIO_FILES.get(cmd)
    if audio_file and os.path.exists(audio_file):
        st.audio(audio_file, loop=True, autoplay=True)


# ============================================================
# NAVEGACIÓN
# ============================================================
st.sidebar.title("MARGEN")
st.sidebar.caption("Tu compañero multimodal de lectura")
menu = st.sidebar.radio("Navegación:", PAGES)
st.sidebar.markdown("---")
with st.sidebar:
    device_sync()

{PAGES[0]: page_home, PAGES[1]: page_library, PAGES[2]: page_diary, PAGES[3]: page_device}[menu]()

# Va después de la página para que ya conozca el ambiente elegido en esta ejecución.
with st.sidebar:
    ambience_player()
