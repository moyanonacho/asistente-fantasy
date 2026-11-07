"""Asistente de Fantasy NFL — página principal.

Arrancar con:  .venv\\Scripts\\streamlit run app.py
"""
import hmac
import html
import os
import re
from datetime import datetime

import markdown
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

import analisis
import fuentes
import ilustraciones
import partidos
import proyecciones
import sleeper
import vistas
import waivers

load_dotenv()
# En Streamlit Cloud no hay .env: la configuración llega por los "Secrets" de la app
try:
    for _k, _v in st.secrets.items():
        if isinstance(_v, (str, int, float)):
            os.environ.setdefault(_k, str(_v))
except Exception:
    pass
st.set_page_config(page_title="Asistente Fantasy NFL", page_icon="🏈", layout="wide")

INJURY_ICON = {"Out": "🔴", "IR": "🔴", "PUP": "🔴", "Sus": "🔴", "Doubtful": "🟠", "Questionable": "🟡"}

# Colores de la página. Se fuerzan aquí además de en .streamlit/config.toml para que
# no los pise el tema que el navegador tenga guardado.
COLORS = {
    "fondo": "#2C4066",          # azul medio
    "lateral": "#1F2D44",        # azul oscuro suave
    "texto": "#FFFFFF",
    "texto_suave": "#D6DDE8",    # textos secundarios
    "rojo": "#9B1C1F",           # botones y pestaña activa
    "tabla_cabecera": "#9AA1AC", # gris medio
    "tabla_fondo": "#E9ECF0",    # gris clarito
    "tabla_texto": "#1A2233",
}
st.markdown("""
<style>
.stApp, [data-testid="stHeader"] { background-color: %(fondo)s; }
[data-testid="stSidebar"], [data-testid="stSidebar"] > div { background-color: %(lateral)s; }

/* Textos en blanco sobre los fondos azules (las tablas mantienen su propio color) */
.stApp, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp p, .stApp li, .stApp label,
[data-testid="stMetricValue"], [data-testid="stMetricLabel"] p, [data-baseweb="tab"] p,
[data-testid="stSidebar"] * { color: %(texto)s; }
[data-testid="stCaptionContainer"], [data-testid="stCaptionContainer"] p { color: %(texto_suave)s; }
.stApp a { color: #9CC3FF; }

/* Fondos translúcidos para que el texto blanco se lea en avisos, cuadros y botones */
[data-testid="stAlertContainer"] { background-color: rgba(255, 255, 255, 0.12); }
[data-testid="stExpander"] details, [data-testid="stExpander"] summary { background-color: rgba(255, 255, 255, 0.06); }
.stButton > button { background-color: transparent; }

/* Botones */
.stButton > button { border-color: %(rojo)s; }
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] {
    background-color: %(rojo)s; border-color: %(rojo)s; color: #FFFFFF;
}
.stButton > button:hover { border-color: #7A1518; filter: brightness(1.1); }

/* Cabecera */
.fx-hero {
    display: flex; align-items: center; gap: 20px; flex-wrap: wrap;
    padding: 22px 26px; margin-bottom: 36px; border-radius: 16px;
    background: linear-gradient(120deg, %(lateral)s 0%%, #3A1A2A 100%%);
    border: 1px solid rgba(255, 255, 255, 0.12); box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
}
.fx-hero img { width: 72px; height: 72px; border-radius: 50%%; border: 3px solid %(rojo)s; object-fit: cover; }
.fx-hero .fx-avatar { width: 72px; height: 72px; border-radius: 50%%; background: %(rojo)s;
    display: flex; align-items: center; justify-content: center; font-size: 2rem; }
.fx-hero-main { flex: 1; min-width: 200px; }
.fx-hero-main .fx-kicker { color: %(texto_suave)s; font-size: 0.85rem; letter-spacing: 0.08em; text-transform: uppercase; }
.fx-hero-main .fx-team { color: #FFFFFF; font-size: 2.1rem; font-weight: 800; line-height: 1.15; }
.fx-hero-main .fx-vs { color: %(texto_suave)s; margin-top: 4px; }
.fx-stats { display: flex; gap: 12px; flex-wrap: wrap; }
.fx-stat {
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.24), rgba(255, 255, 255, 0.12));
    border: 1px solid rgba(255, 255, 255, 0.35); border-top: 3px solid #E5252A; border-radius: 12px;
    padding: 10px 18px; text-align: center; min-width: 110px; box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35);
}
.fx-stat .fx-num { color: #FFFFFF; font-size: 1.5rem; font-weight: 800; }
.fx-stat .fx-lbl { color: %(texto_suave)s; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.06em; }
.fx-stat .fx-sub { color: %(texto_suave)s; font-size: 0.78rem; min-height: 1em; }
.fx-stat .fx-thumb { font-size: 1.4rem; line-height: 1.2; }
.fx-stat .fx-po-in { color: #7CE38B; font-weight: 600; }
.fx-stat .fx-po-out { color: #FF8A8A; font-weight: 600; }

/* Botón y ventana de Fuentes */
[data-testid="stPopover"] button {
    background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.30); border-radius: 10px;
}
[data-testid="stPopover"] button:hover { background: rgba(255, 255, 255, 0.16); border-color: %(rojo)s; }
[data-testid="stPopoverBody"] { background: %(lateral)s; border: 1px solid rgba(255, 255, 255, 0.15); }
[data-testid="stPopoverBody"] * { color: %(texto)s; }
[data-testid="stPopoverBody"] a { color: #9CC3FF; }

/* Tablas (las nuestras y las del informe de Claude) */
.fx-wrap { overflow-x: auto; margin-bottom: 1.2rem; padding: 2px; }
table.fx-table, [data-testid="stMarkdownContainer"] table {
    width: 100%%; border-collapse: separate; border-spacing: 0; background: %(tabla_fondo)s; color: %(tabla_texto)s;
    border-radius: 12px; overflow: hidden; font-size: 0.92rem;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.28); border: 1px solid #7F8794;
}
table.fx-table th, [data-testid="stMarkdownContainer"] th {
    background: linear-gradient(180deg, #A9B0BA, %(tabla_cabecera)s); color: %(tabla_texto)s; text-align: left;
    font-size: 0.74rem; font-weight: 800; text-transform: uppercase; letter-spacing: 0.07em;
    padding: 11px 14px; border: none; border-right: 1px solid #7F8794; border-bottom: 2px solid #6F7784;
}
table.fx-table td, [data-testid="stMarkdownContainer"] td {
    padding: 9px 14px; border: none; border-bottom: 1px solid #D3D8DF; border-right: 1px solid #C3C9D2;
    color: %(tabla_texto)s; transition: background 0.12s ease;
}
table.fx-table tbody tr:nth-child(even) td, [data-testid="stMarkdownContainer"] tbody tr:nth-child(even) td {
    background: #F4F6F9;
}
table.fx-table tbody tr:last-child td, [data-testid="stMarkdownContainer"] tbody tr:last-child td { border-bottom: none; }
table.fx-table th:last-child, table.fx-table td:last-child,
[data-testid="stMarkdownContainer"] th:last-child, [data-testid="stMarkdownContainer"] td:last-child { border-right: none; }
table.fx-table tbody tr:hover td, [data-testid="stMarkdownContainer"] tbody tr:hover td { background: #D9E2EE; }
table.fx-table td:first-child, [data-testid="stMarkdownContainer"] td:first-child { font-weight: 700; }
[data-testid="stMarkdownContainer"] td strong, [data-testid="stMarkdownContainer"] td a { color: %(tabla_texto)s; }

/* Secciones del informe como tarjetas con contorno */
.fx-section {
    background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.22);
    border-left: 6px solid var(--acento, %(rojo)s); border-radius: 14px;
    padding: 6px 22px 14px; margin-bottom: 20px; box-shadow: 0 6px 18px rgba(0, 0, 0, 0.22);
}
.fx-section h1, .fx-section h2, .fx-section h3 {
    padding-bottom: 8px; margin-bottom: 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.15);
}
.fx-section.fx-intro { border-left-color: #FFFFFF; background: rgba(255, 255, 255, 0.08); }
</style>
""" % COLORS, unsafe_allow_html=True)


