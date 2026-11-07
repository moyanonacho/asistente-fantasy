"""El "cerebro": prepara toda la información y se la pasa a Claude Code (con tu suscripción)."""
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ANALYSIS_DIR = Path(__file__).parent / "data" / "analisis"
NOTES_DIR = Path(__file__).parent / "data" / "notas"

FLEX_EXPAND = {"FLEX": ["RB", "WR", "TE"], "SUPER_FLEX": ["QB", "RB", "WR", "TE"], "REC_FLEX": ["WR", "TE"],
               "WRRB_FLEX": ["RB", "WR"], "IDP_FLEX": ["DL", "LB", "DB"]}


# Estados que permiten ocupar un hueco de IR: IR y PUP siempre; el resto según la configuración de la liga
IR_ALWAYS = {"IR", "PUP"}
IR_OPTIONAL = {"reserve_allow_out": "Out", "reserve_allow_doubtful": "Doubtful", "reserve_allow_sus": "Sus",
               "reserve_allow_cov": "COV", "reserve_allow_na": "NA", "reserve_allow_dnr": "DNR"}


def ir_eligible_statuses(league):
    s = league["settings"]
    return IR_ALWAYS | {status for key, status in IR_OPTIONAL.items() if s.get(key)}


def player_value(pid, weekly):
    """Rendimiento del jugador: media y media de los 3 últimos partidos contando SOLO los partidos en que puntuó
    (las jornadas con 0 por lesión o descanso no hunden su media), partidos jugados, jornadas y total."""
    weeks = [weekly.get(pid, {})[w] for w in sorted(weekly.get(pid, {}))]
    played = [p for p in weeks if p]
    return {"avg": sum(played) / len(played) if played else 0.0,
            "last3": sum(played[-3:]) / len(played[-3:]) if played else 0.0,
            "games": len(played), "weeks": len(weeks), "total": sum(played)}


def roster_health(league, roster, players, weekly):
    """Situación del IR y del límite de plantilla, y candidatos a cortar ordenados por menor valor."""
    eligible = ir_eligible_statuses(league)
    reserve = list(roster.get("reserve") or [])
    capacity = len(league["roster_positions"])  # titulares + banquillo (el IR va aparte)
    active = [pid for pid in roster["players"] if pid not in reserve]
    status = {pid: players.get(pid, {}).get("injury_status") or "" for pid in roster["players"]}
    ir_ineligible = [pid for pid in reserve if status[pid] not in eligible]
    ir_slots = league["settings"].get("reserve_slots", 0)
    over_now = len(active) - capacity
    # Si se activan los que ya no pueden estar en IR, ¿cuántos jugadores sobran?
    excess = over_now + len(ir_ineligible)
    free_ir_after = ir_slots - (len(reserve) - len(ir_ineligible))
    ir_candidates = [pid for pid in active if status[pid] in eligible]
    starters = set(roster["starters"])
    values = {pid: player_value(pid, weekly) for pid in roster["players"]}
    # Media del jugador frente a los de su misma posición en la plantilla
    by_pos = {}
    for pid in roster["players"]:
        by_pos.setdefault(players.get(pid, {}).get("position", "?"), []).append(values[pid]["avg"])
    cut_candidates = sorted(
        (pid for pid in active if pid not in starters and status[pid] not in eligible),
        key=lambda pid: (values[pid]["avg"], values[pid]["last3"]))
    return {"eligible": sorted(eligible), "capacity": capacity, "active": len(active), "reserve": reserve,
            "ir_slots": ir_slots, "ir_ineligible": ir_ineligible, "over_now": over_now, "excess": excess,
            "free_ir_after": free_ir_after, "ir_candidates": ir_candidates, "values": values,
            "cut_candidates": cut_candidates, "status": status, "pos_avgs": by_pos}


def usable_positions(roster_positions):
    """Posiciones que se pueden alinear en la liga (p. ej. sin DEF si es liga IDP)."""
    return {p for slot in roster_positions for p in FLEX_EXPAND.get(slot, [slot])}


def _describe(players, pid):
    p = players.get(pid, {})
    line = f"{p.get('full_name') or pid} ({p.get('position', '?')}, {p.get('team') or 'FA'})"
    if p.get("injury_status"):
        line += f" — {p['injury_status']}" + (f" ({p['injury_body_part']})" if p.get("injury_body_part") else "")
    return line


