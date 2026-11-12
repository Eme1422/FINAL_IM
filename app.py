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

st.set_page_config(page_title="MARGEN - Asistente de Lectura", page_icon="📖", layout="wide")

# ============================================================
# ESTILOS CSS PERSONALIZADOS (Tonalidades Azules Minimalistas)
# ============================================================
st.markdown("""
<style>
    /* Fondo y degradado general de la barra lateral */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #EBF3FC 0%, #D4E5FA 100%);
        border-right: 1px solid #C4D9F8;
    }
    
    /* Estilo general de los botones principales */
    .stButton > button {
        background-color: #2B6CB0;
        color: white;
        border-radius: 6px;
        border: none;
        font-weight: 500;
        transition: background-color 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #1A4975;
        color: white;
    }
    
    /* Contenedores con bordes limpios y sutiles */
    div[data-testid="stVerticalBlock"] > div[style*="border"] {
        border-color: #CBD5E1 !important;
        border-radius: 8px;
    }
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

AMBIENCE = {
    "silence": "Silencio",
    "fire": "Fogata",
    "rain": "Lluvia",
    "wind": "Viento",
}
AMBIENCE_CMD = {label: cmd for cmd, label in AMBIENCE.items()}
AUDIO_FILES = {
    "fire": "Fogata Relajante.mp3",
    "rain": "Sonido de Lluvia y Truenos Distantes.mp3",
    "wind": "Sonido de viento.mp3",
}
PAGES = [
    "Inicio",
    "Biblioteca y Sesión",
    "Diario y Análisis",
    "Dispositivo Wokwi",
]
ADD_NEW = "+ Agregar nuevo libro"


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
            client.subscribe(TOPIC_EVENTS, qos=1)
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
        client.connect_async(MQTT_BROKER, MQTT_PORT, keepalive=60)
        client.loop_start()
    except Exception as error:
        print(f"No fue posible iniciar MQTT: {error}")
    return client, incoming


mqtt_client, mqtt_queue = create_mqtt_connection()


def publish_command(action, **extra):
    if not mqtt_client.is_connected():
        return False
    payload = json.dumps({"action": action, **extra}, ensure_ascii=False)
    return mqtt_client.publish(TOPIC_COMMANDS, payload, qos=1).rc == mqtt.MQTT_ERR_SUCCESS


def send(action, **extra):
    extra.setdefault("source", "streamlit")
    ok = publish_command(action, **extra)
    st.toast("Orden enviada" if ok else "Sin conexión MQTT", icon="info" if ok else "warning")


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
        st.toast("Ya hay una sesión activa.", icon="warning")
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
    from deep_translator import GoogleTranslator
    return GoogleTranslator(source="es", target="en").translate(text)


def analyze_sentiment(comment):
    text = comment.strip()
    if not text:
        return "Neutral"
    try:
        from textblob import TextBlob
        polarity = TextBlob(_translate_es_en(text)).sentiment.polarity
    except Exception:
        low = text.lower()
        polarity = 0.2 * (sum(w in low for w in POS_WORDS) - sum(w in low for w in NEG_WORDS))
    if polarity > 0.05:
        return "Positivo"
    if polarity < -0.05:
        return "Negativo"
    return "Neutral"


def save_reading_session(final_page, comment="", source="streamlit"):
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
    st.session_state[f"current_page_{book}"] = final_page

    st.session_state.update(
        session_active=False, session_paused=False, start_time=None, elapsed_before_pause=0.0,
        session_book=None, session_start_page=0, pending_device_finish=False,
    )
    _clear_finish_widgets()
    save_data()
    publish_command("session_saved", page=final_page, minutes=minutes)
    return True, f"Sesión guardada: {minutes} min, {final_page - start_page} páginas."


def process_device_events():
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
    if mqtt_client.is_connected():
        st.success("Broker MQTT conectado", icon="info")
    else:
        st.error("Broker MQTT desconectado", icon="warning")
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
        return "Completado"
    rows = df[df["libro"] == title]
    mins, pages = rows["minutos"].sum(), rows["paginas_leidas"].sum()
    if mins <= 0 or pages <= 0:
        return "Datos insuficientes"
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
        st.toast("Sesión iniciada", icon="info")


def cb_finish():
    pending = st.session_state.pending_device_finish
    ok, msg = save_reading_session(
        st.session_state.get("final_page", 0), st.session_state.get("final_comment", ""),
        source="wokwi" if pending else "streamlit",
    )
    st.toast(msg, icon="info" if ok else "warning")


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
    st.title("MARGEN")
    st.caption("Asistente inteligente de lectura y seguimiento de hábitos.")

    df = time_df()
    days = set(df["fecha"].dt.date)
    total_min = int(df["minutos"].sum())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tiempo total", f"{total_min // 60} h {total_min % 60} min")
    c2.metric("Sesiones", len(df))
    c3.metric("Páginas leídas", int(df["paginas_leidas"].sum()))
    c4.metric("Racha actual", f"{reading_streak(days)} días")

    week_start = date.today() - timedelta(days=date.today().weekday())
    week_min = int(df.loc[df["fecha"].dt.date >= week_start, "minutos"].sum())
    goal = max(1, int(st.session_state.weekly_goal_min))
    st.progress(min(week_min / goal, 1.0), text=f"Meta semanal: {week_min} / {goal} min")
    with st.expander("Configurar meta semanal"):
        st.number_input("Minutos por semana", 10, 3000, goal, 10, key="goal_widget", on_change=cb_save_goal)

    st.subheader("Actividad de los últimos 14 días")
    idx = pd.date_range(end=date.today(), periods=14).date
    daily = df.groupby(df["fecha"].dt.date)["minutos"].sum().reindex(idx, fill_value=0)
    daily.index = pd.to_datetime(daily.index)
    st.bar_chart(daily, y_label="minutos")

    if st.session_state.session_active:
        st.info(f"Sesión en curso: **{st.session_state.session_book}**. Diríjase a la sección *Biblioteca y Sesión*.")


def _timer_view():
    secs = elapsed_seconds()
    c1, c2, c3 = st.columns(3)
    c1.metric("Tiempo transcurrido", f"{secs // 60:02d}:{secs % 60:02d}")
    c2.metric("Estado", "En pausa" if st.session_state.session_paused else "Leyendo")
    c3.metric("Página inicial", st.session_state.session_start_page)


def page_library():
    st.title("Biblioteca y Sesión")
    books = st.session_state.books
    active = st.session_state.session_active

    if active:
        selected_book = st.session_state.session_book
        st.info(f"Sesión en curso: **{selected_book}**")
    else:
        options = list(books) + [ADD_NEW]
        choice = st.selectbox("Seleccionar libro:", options)
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
                        st.warning("Ingrese un título válido.")
            return
        selected_book = choice
        st.session_state.selected_book = choice

    info = books[selected_book]
    page_key = f"current_page_{selected_book}"
    st.session_state.setdefault(page_key, int(info["current_page"]))

    col1, col2 = st.columns(2)
    with col1:
        st.number_input("Página actual / punto de partida", 0, int(info["total_pages"]),
                        step=1, key=page_key, disabled=active)
        if not active and int(st.session_state[page_key]) != info["current_page"]:
            info["current_page"] = int(st.session_state[page_key])
            save_data()
    with col2:
        progress = info["current_page"] / info["total_pages"]
        st.metric("Progreso general", f"{progress * 100:.1f}%")
        st.progress(progress, text=f"Página {info['current_page']} de {info['total_pages']}")

    st.divider()
    st.subheader("Ambiente Sonoro")
    labels = list(AMBIENCE.values())
    current = st.session_state.ambience if st.session_state.ambience in labels else "Silencio"
    choice = st.radio("Seleccionar ambiente:", labels, index=labels.index(current), horizontal=True)
    if choice != st.session_state.ambience:
        st.session_state.ambience = choice
        send("ambience", value=AMBIENCE_CMD[choice])
    audio_file = AUDIO_FILES.get(AMBIENCE_CMD[choice])
    if audio_file and not os.path.exists(audio_file):
        st.caption(f"Nota: Agregue el archivo '{audio_file}' al directorio para reproducir el audio localmente.")

    st.divider()
    st.subheader("Control de Sesión")
    if not active:
        st.write("Inicie la sesión desde la aplicación o mediante el dispositivo físico.")
        st.button("Iniciar sesión", type="primary", on_click=cb_start)
        return

    paused = st.session_state.session_paused
    st.fragment(_timer_view, run_every=None if paused else 1)()

    if paused:
        st.button("Reanudar", on_click=resume_reading)
    else:
        st.button("Pausar", on_click=pause_reading)

    if st.session_state.pending_device_finish:
        st.warning("El dispositivo físico ha solicitado finalizar la sesión. Indique la última página leída.")

    start = int(st.session_state.session_start_page)
    total = int(books[st.session_state.session_book]["total_pages"])
    st.session_state.setdefault("final_page", min(max(start, info["current_page"]), total))
    st.number_input("Página final alcanzada", start, total, step=1, key="final_page")
    st.text_area("Reflexión de lectura (opcional)", key="final_comment")
    st.button("Finalizar y guardar", type="primary", on_click=cb_finish)


def page_diary():
    st.title("Diario y Analítica")
    tab_diary, tab_vocab, tab_sent, tab_quotes = st.tabs(
        ["Registro", "Vocabulario", "Sentimientos", "Citas"])

    df = time_df()

    with tab_diary:
        if df.empty:
            st.info("No hay sesiones registradas actualmente.")
        else:
            st.subheader("Tiempo invertido por libro")
            pivot = df.pivot_table(index="fecha", columns="libro", values="minutos",
                                   aggfunc="sum", fill_value=0)
            st.bar_chart(pivot)
            raw = pd.DataFrame(st.session_state.time_log).sort_values("fecha", ascending=False)
            st.dataframe(raw.head(50), width="stretch")
            st.download_button("Exportar registros (CSV)", raw.to_csv(index=False).encode("utf-8"),
                               "margen_sesiones.csv", "text/csv")

        days = set(df["fecha"].dt.date)
        c1, c2, c3 = st.columns(3)
        c1.metric("Horas acumuladas", f"{df['minutos'].sum() / 60:.1f} h")
        c2.metric("Páginas totales", int(df['paginas_leidas'].sum()))
        c3.metric("Días activos", len(days))

        st.subheader("Detalle bibliográfico")
        title = st.selectbox("Seleccionar libro", list(st.session_state.books), key="diary_book")
        data = st.session_state.books[title]
        st.progress(data["current_page"] / data["total_pages"],
                    text=f"{data['current_page']}/{data['total_pages']} páginas")
        st.caption(f"Estimación para finalizar: {estimate_remaining(title, df)}")
        st.slider(f"Calificación", 1, 5, int(data["rating"]),
                  key=f"rating_{title}", on_change=cb_rating, args=(title,))
        st.text_area("Reseña personal", data["review"], key=f"review_{title}",
                     on_change=cb_review, args=(title,))
        sessions = [s for s in st.session_state.time_log if s["libro"] == title]
        if sessions:
            st.dataframe(pd.DataFrame(sessions), width="stretch")

    with tab_vocab:
        st.subheader("Glosario de Vocabulario")
        with st.form("vocab_form", clear_on_submit=True):
            word = st.text_input("Añadir término nuevo").strip()
            if st.form_submit_button("Agregar término") and word:
                if word not in st.session_state.vocab_list:
                    st.session_state.vocab_list.append(word)
                    save_data()
                    st.rerun()
                else:
                    st.info("El término ya se encuentra registrado.")
                    
        cloud = " ".join(
            f"<span style='font-size:{14 + sum(map(ord, w)) % 15}px;margin:6px;color:#1A365D;"
            f"font-weight:500;display:inline-block;background:#E2E8F0;padding:4px 10px;border-radius:15px;'>{html.escape(w)}</span>"
            for w in st.session_state.vocab_list
        )
        st.markdown(f"<div style='padding:20px;background:#F8FAFC;border:1px solid #E2E8F0;border-radius:8px;"
                    f"text-align:center;'>{cloud}</div>", unsafe_allow_html=True)
        
        if st.session_state.vocab_list:
            to_remove = st.selectbox("Eliminar término", [""] + st.session_state.vocab_list)
            if to_remove and st.button("Eliminar"):
                st.session_state.vocab_list.remove(to_remove)
                save_data()
                st.rerun()

    with tab_sent:
        st.subheader("Análisis de Sentimientos")
        st.caption("Evaluación automática basada en procesamiento de texto.")
        test = st.text_area("Evaluar fragmento", key="sent_test")
        if st.button("Analizar texto") and test.strip():
            st.info(f"Polaridad estimada: {analyze_sentiment(test)}")

        log = st.session_state.feedback_log
        if log:
            st.bar_chart(pd.Series([i["sentimiento"] for i in log]).value_counts())
            for item in reversed(log[-10:]):
                with st.container(border=True):
                    st.markdown(f"**{item['libro']}** — {item['fecha']}")
                    st.write(item["comentario"])
                    st.caption(f"Sentimiento: {item['sentimiento']}")
        else:
            st.info("No hay reflexiones registradas.")

    with tab_quotes:
        st.subheader("Citas Destacadas")
        with st.form("quote_form", clear_on_submit=True):
            book = st.selectbox("Libro de referencia", list(st.session_state.books))
            page = st.number_input("Número de página", min_value=0, value=0)
            quote = st.text_area("Cita textual")
            if st.form_submit_button("Guardar cita") and quote.strip():
                st.session_state.quotes.append({"libro": book, "pagina": int(page),
                                                "cita": quote.strip(), "fecha": str(date.today())})
                save_data()
                st.rerun()
        for q in reversed(st.session_state.quotes):
            with st.container(border=True):
                st.markdown(f"> *{q['cita']}*")
                st.caption(f"{q['libro']} · pág. {q['pagina']} · {q['fecha']}")


def page_device():
    st.title("Dispositivo Wokwi / Hardware")
    st.code(f"Comandos (App → ESP32): {TOPIC_COMMANDS}\nEventos (ESP32 → App): {TOPIC_EVENTS}")

    st.subheader("Control manual de órdenes")
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

    st.subheader("Registro de eventos en tiempo real")
    if st.button("Limpiar registros"):
        st.session_state.device_events = []
    events = st.session_state.device_events
    if events:
        for item in reversed(events[-10:]):
            st.write(f"**{item['hora']}** · `{json.dumps(item['mensaje'], ensure_ascii=False)}`")
    else:
        st.info("Sin eventos recientes recibidos desde el hardware.")

    with st.expander("Especificación del protocolo"):
        st.markdown(
            "Estructura JSON intercambiada entre la aplicación Streamlit y el nodo ESP32 mediante MQTT."
        )


# ============================================================
# AUDIO AMBIENTAL
# ============================================================
def ambience_player():
    cmd = AMBIENCE_CMD.get(st.session_state.ambience)
    audio_file = AUDIO_FILES.get(cmd)
    if audio_file and os.path.exists(audio_file):
        st.audio(audio_file, loop=True, autoplay=True)


# ============================================================
# NAVEGACIÓN Y MENÚ LATERAL
# ============================================================
st.sidebar.title("MARGEN")
st.sidebar.caption("Asistente multimodal")
menu = st.sidebar.radio("Navegación", PAGES)
st.sidebar.markdown("---")
with st.sidebar:
    device_sync()

{PAGES[0]: page_home, PAGES[1]: page_library, PAGES[2]: page_diary, PAGES[3]: page_device}[menu]()

with st.sidebar:
    ambience_player()