def show_table(rows, where=st):
    """Pinta una lista de filas como tabla blanca."""
    html = pd.DataFrame(rows).to_html(index=False, classes="fx-table", border=0, float_format="{:.2f}".format)
    where.markdown(f'<div class="fx-wrap">{html}</div>', unsafe_allow_html=True)


# Color del borde izquierdo de cada sección del informe, según su título
SECTION_COLORS = {"Tus opiniones": "#8B5CF6", "IR y límite": "#EC4899", "Alertas": "#E5252A", "Alineación": "#2E8B57", "Waivers": "#C98A1A", "Opiniones": "#1F6FB2"}


def render_report(text, made, week, team, league_name):
    """Pinta el informe de Claude: cartel de título y cada sección (### ...) en una tarjeta con contorno."""
    # El cartel se construye con los datos del equipo, igual para todos; el título "# ..." de Claude se descarta
    title_match = re.match(r"\s*# .+\n", text)
    if title_match:
        text = text[title_match.end():]
    st.markdown(f"""
<div class="fx-report-title">
  <div class="fx-rt-left">
    <div class="fx-report-icon">📋</div>
    <div>
      <span class="fx-report-kicker">Informe Fantasy</span>
      <div class="fx-report-main">Semana {week}</div>
    </div>
  </div>
  <div class="fx-rt-info">
    <div><div class="fx-rt-label">Equipo</div><div class="fx-rt-value">{html.escape(team)}</div></div>
    <div><div class="fx-rt-label">Liga</div><div class="fx-rt-value">{html.escape(league_name)}</div></div>
  </div>
  <div class="fx-report-date">
    <div class="fx-rt-label">Generado</div><b>{made:%d/%m/%Y}</b><span>{made:%H:%M} h</span>
  </div>
</div>""", unsafe_allow_html=True)
    for i, section in enumerate(re.split(r"(?m)^(?=#{2,3} )", text)):
        if not section.strip() or section.strip() == "---":
            continue
        body = markdown.markdown(section.strip().removesuffix("---"), extensions=["tables"])
        body = re.sub(r"\n\s*\n", "\n", body)  # sin líneas en blanco, para que Streamlit no corte el HTML
        title = section.splitlines()[0]
        color = next((c for k, c in SECTION_COLORS.items() if k in title), None)
        css_class = "fx-section fx-intro" if i == 0 and not section.startswith("##") else "fx-section"
        style = f' style="--acento: {color}"' if color else ""
        st.markdown(f'<div class="{css_class}"{style}>{body}</div>', unsafe_allow_html=True)


@st.cache_data(ttl=600)
def load_league_data(username, league_id):
    """Descarga todo lo necesario de Sleeper (se guarda 10 minutos en memoria)."""
    user = sleeper.get_user(username)
    state = sleeper.get_state()
    league = sleeper.get_league(league_id)
    last_done = league["settings"].get("last_scored_leg") or state["week"] - 1
    return {
        "user": user,
        "state": state,
        "league": league,
        "rosters": sleeper.get_rosters(league_id),
        "users": sleeper.get_users(league_id),
        "matchups": sleeper.get_matchups(league_id, state["week"]),
        # resultados de las jornadas ya jugadas, para la clasificación con movimientos
        "history": {wk: sleeper.get_matchups(league_id, wk) for wk in range(1, last_done + 1)},
        "last_done": last_done,
        "trending": sleeper.get_trending("add"),
        "drops": {t["player_id"]: t["count"] for t in sleeper.get_trending("drop", limit=200)},
        "fetched_at": datetime.now(),
    }