def _value_text(v):
    if not v["games"]:
        return "sin puntos registrados en esta liga"
    missed = v["weeks"] - v["games"]
    return (f"media {v['avg']:.1f} pts en {v['games']} partidos jugados"
            + (f" (se perdió {missed} jornada(s))" if missed else "")
            + f", últimos 3 partidos: {v['last3']:.1f}, total {v['total']:.0f}")


def _ir_section(players, health):
    name = lambda pid: players.get(pid, {}).get("full_name") or pid
    lines = ["", "SITUACIÓN DEL IR Y DEL LÍMITE DE PLANTILLA (calculada con los datos de Sleeper):",
             f"- Estados que admite el IR en esta liga: {', '.join(health['eligible'])}. "
             "Questionable o sin lesión NO pueden estar en IR.",
             f"- Huecos activos (titulares + banquillo): {health['capacity']}. Jugadores activos ahora: {health['active']}. "
             f"Huecos de IR: {health['ir_slots']} (ocupados: {len(health['reserve'])})."]
    if health["ir_ineligible"]:
        lines.append("- Jugadores en IR que YA NO son elegibles (Sleeper obliga a activarlos antes de hacer otros "
                     "movimientos): " + ", ".join(f"{name(p)} ({health['status'][p] or 'sano'})"
                                                  for p in health["ir_ineligible"]))
    if health["ir_candidates"]:
        lines.append("- Jugadores activos que SÍ podrían ir al IR (liberan sitio sin cortar a nadie): " +
                     ", ".join(f"{name(p)} ({health['status'][p]})" for p in health["ir_candidates"]))
    lines.append(f"- Tras activar a los no elegibles sobrarían {max(health['excess'], 0)} jugador(es); "
                 f"quedarían {max(health['free_ir_after'], 0)} hueco(s) de IR libres.")
    cuts = health["cut_candidates"][:6]
    if cuts:
        lines.append("- Suplentes sanos con MENOS rendimiento (de menor a mayor media): " +
                     "; ".join(f"{name(p)} ({players.get(p, {}).get('position', '?')}, {_value_text(health['values'][p])})"
                               for p in cuts))
    return lines


def build_context(league, mine, rival, players, free_agents, week, team, manager, weekly=None):
    weekly = weekly or {}
    slots = [s for s in league["roster_positions"] if s != "BN"]
    sc = league["scoring_settings"]
    health = roster_health(league, mine, players, weekly)
    val = lambda pid: _value_text(health["values"][pid])
    lines = [
        f"EQUIPO ANALIZADO: {team} (manager: {manager}).",
        f"LIGA: {league['name']} — Sleeper, temporada {league['season']}, semana {week}.",
        f"Formato: {league['total_rosters']} equipos, {sc.get('rec', 0)} puntos por recepción, "
        f"{sc.get('pass_td', 4)} puntos por TD de pase.",
        f"Huecos titulares: {', '.join(slots)}.",
        f"Huecos de banquillo: {league['roster_positions'].count('BN')}. "
        f"Huecos de lesionados (IR): {league['settings'].get('reserve_slots', 0)}.",
        "",
        "MIS TITULARES ACTUALES (con su rendimiento en las jornadas jugadas):",
        *[f"- {slot}: {_describe(players, pid)} · {val(pid)}"
          for slot, pid in zip(slots, mine["starters"]) if pid != "0"],
        "",
        "MI BANQUILLO:",
        *[f"- {_describe(players, pid)} · {val(pid)}"
          + (" — colocado en hueco de IR" if pid in health["reserve"] else "")
          for pid in mine["players"] if pid not in mine["starters"]],
        *_ir_section(players, health),
    ]
    if rival:
        lines += ["", "TITULARES DEL RIVAL DE ESTA SEMANA:",
                  *[f"- {slot}: {_describe(players, pid)}" for slot, pid in zip(slots, rival["starters"]) if pid != "0"]]
    lines += ["", "AGENTES LIBRES EN MI LIGA MÁS AÑADIDOS EN SLEEPER (últimas 24 h):",
              *[f"- {_describe(players, pid)} — añadido {count} veces · "
                f"{_value_text(player_value(pid, weekly))}" for pid, count in free_agents]]
    return "\n".join(lines)


def _format_news(item, name=None):
    line = f"- **{name or item['player']}** ({item['date']}) — {item['headline']}: {item['news']}"
    if item["analysis"]:
        line += f"\n  Análisis Rotowire: {item['analysis']}"
    return line


