"""Dibujos (SVG) y estilos de la barra lateral, las pestañas y los botones."""
import base64

# Colores de los Buffalo Bills
BILLS_AZUL = "#00338D"
BILLS_ROJO = "#C60C30"

# Monigote con la camiseta de los Bills y casco, tomando apuntes (el lápiz se mueve)
_MONIGOTE_SVG = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 170 180">
  <ellipse cx="82" cy="170" rx="52" ry="6" fill="rgba(0,0,0,0.30)"/>
  <!-- balón en el suelo -->
  <g transform="rotate(-18 136 160)">
    <ellipse cx="136" cy="160" rx="16" ry="9" fill="#8B4513" stroke="#5A2D0C" stroke-width="1.5"/>
    <path d="M128 160 H144 M131 157 V163 M135 157 V163 M139 157 V163" stroke="#FFFFFF" stroke-width="1.8"/>
  </g>
  <!-- piernas musculosas: muslo y gemelo (pantalón blanco), medias azules y botas -->
  <ellipse cx="71" cy="130" rx="9" ry="16" transform="rotate(10 71 130)" fill="#FFFFFF"/>
  <ellipse cx="89" cy="130" rx="9" ry="16" transform="rotate(-10 89 130)" fill="#FFFFFF"/>
  <path d="M69 142 L66 161 M91 142 L94 161" stroke="#FFFFFF" stroke-width="8" stroke-linecap="round"/>
  <ellipse cx="67" cy="149" rx="6" ry="7" fill="#FFFFFF"/>
  <ellipse cx="93" cy="149" rx="6" ry="7" fill="#FFFFFF"/>
  <path d="M67 153 L66 161 M93 153 L94 161" stroke="{BILLS_AZUL}" stroke-width="8" stroke-linecap="round"/>
  <path d="M58 165 L71 165 M89 165 L102 165" stroke="#1A2233" stroke-width="7" stroke-linecap="round"/>
  <!-- coraza (hombreras) por debajo de la camiseta -->
  <path d="M47 76 Q48 62 64 61 L96 61 Q112 62 113 76 Q106 82 98 80 L62 80 Q54 82 47 76 Z" fill="#C9CED6"/>
  <!-- camiseta sobre la coraza: hombros anchos -->
  <path d="M50 74 Q52 63 66 62 Q80 58 94 62 Q108 63 110 74 L104 79 Q97 76 93 78 L93 116 L67 116
           L67 78 Q63 76 56 79 Z" fill="{BILLS_AZUL}"/>
  <path d="M52 72 Q57 66 66 66 M108 72 Q103 66 94 66" stroke="{BILLS_ROJO}" stroke-width="3.5"
        fill="none" stroke-linecap="round"/>
  <path d="M72 62 L80 69 L88 62" stroke="{BILLS_ROJO}" stroke-width="3" fill="none" stroke-linejoin="round"/>
  <path d="M50 79 Q55 83 60 80 M110 79 Q105 83 100 80" stroke="#9AA1AC" stroke-width="2" fill="none"/>
  <!-- brazo izquierdo: hombro → codo → mano bajo la libreta (bíceps sobre el tramo superior) -->
  <path d="M54 76 L48 96 L63 104" stroke="#F2C9A0" stroke-width="9" stroke-linecap="round"
        stroke-linejoin="round" fill="none"/>
  <ellipse cx="51" cy="86" rx="6.5" ry="9" transform="rotate(17 51 86)" fill="#F2C9A0"/>
  <!-- libreta pequeña, inclinada hacia él (página en perspectiva + canto de la tapa) -->
  <path d="M62 86 L85 82 L88 101 L65 106 Z" fill="#FFFFFF" stroke="#C9CED6"/>
  <path d="M65 106 L88 101 L88 104 L65 109 Z" fill="#2D3748"/>
  <path d="M66 91 L83 88 M67 95 L84 92 M67 99 L79 97" stroke="#9AA1AC" stroke-width="1.6"/>
  <g fill="none" stroke="#7F8794" stroke-width="1.4">
    <circle cx="67" cy="85" r="1.8"/><circle cx="73" cy="84" r="1.8"/><circle cx="79" cy="83" r="1.8"/>
  </g>
  <circle cx="63" cy="104" r="5" fill="#F2C9A0"/>
  <!-- brazo derecho escribiendo: gira un poco desde el hombro, así nunca se separa -->
  <g>
    <animateTransform attributeName="transform" type="rotate"
                      values="0 106 76; -4 106 76; 1 106 76; 0 106 76" dur="1.2s" repeatCount="indefinite"/>
    <path d="M106 76 L112 94 L88 95" stroke="#F2C9A0" stroke-width="9" stroke-linecap="round"
          stroke-linejoin="round" fill="none"/>
    <ellipse cx="109" cy="85" rx="6.5" ry="9" transform="rotate(-17 109 85)" fill="#F2C9A0"/>
    <path d="M90 88 L78 97" stroke="#F4B400" stroke-width="4.5" stroke-linecap="round"/>
    <path d="M78 97 L75 99" stroke="#1A2233" stroke-width="2.5" stroke-linecap="round"/>
    <circle cx="86" cy="94" r="5" fill="#F2C9A0"/>
  </g>
  <!-- mangas: tapan la unión del brazo con el hombro -->
  <g fill="{BILLS_AZUL}">
    <ellipse cx="54" cy="77" rx="8.5" ry="7" transform="rotate(20 54 77)"/>
    <ellipse cx="106" cy="77" rx="8.5" ry="7" transform="rotate(-20 106 77)"/>
  </g>
  <path d="M47 80 Q52 85 59 82 M113 80 Q108 85 101 82" stroke="{BILLS_ROJO}" stroke-width="2" fill="none"/>
  <g font-size="7" font-weight="800" fill="#FFFFFF" font-family="sans-serif" text-anchor="middle">
    <text x="53" y="79">17</text><text x="107" y="79">17</text>
  </g>
  <!-- casco: la cabeza mira hacia la libreta -->
  <g transform="rotate(-8 80 62)">
    <circle cx="80" cy="40" r="22" fill="#FFFFFF" stroke="#C9CED6" stroke-width="1.5"/>
    <rect x="77" y="18" width="6" height="14" rx="2" fill="{BILLS_ROJO}"/>
    <rect x="79" y="18" width="2" height="14" fill="{BILLS_AZUL}"/>
    <ellipse cx="80" cy="47" rx="13" ry="12" fill="#F2C9A0"/>
    <circle cx="75" cy="48" r="2" fill="#1A2233"/>
    <circle cx="85" cy="48" r="2" fill="#1A2233"/>
    <path d="M73 45 h4 M83 45 h4" stroke="#1A2233" stroke-width="1.3" stroke-linecap="round"/>
    <path d="M77 53 Q80 54.5 83 53" stroke="#1A2233" stroke-width="1.5" fill="none" stroke-linecap="round"/>
    <circle cx="60" cy="45" r="3" fill="#C9CED6"/>
    <circle cx="100" cy="45" r="3" fill="#C9CED6"/>
    <path d="M63 50 Q80 64 97 50 M65 56 Q80 66 95 56 M80 54 V62" stroke="{BILLS_AZUL}" stroke-width="2.6"
          fill="none" stroke-linecap="round"/>
  </g>