@st.cache_data(ttl=600)
def load_games(season, week):
    """Partidos NFL de la jornada (ESPN), refrescados cada 10 minutos para seguir los resultados."""
    return partidos.week_games(season, week)


@st.cache_data(ttl=3 * 3600)
def load_team_stats(season, games):
    return partidos.all_team_stats(season, games)


@st.cache_data(ttl=24 * 3600)
def load_team_colors():
    return partidos.team_colors()


@st.cache_data(ttl=1800)
def load_projections(season, week):
    """Proyecciones de la semana de Sleeper (cada 30 minutos)."""
    return sleeper.get_projections(season, week)


@st.cache_data(ttl=3 * 3600)
def load_stats(season, last_week):
    """Estadísticas reales de cada jornada jugada de todos los jugadores, también los libres (cada 3 horas)."""
    return {wk: sleeper.get_stats(season, wk) for wk in range(1, last_week + 1)}


@st.cache_data(ttl=3 * 3600)
def load_fpi(season):
    return partidos.fpi(season)


@st.cache_data(ttl=600)
def load_summaries(games):
    """Predicción ESPN, lesiones y líderes de cada partido (cada 10 minutos, por las lesiones de última hora)."""
    return partidos.all_summaries(games)


@st.cache_data(ttl=3600)
def load_players():
    return sleeper.get_players()


def team_name(users, owner_id):
    u = next((u for u in users if u["user_id"] == owner_id), None)
    if not u:
        return "Sin dueño"
    return (u.get("metadata") or {}).get("team_name") or u["display_name"]


def avatar_of(user):
    """URL del avatar del equipo (o del usuario) en Sleeper, o None."""
    return (user.get("metadata") or {}).get("avatar") or (
        f"https://sleepercdn.com/avatars/thumbs/{user['avatar']}" if user.get("avatar") else None)


def player_row(players, pid, slot=None, on_ir=frozenset()):
    """Fila de tabla de un jugador. `on_ir`: jugadores colocados en huecos de lesionados (IR)."""
    p = players.get(pid, {})
    status = p.get("injury_status") or ""
    name = p.get("full_name") or pid
    row = {
        "Jugador": f"🏥 {name}" if status == "IR" or pid in on_ir else name,
        "Pos": p.get("position", ""),
        "Equipo": p.get("team") or "FA",
        "Estado": f"{INJURY_ICON.get(status, '')} {status}".strip(),
        "Lesión": p.get("injury_body_part") or "",
    }
    if slot:
        row = {"Hueco": slot, **row}
    return row


# --- Barra lateral -----------------------------------------------------------
st.markdown(ilustraciones.SIDEBAR_CSS + ilustraciones.PAGE_CSS + vistas.CSS + ilustraciones.MOBILE_CSS,
            unsafe_allow_html=True)

# --- Modo invitado -------------------------------------------------------------
# Quien entra desde este PC (localhost) es el dueño. Quien llega por el enlace compartido (túnel de
# Cloudflare, que añade sus cabeceras) o desde otro equipo es invitado: necesita contraseña y no puede
# lanzar análisis (que gastarían la suscripción de Claude del dueño).
headers = {k.lower() for k in st.context.headers.keys()}
host = (st.context.headers.get("host") or "localhost").split(":")[0].lower()
client_ip = getattr(st.context, "ip_address", None)
is_guest = (bool(headers & {"cf-connecting-ip", "cf-ray"})
            or host not in ("localhost", "127.0.0.1", "[::1]")
            or client_ip not in (None, "127.0.0.1", "::1"))

if is_guest and not st.session_state.get("guest_ok"):
    st.markdown("""<div class="fx-login">
  <div class="fx-login-ball">🏈</div>
  <div class="fx-login-title">Asistente Fantasy</div>
  <div class="fx-login-sub">Acceso para invitados</div>
</div>""", unsafe_allow_html=True)
    _, col, _ = st.columns([1, 2, 1])
    with col.form("login"):
        password = st.text_input("Contraseña", type="password")
        if st.form_submit_button("Entrar", type="primary", width="stretch"):
            st.session_state["login_attempts"] = st.session_state.get("login_attempts", 0) + 1
            expected = os.getenv("GUEST_PASSWORD", "")
            if st.session_state["login_attempts"] > 10:
                st.error("Demasiados intentos. Cierra la página y vuelve a intentarlo más tarde.")
            elif expected and hmac.compare_digest(password, expected):
                st.session_state["guest_ok"] = True
                st.rerun()
            else:
                st.error("Contraseña incorrecta")
    st.stop()
st.sidebar.markdown("""
<div class="fx-brand">
  <div class="fx-logo">🏈</div>
  <div><div class="fx-name">Asistente Fantasy</div><div class="fx-tag">NFL · Temporada en curso</div></div>
</div>
""", unsafe_allow_html=True)
username = os.getenv("SLEEPER_USERNAME", "")
league_id = os.getenv("SLEEPER_LEAGUE_ID", "")
if not username or not league_id:
    st.error("Falta SLEEPER_USERNAME o SLEEPER_LEAGUE_ID en el archivo .env")
    st.stop()
if st.sidebar.button("Actualizar datos"):
    st.cache_data.clear()
# Resultado de la publicación automática tras un análisis o pronóstico
if "publicado" in st.session_state:
    ok, msg = st.session_state.pop("publicado")
    if ok:
        st.toast("🌐 Publicado en la web pública: aparecerá en 1-2 minutos", icon="✅")
    else:
        st.toast(f"No se ha podido publicar ({msg}). Usa publicar.bat.", icon="⚠️", duration="long")