def _notes_block(notes):
    """Instrucciones y sección extra del informe cuando el manager ha escrito sus opiniones."""
    if not notes.strip():
        return "", ""
    block = f"""
## Opiniones del manager (escritas por él; pueden ser acertadas o no)
{notes.strip()}

Trátalas como hipótesis, NO como órdenes. Contrasta cada una con los datos de la liga, las noticias,
los vídeos y tus búsquedas. Si una opinión tiene lógica y está respaldada, incorpórala a tus recomendaciones.
Si no la tiene (contradice los datos, se basa en algo desactualizado o es pura intuición sin apoyo),
NO la apliques y explica por qué con datos concretos. Sé honesto aunque le lleve la contraria.
"""
    section = """
### 🧐 Tus opiniones a examen
Tabla con columnas: Tu opinión (resumida) | Veredicto (✅ Tiene sentido / ⚠️ Con matices / ❌ No la recomiendo) | Por qué.
Después, una frase sobre cómo han influido en la alineación y los waivers recomendados.
"""
    return block, section


def load_notes(roster_id):
    path = NOTES_DIR / f"equipo{roster_id:02d}.txt"
    return path.read_text(encoding="utf-8") if path.exists() else ""


def save_notes(roster_id, text):
    NOTES_DIR.mkdir(parents=True, exist_ok=True)
    (NOTES_DIR / f"equipo{roster_id:02d}.txt").write_text(text, encoding="utf-8")


def build_prompt(context, transcripts, week, players, roto_players, roto_latest, notes=""):
    notes_block, notes_section = _notes_block(notes)
    videos = "\n\n".join(
        f"### {t['source']} — «{t['title']}» ({t['url']})\n{t['text']}" for t in transcripts
    ) or "(No hay transcripciones disponibles.)"
    player_news = "\n".join(
        _format_news(item, players.get(pid, {}).get("full_name"))
        for pid, items in roto_players.items() for item in items
    ) or "(Sin noticias.)"
    latest_news = "\n".join(_format_news(item) for item in roto_latest) or "(Sin noticias.)"
    return f"""Eres mi asesor experto de Fantasy NFL. Responde SIEMPRE en español de España.

Hoy es {datetime.now():%d/%m/%Y}. Estamos en la semana {week} de la temporada.
Tus conocimientos internos pueden estar desfasados: plantillas, lesiones y roles cambian cada semana.
Antes de recomendar nada:
1. Abre con WebFetch https://www.cbssports.com/fantasy/football/ y lee los artículos de ESTA semana que sean útiles
   (waiver wire, rankings y proyecciones, previews por posición, risers & fallers, start/sit). Cítalos.
2. USA LA BÚSQUEDA WEB para completar lo que falte en fuentes fiables (ESPN, NFL.com, FantasyPros, NBC Sports,
   The Athletic, informes de lesiones oficiales): participación en entrenamientos, semanas de descanso (bye),
   reparto de snaps y targets, cambios de rol y dificultad del rival.
Da prioridad a las noticias de Rotowire de abajo, a CBS, a tus búsquedas y a los vídeos por encima de tu memoria.

## Mi situación (datos reales de mi liga)
{context}

## Noticias de Rotowire sobre mis jugadores, los del rival y los agentes libres
{player_news}

## Últimas noticias generales de la NFL en Rotowire
{latest_news}
{notes_block}
## Lo que comentan los analistas en sus últimos vídeos (transcripciones automáticas, pueden tener errores)
{videos}

## Lo que necesito
Escribe un informe en Markdown. La primera línea debe ser exactamente:
# Informe Fantasy · Semana {week} · <nombre del equipo analizado>
Después, un resumen de 2-3 frases y estas secciones exactas, en este orden:

### 🚨 Alertas
Lesiones, dudas, jugadores en bye o titulares que no deberían jugar. Para cada una, qué hacer.

### ✅ Alineación recomendada
Tabla con columnas: Hueco | Jugador | Confianza (Alta/Media/Baja) | Motivo breve.
Debe respetar los huecos de mi liga y usar solo jugadores de mi plantilla. Indica claramente los CAMBIOS respecto a mi alineación actual.

### 🏥 IR y límite de plantilla
Usa la "SITUACIÓN DEL IR" de los datos (confírmala con las noticias: el estado de lesión puede tener horas de retraso).
Si hay jugadores en IR que ya no son elegibles, explica que Sleeper obliga a activarlos y propón cómo cuadrar la
plantilla en este orden de preferencia: 1) pasar al IR a otro jugador que sí sea elegible (Out, Doubtful, IR...);
2) cortar al jugador de MENOS valor. Si todo está en regla, dilo en una línea.

### 📈 Waivers
Hasta 3 jugadores libres a pedir, por orden de prioridad, con a quién soltar a cambio y por qué.
Prioriza las posiciones marcadas como Urgente o Prioridad en NECESIDADES POR POSICIÓN y busca también libres
que no estén en tendencia si mejoran al titular más flojo. Si no merece la pena hacer cambios, dilo.

REGLAS PARA RECOMENDAR CORTES (en esta sección y en la del IR):
- Decide a quién cortar por su RENDIMIENTO REAL: media de puntos, media de las 3 últimas jornadas y partidos jugados.
  Cita esas cifras al justificar cada corte.
- NO recomiendes cortar a un jugador con buena media solo porque haya muchos en su posición: la profundidad con
  valor sirve para byes, lesiones y Superflex/FLEX. Antes que eso, corta a un suplente de media baja.
- Un jugador de media alta temporalmente lesionado (pero no elegible para IR) suele valer más que un suplente
  sano de media baja.
- Compara siempre la media del jugador a cortar con la del agente libre que entraría; si el libre no tiene
  puntos registrados, básate en su rol y en las noticias, y dilo.

### 🎙️ Opiniones de los expertos
Lo más relevante de los vídeos, de CBS Sports y de Rotowire sobre MIS jugadores, el rival o los waivers,
indicando de qué fuente sale cada cosa.
{notes_section}
### 📚 Fuentes
Enlaces de las noticias y artículos que has consultado.

Sé directo y concreto. Explica el porqué de cada decisión en una o dos frases.
Pon el emoji 🏥 delante del nombre de cualquier jugador que esté en la lista de lesionados (IR)."""