</svg>"""
MONIGOTE = (
    '<img alt="Monigote tomando apuntes" style="width:100%;max-width:200px;display:block;margin:0 auto" '
    f'src="data:image/svg+xml;base64,{base64.b64encode(_MONIGOTE_SVG.encode()).decode()}">'
    '<div class="fx-side-caption">Tomando apuntes de tu liga…</div>'
)

# Sirena de emergencia animada (sustituye al emoji 🚨 en el informe)
_SIRENA_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <radialGradient id="g" cx="40%" cy="35%" r="70%">
      <stop offset="0%" stop-color="#FF9A9E"/><stop offset="55%" stop-color="#E5252A"/><stop offset="100%" stop-color="#8E0E12"/>
    </radialGradient>
  </defs>
  <g stroke="#FFD23F" stroke-width="3.5" stroke-linecap="round">
    <animate attributeName="opacity" values="1;0.15;1" dur="0.9s" repeatCount="indefinite"/>
    <path d="M32 3 V10 M11 12 L16 17 M53 12 L48 17 M3 31 H10 M61 31 H54"/>
  </g>
  <path d="M17 46 V31 A15 15 0 0 1 47 31 V46 Z" fill="url(#g)">
    <animate attributeName="opacity" values="1;0.75;1" dur="0.9s" repeatCount="indefinite"/>
  </path>
  <ellipse cx="25" cy="30" rx="3.5" ry="7" fill="#FFFFFF" opacity="0.55"/>
  <rect x="12" y="45" width="40" height="7" rx="2" fill="#4A5568"/>
  <rect x="8" y="52" width="48" height="7" rx="2.5" fill="#2D3748"/>
</svg>"""
SIRENA = (f'<img alt="Alerta" style="height:1.3em;vertical-align:-0.25em" '
          f'src="data:image/svg+xml;base64,{base64.b64encode(_SIRENA_SVG.encode()).decode()}">')

# Balón para el botón de actualizar: puntas afiladas, cuero con brillo, franjas blancas y cordones
_BALON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <defs>
    <radialGradient id="cuero" cx="38%" cy="32%" r="75%">
      <stop offset="0%" stop-color="#C8743A"/><stop offset="60%" stop-color="#8B4513"/><stop offset="100%" stop-color="#4E260A"/>
    </radialGradient>
  </defs>
  <g transform="rotate(-35 32 32)">
    <ellipse cx="33" cy="35" rx="27" ry="15" fill="rgba(0,0,0,0.25)"/>
    <path d="M4 32 Q32 2 60 32 Q32 62 4 32 Z" fill="url(#cuero)" stroke="#3B1C06" stroke-width="1.5"/>
    <path d="M15 21 Q20 32 15 43 M49 21 Q44 32 49 43" stroke="#FFFFFF" stroke-width="3" fill="none" stroke-linecap="round"/>
    <path d="M22 32 H42" stroke="#FFFFFF" stroke-width="2.4" stroke-linecap="round"/>
    <path d="M25 28.5 V35.5 M29 28.5 V35.5 M33 28.5 V35.5 M37 28.5 V35.5 M41 29.5 V34.5" stroke="#FFFFFF"
          stroke-width="2" stroke-linecap="round"/>
    <path d="M14 26 Q24 14 38 13" stroke="rgba(255,255,255,0.35)" stroke-width="2.5" fill="none" stroke-linecap="round"/>
  </g>