with st.spinner("Descargando datos de Sleeper..."):
    data = load_league_data(username, league_id)
    players = load_players()

league, rosters, users = data["league"], data["rosters"], data["users"]
week = data["state"]["week"]
st.sidebar.markdown(f'<div class="fx-updated">🕒 Datos actualizados a las {data["fetched_at"]:%H:%M}</div>',
                    unsafe_allow_html=True)

# Equipos que se pueden consultar: el mío y los de SLEEPER_EQUIPOS_EXTRA
# (usuarios separados por comas, o "todos" para toda la liga), ordenados por clasificación
my_user_id = data["user"]["user_id"]
extra = os.getenv("SLEEPER_EQUIPOS_EXTRA", "").strip().lower()
extra_names = {n.strip() for n in extra.split(",") if n.strip()}
ranked_owners = [r["owner_id"] for r in sorted(
    rosters, key=lambda r: (r["settings"]["wins"], r["settings"].get("fpts", 0)), reverse=True)]
visible_ids = [uid for uid in ranked_owners if uid and (
    uid == my_user_id or extra == "todos"
    or next((u["display_name"].lower() for u in users if u["user_id"] == uid), "") in extra_names)]
MODO_FANTASY, MODO_NFL = "🏈 Mi Fantasy", "🏟️ Partidos NFL"

# "Mi equipo" de quien está mirando: se elige en la pantalla de bienvenida y se recuerda en la dirección
# de la página (?equipo=6), así al recargar o guardar el enlace se entra directamente en ese equipo.
uid_by_rid = {r["roster_id"]: r["owner_id"] for r in rosters}
rid_by_uid = {uid: rid for rid, uid in uid_by_rid.items()}
if "mi_equipo" not in st.session_state:
    chosen = st.query_params.get("equipo", "")
    if chosen.isdigit() and uid_by_rid.get(int(chosen)) in visible_ids:
        st.session_state["mi_equipo"] = st.session_state["equipo"] = uid_by_rid[int(chosen)]
home_uid = st.session_state.get("mi_equipo")


def choose_team(uid):
    st.session_state["mi_equipo"] = st.session_state["equipo"] = uid
    st.session_state["modo"] = MODO_FANTASY
    st.query_params["equipo"] = str(rid_by_uid[uid])


def forget_team():
    st.session_state.pop("mi_equipo", None)
    st.query_params.pop("equipo", None)


team_ids = ([home_uid] if home_uid else []) + [uid for uid in visible_ids if uid != home_uid]
owner_id = st.sidebar.radio(
    "Equipo", team_ids, key="equipo",
    disabled=st.session_state.get("modo") == MODO_NFL,  # el selector de equipo solo sirve para el fantasy
    # una sola línea por equipo: posición en una etiqueta + nombre (el manager ya sale en la cabecera)
    format_func=lambda uid: (f":gray-background[{ranked_owners.index(uid) + 1}º] "
                             + ("⭐ " if uid == home_uid else "") + team_name(users, uid).strip()),
)
if home_uid:
    st.sidebar.button("🔁 Cambiar mi equipo", on_click=forget_team, key="cambiar_equipo")
# `mine` es la plantilla del equipo seleccionado (el mío o el de otro manager)
mine = next(r for r in rosters if r["owner_id"] == owner_id)

st.sidebar.markdown(f"""
<div class="fx-league-card">
  <div class="fx-row"><span>Liga</span><span>{html.escape(league['name'])}</span></div>
  <div class="fx-row"><span>Plataforma</span><span>Sleeper</span></div>
  <div class="fx-row"><span>Temporada</span><span>{league['season']}</span></div>
  <div class="fx-row"><span>Semana</span><span>{week}</span></div>
</div>
""", unsafe_allow_html=True)
st.sidebar.markdown(ilustraciones.MONIGOTE, unsafe_allow_html=True)

# --- Bienvenida: ¿de qué equipo eres mánager? ----------------------------------
if not home_uid:
    st.markdown(f"""<div class="fx-welcome">
  <div class="fx-welcome-ball">🏈</div>
  <div class="fx-welcome-title">¿De qué equipo eres mánager?</div>
  <div class="fx-welcome-sub">{html.escape(league['name'])} · Semana {week} · elige tu equipo para entrar directamente en él</div>
</div>""", unsafe_allow_html=True)
    user_by_id = {u["user_id"]: u for u in users}
    for start in range(0, len(visible_ids), 4):
        cols = st.columns(4)
        for col, uid in zip(cols, visible_ids[start:start + 4]):
            user = user_by_id.get(uid, {})
            roster = next(r for r in rosters if r["owner_id"] == uid)
            avatar = avatar_of(user) if user else None
            img = f'<img src="{html.escape(avatar)}">' if avatar else '<span class="fx-wc-noav">🏈</span>'
            with col:
                st.markdown(f"""<div class="fx-wc">
  <div class="fx-wc-rank">{ranked_owners.index(uid) + 1}º</div>{img}
  <div class="fx-wc-name">{html.escape(team_name(users, uid).strip())}</div>
  <div class="fx-wc-mgr">{html.escape(user.get('display_name', ''))}</div>
  <div class="fx-wc-rec">{roster['settings']['wins']}-{roster['settings']['losses']}</div>
</div>""", unsafe_allow_html=True)
                st.button("Soy este mánager", key=f"elegir_{uid}", on_click=choose_team, args=(uid,),
                          width="stretch")
    st.caption("Tu elección se guarda en la dirección de la página: si la guardas en favoritos, la próxima vez "
               "entrarás directamente en tu equipo. Desde la barra lateral puedes ver los demás equipos.")
    st.stop()

# --- Sección: Mi Fantasy o Partidos NFL ---------------------------------------
modo = st.radio("Sección", [MODO_FANTASY, MODO_NFL], horizontal=True, key="modo", label_visibility="collapsed")