def run_claude(prompt, timeout_min=10):
    """Lanza Claude Code en modo no interactivo con tu suscripción y devuelve la respuesta."""
    exe = shutil.which("claude")
    if not exe:
        raise RuntimeError("No encuentro Claude Code ('claude'). ¿Está instalado y has iniciado sesión?")
    proc = subprocess.run(
        [exe, "-p", "--output-format", "json", "--allowedTools", "WebSearch,WebFetch"],
        input=prompt, capture_output=True, text=True, encoding="utf-8",
        timeout=timeout_min * 60, cwd=Path(__file__).parent,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Claude Code devolvió un error:\n{proc.stderr or proc.stdout}")
    result = json.loads(proc.stdout)
    if result.get("is_error"):
        raise RuntimeError(f"Claude Code devolvió un error:\n{result.get('result')}")
    return result["result"]


def save(report, week, roster_id):
    """Guarda el informe de un equipo: data/analisis/semana_08_equipo06_20261027_2222.md"""
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    path = ANALYSIS_DIR / f"semana_{week:02d}_equipo{roster_id:02d}_{datetime.now():%Y%m%d_%H%M}.md"
    path.write_text(report, encoding="utf-8")
    return path


GIT = shutil.which("git") or r"C:\Program Files\Git\cmd\git.exe"


def publish(message):
    """Sube a GitHub los informes y pronósticos nuevos para que aparezcan en la web pública.

    Devuelve (ok, texto). Nunca pide nada en pantalla: si GitHub necesita volver a iniciar sesión,
    falla y hay que usar publicar.bat a mano.
    """
    root = Path(__file__).parent
    if not (root / ".git").exists() or not Path(GIT).exists():
        return False, "no hay repositorio de Git en esta carpeta"
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0", "GCM_INTERACTIVE": "never"}

    def git(*args):
        return subprocess.run([GIT, *args], cwd=root, env=env, capture_output=True, text=True,
                              encoding="utf-8", errors="replace", timeout=90)

    try:
        git("add", "data/analisis", "data/partidos")
        git("commit", "-m", message)  # si no hay nada nuevo falla, pero puede quedar algo pendiente de subir
        push = git("push", "origin", "main")
    except (OSError, subprocess.TimeoutExpired) as e:
        return False, str(e)
    if push.returncode != 0:
        lines = (push.stderr or push.stdout).strip().splitlines()
        return False, lines[-1] if lines else f"git push terminó con código {push.returncode}"
    return True, "publicado en la web pública"


def latest(week, roster_id):
    """Último informe guardado de esta semana para un equipo (o None)."""
    files = sorted(ANALYSIS_DIR.glob(f"semana_{week:02d}_equipo{roster_id:02d}_*.md"))
    return files[-1] if files else None