</svg>"""
_BALON = f"data:image/svg+xml;base64,{base64.b64encode(_BALON_SVG.encode()).decode()}"

def campo_animado(team, texto="Claude está analizando tu semana"):
    """Campo de fútbol americano con el balón rodando hacia la zona de anotación (mientras Claude analiza)."""
    numeros = "".join(f"<span>{n}</span>" for n in (10, 20, 30, 40, 50, 40, 30, 20, 10))
    return f"""<div class="fx-field-wrap">
  <div class="fx-field">
    <div class="fx-endzone left"><span>{team}</span></div>
    <div class="fx-yards">{numeros}</div>
    <div class="fx-endzone right"><span>TOUCHDOWN</span></div>
    <div class="fx-first-down"></div>
    <div class="fx-ball-run"><div class="fx-ball-hop"><img class="fx-ball" src="{_BALON}" alt="Balón"></div></div>
  </div>
  <div class="fx-field-text">🏈 Avanzando yardas… {texto}<span class="fx-dots-anim"></span></div>
</div>"""


# Ajustes para móvil: se aplican solo en pantallas estrechas. Se cargan los últimos para que manden.
MOBILE_CSS = """
<style>
@media (max-width: 640px) {
    /* Página: menos margen lateral */
    [data-testid="stMainBlockContainer"], .block-container {
        padding-left: 0.6rem !important; padding-right: 0.6rem !important; padding-top: 1rem !important;
    }

    /* Cabecera del equipo: todo apilado y los tres recuadros en una fila */
    .fx-hero { padding: 14px; gap: 12px; margin-bottom: 20px; }
    .fx-hero img, .fx-hero .fx-avatar { width: 54px; height: 54px; }
    .fx-hero-main .fx-team { font-size: 1.5rem; }
    .fx-hero-main .fx-kicker { font-size: 0.68rem; }
    .fx-stats { width: 100%; display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
    .fx-stat { min-width: 0; padding: 8px 4px; }
    .fx-stat .fx-num { font-size: 1.15rem; }
    .fx-stat .fx-lbl, .fx-stat .fx-sub { font-size: 0.6rem; }
    .fx-stat .fx-thumb { font-size: 1.1rem; }

    /* Cuadro de pestañas: las pestañas en una fila que se desliza con el dedo */
    [data-testid="stTabs"] { padding: 10px 6px 12px; border-radius: 16px; }
    [data-baseweb="tab-list"] { flex-wrap: nowrap !important; overflow-x: auto !important; scrollbar-width: none; padding-left: 4px; }
    [data-baseweb="tab-list"]::-webkit-scrollbar { display: none; }
    [data-baseweb="tab"] { padding: 9px 14px; flex-shrink: 0; }
    [data-baseweb="tab"][aria-selected="true"] { padding: 12px 16px 10px; }
    [data-baseweb="tab"] p { font-size: 0.9rem; }
    [data-baseweb="tab"][aria-selected="true"] p { font-size: 0.95rem; }
    [data-baseweb="tab-panel"] { padding: 12px 8px !important; }

    /* Botones */
    .stButton > button[kind="primary"] p { font-size: 1.05rem; }

    /* Tablas: letra más pequeña y desplazamiento lateral si no caben */
    table.fx-table, [data-testid="stMarkdownContainer"] table { font-size: 0.8rem; }
    table.fx-table th, table.fx-table td,
    [data-testid="stMarkdownContainer"] th, [data-testid="stMarkdownContainer"] td { padding: 7px 8px; }
    .fx-section table { display: block; overflow-x: auto; }
    .fx-standings th:nth-child(6), .fx-standings td:nth-child(6),
    .fx-standings th:nth-child(8), .fx-standings td:nth-child(8) { display: none; }

    /* Informe */
    .fx-report-title { padding: 14px; gap: 12px; }
    .fx-report-icon { width: 46px; height: 46px; font-size: 1.5rem; }
    .fx-report-main { font-size: 1.6rem; }
    .fx-rt-info { order: 3; flex-basis: 100%; justify-content: space-between; padding: 10px 0 0;
                  border-left: none; border-right: none; border-top: 1px solid rgba(255, 255, 255, 0.2); }
    .fx-rt-value { font-size: 1.1rem; }
    .fx-report-date { padding: 6px 10px; }
    .fx-section { padding: 4px 12px 10px; }

    /* Enfrentamiento */
    .fx-vs-side { padding: 12px 4px; }
    .fx-vs-side img, .fx-vs-noav { width: 46px; height: 46px; }
    .fx-vs-team { font-size: 0.95rem; }
    .fx-vs-mgr, .fx-vs-rec { font-size: 0.68rem; }
    .fx-vs-score { font-size: 1.7rem; }
    .fx-vs-badge { width: 44px; height: 44px; font-size: 1.05rem; border-width: 3px; }
    .fx-vs-week { font-size: 0.5rem; }
    .fx-cmp { grid-template-columns: 58px 1fr 58px; gap: 6px; }
    .fx-cmp-val { font-size: 0.95rem; } .fx-cmp-val.win { font-size: 1.05rem; }
    .fx-duels td { padding: 6px 5px; font-size: 0.75rem; }
    .fx-duels .fx-d-pts { font-size: 0.85rem; }
    .fx-duels .fx-d-slot { font-size: 0.55rem; }

    /* Mercado de waivers */
    .fx-market { padding: 10px; }
    .fx-mk-title { font-size: 1.1rem; flex-basis: 100%; }
    .fx-mk-chip { flex: 1 1 40%; font-size: 0.72rem; }
    .fx-mk-table { font-size: 0.75rem; }
    .fx-mk-table td { padding: 7px 6px; }
    .fx-bar { width: 60px; }

    /* Mi equipo */
    .fx-cards { grid-template-columns: 1fr; }
    .fx-summary { grid-template-columns: repeat(2, 1fr); gap: 8px; }
    .fx-summary b { font-size: 1.2rem; }

    /* Campo animado */
    .fx-field { height: 100px; }
    .fx-endzone span { font-size: 0.55rem; }
    .fx-yards { font-size: 0.7rem; }
    .fx-ball-run { top: 30px; width: 34px; height: 34px; }
    .fx-ball { width: 34px; height: 34px; }

    /* Acceso de invitados */
    .fx-login-title { font-size: 1.8rem; }

    /* Selector de sección */
    .st-key-modo [role="radiogroup"] { gap: 8px; }
    .st-key-modo [role="radiogroup"] > label { flex: 1 1 40%; padding: 10px 8px; }
    .st-key-modo [role="radiogroup"] > label p { font-size: 1rem; }
}
</style>
"""


SIDEBAR_CSS = """
<style>
[data-testid="stSidebar"] { border-right: 1px solid rgba(255, 255, 255, 0.08); }
.fx-brand { display: flex; align-items: center; gap: 12px; padding: 6px 0 18px; }
.fx-brand .fx-logo {
    width: 48px; height: 48px; border-radius: 14px; font-size: 1.7rem;
    display: flex; align-items: center; justify-content: center;
    background: #2C4066; border: 1px solid rgba(255, 255, 255, 0.12);
}
.fx-brand .fx-name { font-size: 1.25rem; font-weight: 800; line-height: 1.1; }
.fx-brand .fx-tag { font-size: 0.75rem; opacity: 0.75; letter-spacing: 0.06em; text-transform: uppercase; }
.fx-league-card {
    background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 14px; padding: 12px 14px; margin: 14px 0 18px;
}
.fx-league-card .fx-row { display: flex; justify-content: space-between; padding: 4px 0; font-size: 0.9rem; }
.fx-league-card .fx-row span:first-child { opacity: 0.7; }
.fx-league-card .fx-row span:last-child { font-weight: 700; text-align: right; }
/* Botón "Actualizar datos": verde césped, compacto, balón a la izquierda y un destello que lo recorre */
@keyframes fx-destello { 0% { left: -60%; } 55%, 100% { left: 130%; } }
[data-testid="stSidebar"] .stButton > button {
    position: relative; overflow: hidden; width: 100%; min-height: 42px; padding: 7px 14px 7px 50px;
    border: 2px solid rgba(255, 255, 255, 0.85) !important; border-radius: 999px !important;
    background: url("BALON") no-repeat 12px center / 30px 30px,
                linear-gradient(135deg, #3FA66B 0%, #23784A 55%, #145232 100%) !important;
    box-shadow: 0 4px 12px rgba(20, 82, 50, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.35);
    transition: transform 0.15s ease, filter 0.15s ease;
}
[data-testid="stSidebar"] .stButton > button::after {
    content: ""; position: absolute; top: 0; left: -60%; width: 40%; height: 100%;
    background: linear-gradient(100deg, transparent, rgba(255, 255, 255, 0.35), transparent);
    animation: fx-destello 3.5s ease-in-out infinite;
}
[data-testid="stSidebar"] .stButton > button:hover { transform: translateY(-2px) scale(1.02); filter: brightness(1.12); }
[data-testid="stSidebar"] .stButton > button p {
    font-family: 'Oswald', sans-serif; font-size: 0.98rem; font-weight: 600;
    letter-spacing: 0.1em; text-transform: uppercase; text-shadow: 0 1px 3px rgba(0, 0, 0, 0.4);
}
.fx-updated { text-align: center; font-size: 0.78rem; opacity: 0.75; margin: 6px 0 14px; }
/* Selector de equipo: cada opción es una tarjeta; la elegida en rojo */
[data-testid="stSidebar"] [data-testid="stRadio"] > label p {
    font-size: 0.75rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase; opacity: 0.75;
}
[data-testid="stSidebar"] [role="radiogroup"] { gap: 5px; margin: 6px 0 4px; }
[data-testid="stSidebar"] [data-testid="stRadioOption"], [data-testid="stSidebar"] [role="radiogroup"] > label {
    width: 100%; margin: 0; padding: 6px 10px; border-radius: 10px; cursor: pointer; min-height: 0;
    background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.18);
    transition: all 0.15s ease;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:hover { background: rgba(255, 255, 255, 0.13); transform: translateX(3px); }
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) {
    background: linear-gradient(135deg, #B3262A, #6E1316); border-color: rgba(255, 255, 255, 0.6);
    box-shadow: 0 4px 14px rgba(155, 28, 31, 0.5);
}
/* oculta el circulito del radio (el bloque que no contiene texto) */
[data-testid="stSidebar"] [role="radiogroup"] > label > div:not(:has(p)) { display: none; }
[data-testid="stSidebar"] [role="radiogroup"] > label p { font-weight: 700; font-size: 0.92rem; line-height: 1.3; margin: 0; }
/* etiqueta con la posición (1º, 2º...) */
[data-testid="stSidebar"] [role="radiogroup"] > label p span {
    display: inline-block; min-width: 30px; text-align: center; margin-right: 6px; padding: 1px 6px;
    border-radius: 6px; font-size: 0.75rem; background: rgba(255, 255, 255, 0.18) !important;
}
[data-testid="stSidebar"] [role="radiogroup"] > label:has(input:checked) p span { background: rgba(255, 255, 255, 0.3) !important; }
[data-testid="stSidebar"] [data-testid="stRadioCaption"] p,
[data-testid="stSidebar"] [role="radiogroup"] [data-testid="stCaptionContainer"] p {
    font-size: 0.78rem; font-weight: 400; opacity: 0.8;
}
.fx-side-caption { text-align: center; font-size: 0.85rem; font-style: italic; opacity: 0.8; margin-top: 4px; }
</style>
""".replace("BALON", _BALON)

# Pestañas como marcadores de agenda: cada una de un color; la activa queda por encima de las demás.
# El orden coincide con el de st.tabs en app.py.
TAB_COLORS = ["#9B1C1F", "#1F6FB2", "#C98A1A", "#D9480F", "#2E8B57", "#6B4FA0"]

_per_tab = "\n".join(
    f'[data-baseweb="tab"]:nth-of-type({i}) {{ background: {c}; }}\n'
    f'[data-testid="stTabs"]:has([data-baseweb="tab"]:nth-of-type({i})[aria-selected="true"]) '
    f'[data-baseweb="tab-panel"] {{ border-top-color: {c}; }}'
    for i, c in enumerate(TAB_COLORS, start=1)
)

PAGE_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Oswald:wght@500;600&display=swap');

/* Menos hueco en la parte de arriba de la página, para que la cabecera quede más alta */
[data-testid="stMainBlockContainer"], .block-container { padding-top: 1.5rem !important; }

/* Selector principal de sección: Mi Fantasy (rojo) / Partidos NFL (verde azulado y dorado) */
.st-key-modo [role="radiogroup"] { display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 14px; }
.st-key-modo [role="radiogroup"] > label {
    flex: 1 1 220px; margin: 0; padding: 14px 22px; border-radius: 16px; cursor: pointer; justify-content: center;
    border: 2px solid rgba(255, 255, 255, 0.35); background: rgba(255, 255, 255, 0.06);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3); transition: all 0.15s ease; opacity: 0.7;
}
.st-key-modo [role="radiogroup"] > label > div:not(:has(p)) { display: none; }
.st-key-modo [role="radiogroup"] > label p {
    font-family: 'Oswald', sans-serif; font-size: 1.45rem; font-weight: 600; letter-spacing: 0.08em;
    text-transform: uppercase; color: #FFFFFF; text-align: center; margin: 0;
}
.st-key-modo [role="radiogroup"] > label:hover { opacity: 1; transform: translateY(-2px); }
.st-key-modo [role="radiogroup"] > label:nth-of-type(1):has(input:checked) {
    opacity: 1; border-color: #FFFFFF; background: linear-gradient(135deg, #D3343A 0%, #9B1C1F 55%, #5E1013 100%);
    box-shadow: 0 6px 22px rgba(229, 37, 42, 0.55);
}
.st-key-modo [role="radiogroup"] > label:nth-of-type(2):has(input:checked) {
    opacity: 1; border-color: #FFD23F; background: linear-gradient(135deg, #0E7490 0%, #0B4F6C 55%, #062E40 100%);
    box-shadow: 0 6px 22px rgba(255, 210, 63, 0.45);
}
.st-key-modo [role="radiogroup"] > label:nth-of-type(2) { border-color: rgba(255, 210, 63, 0.6); }

/* Sección Partidos NFL: cabecera propia en verde azulado y dorado, distinta del fantasy */
.fx-g-top { background: linear-gradient(120deg, #0B4F6C 0%, #062E40 100%); border: 2px solid #FFD23F;
            border-radius: 16px; padding: 16px 22px; box-shadow: 0 6px 20px rgba(0, 0, 0, 0.35); }
.fx-g-title { color: #FFD23F !important; }

/* Bienvenida: elegir equipo */
.fx-welcome { text-align: center; margin: 2vh 0 22px; }
.fx-welcome-ball { font-size: 3rem; animation: fx-pulse 1.8s ease-in-out infinite; }
.fx-welcome-title { font-family: 'Oswald', sans-serif; font-size: 2.3rem; font-weight: 600; text-transform: uppercase;
                    letter-spacing: 0.05em; color: #FFFFFF; }
.fx-welcome-sub { color: #D6DDE8; font-size: 0.9rem; }
.fx-wc { position: relative; text-align: center; padding: 16px 10px 12px; margin-bottom: 6px; border-radius: 16px;
         background: linear-gradient(160deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.04));
         border: 1px solid rgba(255, 255, 255, 0.22); box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3); }
.fx-wc img, .fx-wc-noav { width: 64px; height: 64px; border-radius: 50%; object-fit: cover; border: 3px solid #FFFFFF;
                          box-shadow: 0 4px 10px rgba(0, 0, 0, 0.4); display: inline-flex; align-items: center;
                          justify-content: center; font-size: 1.8rem; background: rgba(0, 0, 0, 0.3); }
.fx-wc-rank { position: absolute; top: 8px; left: 10px; font-family: 'Oswald', sans-serif; font-size: 0.9rem;
              background: rgba(0, 0, 0, 0.35); padding: 0 8px; border-radius: 999px; color: #FFD23F; }
.fx-wc-name { font-family: 'Oswald', sans-serif; font-size: 1.15rem; color: #FFFFFF; margin-top: 8px;
              white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fx-wc-mgr { color: #A9B6CC; font-size: 0.78rem; }
.fx-wc-rec { display: inline-block; margin-top: 6px; padding: 1px 10px; border-radius: 999px; font-weight: 800;
             font-size: 0.8rem; background: rgba(0, 0, 0, 0.3); color: #FFFFFF; }
/* La tarjeta y su botón forman una sola pieza: la tarjeta arriba y el botón como "pie" pegado debajo */
.fx-wc { border-radius: 16px 16px 0 0; margin-bottom: -16px; border-bottom: none; padding-bottom: 14px; }
[class*="st-key-elegir_"] button {
    width: 100%; min-height: 0; padding: 9px 12px; margin-bottom: 18px;
    border-radius: 0 0 16px 16px !important; border: 1px solid rgba(255, 255, 255, 0.22) !important; border-top: none !important;
    background: linear-gradient(135deg, #D3343A 0%, #9B1C1F 55%, #5E1013 100%) !important;
    box-shadow: 0 6px 16px rgba(0, 0, 0, 0.3); transition: filter 0.15s ease, box-shadow 0.15s ease;
}
[class*="st-key-elegir_"] button p {
    font-family: 'Oswald', sans-serif; font-size: 0.95rem; font-weight: 600; letter-spacing: 0.1em;
    text-transform: uppercase; color: #FFFFFF;
}
[class*="st-key-elegir_"] button p::before { content: "👉 "; }
[class*="st-key-elegir_"] button:hover { filter: brightness(1.15); box-shadow: 0 8px 22px rgba(229, 37, 42, 0.5); }
[class*="st-key-elegir_"] button:focus:not(:active) { border-color: rgba(255, 255, 255, 0.22) !important; }
[data-testid="stSidebar"] .st-key-cambiar_equipo button { min-height: 0 !important; padding: 4px 12px 4px 12px !important; border-radius: 999px !important;
    background: rgba(255, 255, 255, 0.08) !important; border: 1px solid rgba(255, 255, 255, 0.35) !important;
    box-shadow: none !important; }
[data-testid="stSidebar"] .st-key-cambiar_equipo button::after { display: none; }
[data-testid="stSidebar"] .st-key-cambiar_equipo button p { font-family: 'Segoe UI', sans-serif !important; font-size: 0.8rem !important;
    letter-spacing: 0 !important; text-transform: none !important; }

/* Aviso de IR y límite de plantilla */
.fx-ir-alert { background: rgba(236, 72, 153, 0.14); border: 2px solid #EC4899; border-left: 8px solid #EC4899;
               border-radius: 14px; padding: 12px 16px; margin: -16px 0 22px; color: #FFFFFF; line-height: 1.55;
               box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3); }
.fx-ir-alert b { color: #FFD6EC; }
.fx-ir-note { font-size: 0.75rem; opacity: 0.75; margin-top: 4px; }

/* Pantalla de acceso de invitados */
.fx-login { text-align: center; margin: 6vh 0 18px; }
.fx-login-ball { font-size: 3.5rem; animation: fx-pulse 1.8s ease-in-out infinite; }
@keyframes fx-pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }
.fx-login-title { font-family: 'Oswald', sans-serif; font-size: 2.4rem; font-weight: 600; text-transform: uppercase;
                  letter-spacing: 0.06em; color: #FFFFFF; }
.fx-login-sub { color: #D6DDE8; letter-spacing: 0.12em; text-transform: uppercase; font-size: 0.85rem; }
[data-testid="stForm"] { background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.25) !important;
                         border-radius: 16px; padding: 18px 20px; }
.fx-guest-note { background: rgba(255, 255, 255, 0.08); border: 1px dashed rgba(255, 255, 255, 0.35);
                 border-radius: 12px; padding: 10px 14px; font-size: 0.9rem; color: #FFFFFF; }

/* Campo animado mientras Claude analiza */
.fx-field-wrap { margin: 10px 0 6px; }
.fx-field {
    position: relative; height: 130px; border-radius: 12px; overflow: hidden; display: flex;
    border: 3px solid #FFFFFF; box-shadow: 0 6px 18px rgba(0, 0, 0, 0.4);
    background:
        repeating-linear-gradient(90deg, rgba(255, 255, 255, 0.85) 0 2px, transparent 2px 10%),
        repeating-linear-gradient(90deg, #2E8B3E 0 5%, #297F37 5% 10%);
}
.fx-endzone { width: 11%; display: flex; align-items: center; justify-content: center; z-index: 1; }
.fx-endzone.left { background: #9B1C1F; border-right: 3px solid #FFFFFF; }
.fx-endzone.right { background: #1F6FB2; border-left: 3px solid #FFFFFF; }
.fx-endzone span { writing-mode: vertical-rl; transform: rotate(180deg); font-family: 'Oswald', sans-serif;
                   font-weight: 600; letter-spacing: 0.12em; color: #FFFFFF; font-size: 0.85rem; white-space: nowrap; }
.fx-yards { flex: 1; display: flex; justify-content: space-around; align-items: flex-end; padding-bottom: 6px;
            font-family: 'Oswald', sans-serif; font-size: 1.1rem; color: rgba(255, 255, 255, 0.85); }
@keyframes fx-run { 0% { left: 9%; } 90% { left: 86%; } 100% { left: 86%; } }
@keyframes fx-spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
@keyframes fx-hop { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-14px); } }
@keyframes fx-chains { 0% { left: 20%; } 20% { left: 35%; } 40% { left: 50%; } 60% { left: 65%; } 80%, 100% { left: 80%; } }
.fx-ball-run { position: absolute; top: 42px; left: 9%; width: 46px; height: 46px; z-index: 2;
               animation: fx-run 6s cubic-bezier(0.45, 0, 0.55, 1) infinite; }
.fx-ball-hop { animation: fx-hop 0.7s ease-in-out infinite; }
.fx-ball { width: 46px; height: 46px; animation: fx-spin 0.7s linear infinite;
           filter: drop-shadow(0 6px 4px rgba(0, 0, 0, 0.45)); }
.fx-first-down { position: absolute; top: 0; bottom: 0; width: 4px; background: #FFD23F; z-index: 1;
                 box-shadow: 0 0 10px #FFD23F; animation: fx-chains 6s steps(1, end) infinite; }
.fx-field-text { text-align: center; margin-top: 10px; font-weight: 700; color: #FFFFFF; }
@keyframes fx-dots { 0% { content: ""; } 25% { content: "."; } 50% { content: ".."; } 75% { content: "..."; } }
.fx-dots-anim::after { content: ""; animation: fx-dots 1.6s steps(1, end) infinite; }

/* Todo el bloque de pestañas dentro de un gran cuadro con fondo propio */
[data-testid="stTabs"] {
    background: linear-gradient(180deg, #1B2A47 0%, #16223B 100%);
    border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 22px;
    padding: 18px 20px 22px; box-shadow: 0 12px 34px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.08);
}

/* Pestañas tipo marcador de agenda */
[data-baseweb="tab-list"] { gap: 0; padding: 0 0 0 10px; align-items: flex-end; flex-wrap: wrap; overflow: visible; }
[data-baseweb="tab-highlight"], [data-baseweb="tab-border"] { display: none; }
[data-baseweb="tab"] {
    height: auto; margin: 0 -6px 0 0; padding: 13px 30px; position: relative; z-index: 1; cursor: pointer;
    border-radius: 14px 14px 0 0 !important;
    border: 2px solid rgba(255, 255, 255, 0.55) !important; border-bottom: none !important;
    box-shadow: 3px -2px 6px rgba(0, 0, 0, 0.25); transition: all 0.15s ease;
    /* oscurece el color de fondo de las no activas sin apagar el contorno */
    background-image: linear-gradient(rgba(0, 0, 0, 0.38), rgba(0, 0, 0, 0.38)) !important;
}
[data-baseweb="tab"]:hover {
    transform: translateY(-3px);
    background-image: linear-gradient(rgba(0, 0, 0, 0.15), rgba(0, 0, 0, 0.15)) !important;
}
[data-baseweb="tab"][aria-selected="true"] {
    background-image: none !important;
    z-index: 3; transform: none; padding: 18px 36px 15px; border-color: #FFFFFF !important;
    box-shadow: 0 -4px 14px rgba(0, 0, 0, 0.35);
}
[data-baseweb="tab"] p {
    font-size: 1.2rem; font-weight: 700; color: #FFFFFF; letter-spacing: 0.02em;
    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.45);
}
[data-baseweb="tab"][aria-selected="true"] p { font-size: 1.3rem; }
[data-baseweb="tab-panel"] {
    position: relative; z-index: 2; margin-top: 0; padding: 22px !important;
    background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.10);
    border-top: 5px solid #9B1C1F; border-radius: 0 16px 16px 16px;
}
PER_TAB

/* Botón principal (Analizar mi semana): degradado, borde blanco y brillo que late */
@keyframes fx-latido {
    0%, 100% { box-shadow: 0 6px 18px rgba(155, 28, 31, 0.45), inset 0 1px 0 rgba(255, 255, 255, 0.35); }
    50% { box-shadow: 0 6px 30px rgba(229, 37, 42, 0.85), inset 0 1px 0 rgba(255, 255, 255, 0.35); }
}
.stButton > button[kind="primary"] {
    padding: 11px 22px; border-radius: 14px !important;
    background: linear-gradient(135deg, #D3343A 0%, #9B1C1F 55%, #5E1013 100%) !important;
    border: 2px solid rgba(255, 255, 255, 0.85) !important;
    animation: fx-latido 2.4s ease-in-out infinite; transition: transform 0.15s ease;
}
.stButton > button[kind="primary"]:hover { transform: translateY(-3px) scale(1.02); filter: brightness(1.1); }
.stButton > button[kind="primary"]:active { transform: translateY(0) scale(0.99); }
.stButton > button[kind="primary"] p {
    font-family: 'Oswald', sans-serif; font-size: 1.2rem; font-weight: 600;
    letter-spacing: 0.1em; text-transform: uppercase; text-shadow: 0 2px 4px rgba(0, 0, 0, 0.4);
}

/* Botones para plegar/desplegar la barra lateral: bien visibles */
[data-testid="stExpandSidebarButton"], [data-testid="stSidebarCollapseButton"] button {
    background: #9B1C1F !important; border: 2px solid #FFFFFF !important; border-radius: 10px !important;
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.4); opacity: 1 !important; visibility: visible !important;
}
[data-testid="stExpandSidebarButton"] *, [data-testid="stSidebarCollapseButton"] * {
    color: #FFFFFF !important; fill: #FFFFFF !important;
}
[data-testid="stExpandSidebarButton"]:hover, [data-testid="stSidebarCollapseButton"] button:hover {
    filter: brightness(1.2);
}

/* Cartel del título del informe: [icono + SEMANA] | [equipo · liga] | [fecha] */
.fx-report-title {
    display: flex; align-items: center; justify-content: space-between; gap: 24px; flex-wrap: wrap;
    padding: 20px 28px; margin: 18px 0 22px; border-radius: 16px;
    background: linear-gradient(120deg, #1F2D44 0%, #3A1A2A 100%);
    border: 1px solid rgba(255, 255, 255, 0.22); box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
}
.fx-rt-left { display: flex; align-items: center; gap: 18px; }
.fx-rt-info {
    flex: 1; display: flex; justify-content: space-evenly; gap: 28px; flex-wrap: wrap;
    padding: 4px 28px; border-left: 1px solid rgba(255, 255, 255, 0.2); border-right: 1px solid rgba(255, 255, 255, 0.2);
}
.fx-rt-label {
    color: #D6DDE8; font-size: 0.7rem; font-weight: 700; letter-spacing: 0.14em; text-transform: uppercase;
    margin-bottom: 2px;
}
.fx-rt-value {
    font-family: 'Oswald', sans-serif; font-size: 1.6rem; font-weight: 500; line-height: 1.15; color: #FFFFFF;
}
.fx-report-icon {
    width: 64px; height: 64px; border-radius: 14px; font-size: 2.2rem;
    display: flex; align-items: center; justify-content: center;
    background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.18);
}
.fx-report-kicker {
    display: inline-block; background: #9B1C1F; color: #FFFFFF; border-radius: 999px; padding: 3px 12px;
    font-size: 0.7rem; font-weight: 800; letter-spacing: 0.14em; text-transform: uppercase;
}
.fx-report-main {
    font-family: 'Oswald', sans-serif; font-size: 2.3rem; font-weight: 600; line-height: 1.1;
    text-transform: uppercase; letter-spacing: 0.04em; color: #FFFFFF; margin-top: 6px;
}
.fx-report-date {
    display: flex; flex-direction: column; align-items: center; padding: 10px 16px; border-radius: 12px;
    background: rgba(255, 255, 255, 0.08); border: 1px solid rgba(255, 255, 255, 0.15); color: #D6DDE8;
}
.fx-report-date b { color: #FFFFFF; font-family: 'Oswald', sans-serif; font-size: 1.25rem; font-weight: 500; }
.fx-report-date span { font-size: 0.85rem; }
</style>
""".replace("PER_TAB", _per_tab)