if modo == MODO_NFL:
    # Partidos NFL de la jornada: análisis aparte del fantasy
    nfl_season = int(league["season"])
    try:
        games, byes = load_games(nfl_season, week)
        team_stats = load_team_stats(nfl_season, games)
        fpi_data = load_fpi(nfl_season)
        summaries = load_summaries(games)
    except Exception as e:
        st.error(f"No se han podido descargar los datos de ESPN: {e}")
        st.stop()
    picks_made, picks = partidos.load_picks(nfl_season, week)

    if not is_guest:
        g1, _ = st.columns([3, 5])
        if g1.button("🔮 Pronosticar la jornada", type="primary", width="stretch"):
            with st.status("Analizando los partidos de la jornada...", expanded=True) as status:
                st.write("📺 Buscando los vídeos de esta semana de TRENDZONE (Mundo NFL) y 100Yardas...")
                transcripts = fuentes.nfl_week_videos()
                for t in transcripts:
                    st.write(f"   ✓ {t['source']}: «{t['title']}» ({t['published']:%d/%m})")
                if not transcripts:
                    st.write("   · Todavía no hay vídeos de esta semana; se analizará sin ellos")
                st.write(f"🧠 Claude está revisando {len(games)} partidos: estadísticas avanzadas, lesiones y "
                         "pronósticos de CBS Sports (5-8 minutos)...")
                field = st.empty()
                field.markdown(ilustraciones.campo_animado("NFL", "Claude está analizando los partidos"),
                               unsafe_allow_html=True)
                try:
                    prompt = partidos.build_prompt(nfl_season, week, games, team_stats, fpi_data, summaries, transcripts)
                    new_picks = partidos.parse_picks(analisis.run_claude(prompt, timeout_min=15))
                except Exception as e:
                    field.empty()
                    status.update(label="Algo ha fallado", state="error")
                    st.error(f"No se ha podido completar el pronóstico: {e}")
                    st.stop()
                field.empty()
                partidos.save_picks(nfl_season, week, new_picks)
                st.write("🌐 Publicando en la web pública...")
                st.session_state["publicado"] = analisis.publish(f"Pronósticos semana {week}")
                status.update(label=f"¡{len(new_picks)} partidos pronosticados!", state="complete", expanded=False)
            st.rerun()
    if picks_made:
        st.caption(f"Pronósticos generados el {picks_made:%d/%m/%Y a las %H:%M}. "
                   "Los resultados y lesiones se actualizan solos cada 10 minutos.")
    elif is_guest:
        st.info("Todavía no hay pronósticos para esta jornada.")
    else:
        st.info("Todavía no hay pronósticos para esta jornada. Pulsa «Pronosticar la jornada» para generarlos.")
    st.markdown(vistas.render_games(week, games, byes, team_stats, picks, fpi_data, summaries,
                                    partidos.strengths_weaknesses), unsafe_allow_html=True)
    st.caption("Los pronósticos son estimaciones a partir de estadísticas y opiniones; no garantizan resultados. "
               "Vídeos usados: el de PICKS de TRENDZONE y los de los viernes de 100Yardas de la semana en curso.")
    st.stop()

# --- Cabecera ----------------------------------------------------------------
s = mine["settings"]
standings = sorted(rosters, key=lambda r: (r["settings"]["wins"], r["settings"].get("fpts", 0)), reverse=True)
rank = standings.index(mine) + 1

slots = [pos for pos in league["roster_positions"] if pos != "BN"]

# Clasificación calculada con los resultados: tras la última jornada jugada y tras la anterior
season = vistas.season_table(rosters, data["history"], data["last_done"])
season_prev = vistas.season_table(rosters, data["history"], data["last_done"] - 1) if data["last_done"] > 1 else None
weekly = vistas.weekly_points(data["history"])  # puntos de cada jugador por jornada
health = analisis.roster_health(league, mine, players, weekly)  # IR y límite de plantilla

# Rival de esta semana
by_roster = {m["roster_id"]: m for m in data["matchups"]}
my_m = by_roster.get(mine["roster_id"])
rival_m = next((m for m in data["matchups"] if my_m and m["matchup_id"] == my_m["matchup_id"]
                and m["roster_id"] != mine["roster_id"]), None)
rival_roster = next((r for r in rosters if rival_m and r["roster_id"] == rival_m["roster_id"]), None)

me = next(u for u in users if u["user_id"] == owner_id)
avatar_url = avatar_of(me)
avatar = f'<img src="{html.escape(avatar_url)}">' if avatar_url else '<div class="fx-avatar">🏈</div>'
vs = f"Semana {week} · vs <b>{html.escape(team_name(users, rival_roster['owner_id']))}</b>" if rival_roster else f"Semana {week}"
thumb = "👍" if s["wins"] > s["losses"] else "👎" if s["wins"] < s["losses"] else "🤝"
playoff_teams = league["settings"].get("playoff_teams", 0)
in_playoffs = rank <= playoff_teams
weeks_left = max(league["settings"].get("playoff_week_start", week) - week, 0)
stats = [
    ("Récord", f"{s['wins']}-{s['losses']}" + (f"-{s['ties']}" if s.get("ties") else ""),
     f'<span class="fx-thumb">{thumb}</span>'),
    ("Posición", f"{rank}º/{len(rosters)}",
     f'<span class="fx-po-{"in" if in_playoffs else "out"}">'
     f'{"✅ En playoffs" if in_playoffs else "❌ Fuera de playoffs"}</span>'),
    ("Jornadas restantes", weeks_left, "hasta playoffs"),
]
st.markdown(f"""
<div class="fx-hero">
  {avatar}
  <div class="fx-hero-main">
    <div class="fx-kicker">{html.escape(league['name'])} · {league['season']} · Manager: {html.escape(me['display_name'])}</div>
    <div class="fx-team">{html.escape(team_name(users, owner_id))}</div>
    <div class="fx-vs">{vs}</div>
  </div>
  <div class="fx-stats">
    {''.join(f'<div class="fx-stat"><div class="fx-lbl">{k}</div><div class="fx-num">{v}</div>'
             f'<div class="fx-sub">{sub}</div></div>' for k, v, sub in stats)}
  </div>
</div>
""", unsafe_allow_html=True)

# Aviso de IR: jugadores que ya no pueden estar en IR o plantilla por encima del límite
if health["ir_ineligible"] or health["excess"] > 0:
    pname = lambda pid: html.escape(players.get(pid, {}).get("full_name") or pid)
    parts = []
    if health["ir_ineligible"]:
        parts.append("Ya no pueden estar en IR: " + ", ".join(
            f"<b>{pname(p)}</b> ({health['status'][p] or 'sin lesión'})" for p in health["ir_ineligible"])
            + ". Sleeper te obliga a activarlos antes de hacer otros movimientos.")
    if health["excess"] > 0:
        parts.append(f"Al activarlos tendrás <b>{health['active'] + len(health['ir_ineligible'])} jugadores para "
                     f"{health['capacity']} huecos</b>: sobran <b>{health['excess']}</b>.")
        options = []
        if health["ir_candidates"] and health["free_ir_after"] > 0:
            options.append("pasar al IR a " + ", ".join(
                f"<b>{pname(p)}</b> ({health['status'][p]})" for p in health["ir_candidates"]))
        if health["cut_candidates"]:
            options.append("cortar al suplente de menos rendimiento: " + ", ".join(
                f"<b>{pname(p)}</b> (media {health['values'][p]['avg']:.1f})" for p in health["cut_candidates"][:3]))
        if options:
            parts.append("Opciones: " + "; o ".join(options) + ".")
    st.markdown(f'<div class="fx-ir-alert">🏥 <b>IR y límite de plantilla</b><br>{"<br>".join(parts)}'
                f'<div class="fx-ir-note">El estado de lesión puede tener unas horas de retraso: confírmalo en Sleeper.</div>'
                f'</div>', unsafe_allow_html=True)

# Agentes libres en tendencia que se pueden alinear en esta liga
rostered ={pid for r in rosters for pid in (r["players"] or [])}
usable = analisis.usable_positions(league["roster_positions"])
free_agents = [(t["player_id"], t["count"]) for t in data["trending"]
               if t["player_id"] not in rostered
               and usable & set(players.get(t["player_id"], {}).get("fantasy_positions") or [])]

# Proyecciones de la semana y estado de cada partido NFL, para Enfrentamiento y Matchups
try:
    projections = load_projections(int(league["season"]), week)
    games_by_team = proyecciones.game_by_team(load_games(int(league["season"]), week)[0])
except Exception:
    projections, games_by_team = {}, {}
# Waivers a medida: valor real de todos los jugadores (también los libres) con la puntuación de la liga
try:
    weekly_all = waivers.weekly_from_stats(load_stats(int(league["season"]), data["last_done"]),
                                           league["scoring_settings"])
except Exception:
    weekly_all = {}
fa_pool = waivers.free_agent_pool(players, rosters, usable, weekly_all, projections, league["scoring_settings"],
                                  adds=dict(free_agents)) if weekly_all else []
needs = waivers.team_needs(league, mine, rosters, players, weekly_all, fa_pool) if weekly_all else []
try:
    team_colors_nfl = load_team_colors()
except Exception:
    team_colors_nfl = {}  # sin colores, las camisetas salen en gris


def matchup_side(roster, matchup):
    """Un lado de un enfrentamiento: datos del equipo, temporada y proyección de la semana."""
    user = next((u for u in users if u["user_id"] == roster["owner_id"]), {"display_name": "", "user_id": None})
    outlook = proyecciones.team_outlook(matchup["starters"], slots, matchup.get("players_points") or {},
                                        projections, players, league["scoring_settings"], games_by_team)
    return {"team": team_name(users, roster["owner_id"]).strip(), "manager": user["display_name"],
            "avatar": avatar_of(user), "matchup": matchup, "stats": season[roster["roster_id"]],
            "outlook": outlook, "roster_id": roster["roster_id"]}


tab_ai, tab_team, tab_matchup, tab_matchups, tab_waivers, tab_league = st.tabs(
    ["🧠 Recomendaciones", "👤 Mi equipo", "⚔️ Enfrentamiento", "💣 Matchups", "📈 Waivers", "🏆 Clasificación"])

# --- Recomendaciones con Claude ----------------------------------------------
with tab_ai:
    last = analisis.latest(week, mine["roster_id"])
    report_body, report_sources = "", ""
    if last:
        # El informe termina con la sección de fuentes: la separamos para mostrarla en un desplegable
        parts = re.split(r"^#{1,4}\s*📚.*$", last.read_text(encoding="utf-8"), maxsplit=1, flags=re.M)
        report_body = (parts[0]
                       .replace("🚨", ilustraciones.SIRENA)
                       # títulos de informes antiguos
                       .replace("🔄 Waivers", "📈 Waivers")
                       .replace("Lo que dicen los analistas", "Opiniones de los expertos"))
        report_sources = parts[1].strip() if len(parts) > 1 else ""

    if not is_guest:
        # Opiniones del manager: se guardan por equipo y Claude las examina en el próximo análisis
        notes_key = f"notes_{mine['roster_id']}"
        if notes_key not in st.session_state:
            st.session_state[notes_key] = analisis.load_notes(mine["roster_id"])
        saved_notes = st.session_state[notes_key]
        with st.expander("📝 Tus opiniones para el análisis" + (" · ✍️ hay notas guardadas" if saved_notes.strip() else ""),
                         expanded=bool(saved_notes.strip())):
            st.text_area(
                "Escribe lo que piensas (una idea por línea). Claude comprobará si cada una tiene lógica "
                "con los datos y las noticias: si la tiene, la tendrá en cuenta; si no, te dirá por qué.",
                key=notes_key, height=130,
                placeholder="Ej.: Creo que Tank Dell va a tener un papel mayor ahora que hay lesiones en Houston.\n"
                            "Ej.: Prefiero alinear a Cam Ward en vez de Shough esta semana.\n"
                            "Ej.: He leído a Mr. Fantasy que hay que fichar a Seth McGowan.",
                on_change=lambda k=notes_key, rid=mine["roster_id"]: analisis.save_notes(rid, st.session_state[k]),
            )
            st.caption("Se guardan solas para este equipo. Bórralas cuando ya no apliquen.")

    b1, _ = st.columns([3, 5])
    if is_guest:
        b1.markdown('<div class="fx-guest-note">👀 Modo invitado: puedes leer los informes, '
                    'pero solo el dueño puede generar análisis nuevos.</div>', unsafe_allow_html=True)
    elif b1.button("🔍 Analizar mi semana", type="primary", width="stretch"):
        with st.status("Analizando tu semana...", expanded=True) as status:
            st.write("📺 Descargando transcripciones de los vídeos...")
            transcripts = fuentes.collect()
            for t in transcripts:
                st.write(f"   ✓ {t['source']}: «{t['title']}»")
            st.write("📰 Leyendo noticias de Rotowire...")
            involved = list(dict.fromkeys(
                mine["players"] + (rival_roster["starters"] if rival_roster else []) + [pid for pid, _ in free_agents[:15]]))
            roto_players = fuentes.rotowire_news_for(players, [pid for pid in involved if pid != "0"])
            roto_latest = fuentes.rotowire_latest()
            st.write(f"   ✓ {len(roto_players)} jugadores con noticias y {len(roto_latest)} noticias generales")
            st.write("🧠 Claude está leyendo CBS Sports, buscando más noticias y analizando (2-4 minutos)...")
            context = analisis.build_context(league, mine, rival_roster, players, free_agents, week,
                                             team=team_name(users, owner_id).strip(), manager=me["display_name"],
                                             weekly=weekly)
            if needs:
                context += "\n" + "\n".join(waivers.needs_text(needs, players))
            notes = analisis.load_notes(mine["roster_id"])
            if notes.strip():
                st.write("📝 Incluyendo tus opiniones para que Claude las examine")
            prompt = analisis.build_prompt(context, transcripts, week, players, roto_players, roto_latest, notes)
            field = st.empty()  # campo con el balón rodando mientras Claude trabaja
            field.markdown(ilustraciones.campo_animado(html.escape(team_name(users, owner_id).strip())),
                           unsafe_allow_html=True)
            try:
                report = analisis.run_claude(prompt)
            except Exception as e:
                field.empty()
                status.update(label="Algo ha fallado", state="error")
                st.error(str(e))
                st.stop()
            field.empty()
            analisis.save(report, week, mine["roster_id"])
            st.write("🌐 Publicando en la web pública...")
            st.session_state["publicado"] = analisis.publish(f"Análisis semana {week} · {team_name(users, owner_id).strip()}")
            status.update(label="¡Análisis completado!", state="complete", expanded=False)
        st.rerun()  # recarga para mostrar el informe nuevo con sus fuentes en el desplegable

    if last:
        made = datetime.strptime(last.stem.split("_", 3)[3], "%Y%m%d_%H%M")
        render_report(report_body, made, week, team_name(users, owner_id).strip(), league["name"])
    else:
        st.info(f"Aún no hay análisis de la semana {week}. Pulsa el botón para generar el primero.")

    with st.popover("📚 Fuentes"):
        st.markdown("**Qué consulta el análisis**\n"
                    "- Rotowire: noticias de tus jugadores, del rival y de los waivers\n"
                    "- CBS Sports: artículos de la semana\n"
                    "- Los Fantásticos (Mundo NFL): últimos vídeos\n"
                    "- Búsquedas propias de Claude")
        if report_sources:
            st.markdown("**Consultadas en el último informe**")
            st.markdown(report_sources)

# --- Mi equipo ---------------------------------------------------------------
with tab_team:
    on_ir = frozenset(mine.get("reserve") or [])
    starters = [player_row(players, pid, slot) for slot, pid in zip(slots, mine["starters"]) if pid != "0"]
    bench_ids = [pid for pid in mine["players"] if pid not in mine["starters"]]
    bench = [player_row(players, pid, on_ir=on_ir) for pid in bench_ids]

    flagged = [r for r in starters if r["Estado"]]
    if flagged:
        st.warning("⚠️ Titulares con problemas físicos: " + ", ".join(f"{r['Jugador']} ({r['Estado']})" for r in flagged))
    injured_bench = [r for pid, r in zip(bench_ids, bench) if "🔴" in r["Estado"] and pid not in on_ir]
    if injured_bench:
        st.info("Lesionados ocupando banquillo: " + ", ".join(r["Jugador"] for r in injured_bench))

    # Resumen de la plantilla
    last_game = next((m for m in data["history"].get(data["last_done"], [])
                      if m["roster_id"] == mine["roster_id"]), {})
    games = max(len(season[mine["roster_id"]]["res"]), 1)
    totals = {pid: sum(weekly.get(pid, {}).values()) for pid in mine["players"]}
    top_pid = max(totals, key=totals.get) if totals else None
    tocados = sum(1 for pid in mine["players"] if players.get(pid, {}).get("injury_status"))
    st.markdown(f"""<div class="fx-summary">
  <div><b>{last_game.get('points', 0):.1f}</b><span>Puntos jornada {data['last_done']}</span></div>
  <div><b>{season[mine['roster_id']]['pf'] / games:.1f}</b><span>Media por jornada</span></div>
  <div><b>{html.escape(players.get(top_pid, {}).get('last_name', '—'))}</b><span>Máximo anotador ({totals.get(top_pid, 0):.0f} pts)</span></div>
  <div><b>{tocados}</b><span>Jugadores tocados</span></div>
</div>""", unsafe_allow_html=True)

    st.markdown(vistas.render_roster(mine, slots, players, weekly), unsafe_allow_html=True)

# --- Enfrentamiento de la semana ---------------------------------------------
with tab_matchup:
    if not my_m or not rival_m:
        st.write("No hay enfrentamiento esta semana.")
    else:
        if not projections:
            st.warning("No se han podido cargar las proyecciones de la semana; se muestran solo los puntos actuales.")
        side_a, side_b = matchup_side(mine, my_m), matchup_side(rival_roster, rival_m)
        win_a = proyecciones.win_probability(side_a["outlook"], side_b["outlook"])
        st.markdown(vistas.render_matchup(week, slots, players, side_a, side_b, win_a, team_colors_nfl),
                    unsafe_allow_html=True)

# --- Matchups de toda la liga --------------------------------------------------
with tab_matchups:
    roster_by_id = {r["roster_id"]: r for r in rosters}
    pairs = {}
    for m in data["matchups"]:
        if m.get("matchup_id"):
            pairs.setdefault(m["matchup_id"], []).append(m)
    cards = []
    for mid, pair in sorted(pairs.items()):
        if len(pair) != 2:
            continue
        # El enfrentamiento del equipo seleccionado, primero y con él a la izquierda
        pair.sort(key=lambda m: m["roster_id"] != mine["roster_id"])
        sa, sb = (matchup_side(roster_by_id[m["roster_id"]], m) for m in pair)
        cards.append((mid, sa, sb, proyecciones.win_probability(sa["outlook"], sb["outlook"]),
                      mine["roster_id"] in (pair[0]["roster_id"], pair[1]["roster_id"])))
    cards.sort(key=lambda c: not c[4])
    my_rid_all = rid_by_uid[home_uid]
    st.markdown(vistas.render_league_matchups(week, cards, my_rid_all), unsafe_allow_html=True)
    for mid, sa, sb, win, _ in cards:
        with st.expander(f"⚔️ Duelo completo: {sa['team']} vs {sb['team']}"):
            st.markdown(vistas.render_matchup(week, slots, players, sa, sb, win, team_colors_nfl),
                        unsafe_allow_html=True)

# --- Waivers -----------------------------------------------------------------
with tab_waivers:
    PARA_TI = "🎯 Para tu equipo"
    choice = PARA_TI
    if needs:
        st.markdown(vistas.render_needs(needs, players, team_name(users, owner_id).strip(),
                                        waivers.drop_candidate(mine, players, weekly_all, projections,
                                                               league["scoring_settings"])), unsafe_allow_html=True)
        choice = st.segmented_control("Ver libres", [PARA_TI] + [n["pos"] for n in needs], default=PARA_TI,
                                      key="waiver_pos", label_visibility="collapsed") or PARA_TI
        fa_rows = waivers.with_gain(fa_pool, needs)
        if choice == PARA_TI:
            # Los que más mejoran a tus titulares, como mucho 3 por posición para que haya variedad
            per_pos, picks = {}, []
            for f in sorted((f for f in fa_rows if f["gain"] > 0.3), key=lambda f: -f["gain"]):
                if per_pos.get(f["pos"], 0) < 3:
                    per_pos[f["pos"]] = per_pos.get(f["pos"], 0) + 1
                    picks.append(f)
            st.markdown(vistas.render_free_agents(
                picks[:12], players, "🎯 FICHAJES QUE TE MEJORAN",
                "Libres que superan a tu titular más flojo de su posición, de más a menos mejora"),
                unsafe_allow_html=True)
        else:
            st.markdown(vistas.render_free_agents(
                [f for f in fa_rows if f["pos"] == choice][:15], players, f"MEJORES {choice} LIBRES",
                "Ordenados por valor (media de la temporada y forma reciente)"), unsafe_allow_html=True)
    else:
        st.warning("No se han podido descargar las estadísticas de Sleeper: solo se muestran las tendencias.")
    market = free_agents if choice == PARA_TI else [
        (pid, c) for pid, c in free_agents if waivers.position_of(players.get(pid, {})) == choice]
    st.markdown("")
    if market:
        budget = league["settings"].get("waiver_budget", 0)
        st.markdown(vistas.render_market(
            players, market, data["drops"],
            vistas.next_waiver_run(league["settings"].get("waiver_day_of_week", 2)),
            faab_left=budget - mine["settings"].get("waiver_budget_used", 0), faab_total=budget,
        ), unsafe_allow_html=True)
    else:
        st.write("Ninguno de los jugadores en tendencia" + (f" ({choice})" if choice != PARA_TI else "")
                 + " está libre en tu liga.")

# --- Clasificación -----------------------------------------------------------
with tab_league:
    user_by_id = {u["user_id"]: u for u in users}
    names = {r["roster_id"]: (team_name(users, r["owner_id"]).strip(),
                              user_by_id.get(r["owner_id"], {}).get("display_name", ""),
                              avatar_of(user_by_id[r["owner_id"]]) if r["owner_id"] in user_by_id else None)
             for r in rosters}
    my_rid = rid_by_uid[home_uid]  # el equipo del mánager que está mirando, marcado con ⭐
    st.markdown(vistas.render_standings(season, season_prev, names, playoff_teams, mine["roster_id"], my_rid,
                                        data["last_done"]), unsafe_allow_html=True)
