"""Partidos NFL de la jornada: calendario y estadísticas (API pública de ESPN) y pronósticos de Claude."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests

SCOREBOARD = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"
TEAM_STATS = ("https://sports.core.api.espn.com/v2/sports/football/leagues/nfl/seasons/{season}"
              "/types/2/teams/{team_id}/statistics")
PICKS_DIR = Path(__file__).parent / "data" / "partidos"

# Estadísticas de equipo que se muestran y se pasan a Claude: (categoría ESPN, nombre ESPN, etiqueta)
KEY_STATS = [
    ("scoring", "totalPointsPerGame", "Puntos por partido"),
    ("passing", "yardsPerGame", "Yardas por partido"),
    ("passing", "netPassingYardsPerGame", "Yardas de pase por partido"),
    ("rushing", "rushingYardsPerGame", "Yardas de carrera por partido"),
    ("miscellaneous", "thirdDownConvPct", "% conversión en 3er down"),
    ("miscellaneous", "redzoneScoringPct", "% anotación en zona roja"),
    ("miscellaneous", "turnOverDifferential", "Diferencial de pérdidas"),
    ("miscellaneous", "totalTakeaways", "Balones recuperados"),
    ("defensive", "sacks", "Sacks de la defensa"),
    ("defensiveInterceptions", "interceptions", "Intercepciones de la defensa"),
]
FPI_URL = "https://site.web.api.espn.com/apis/fitt/v3/sports/football/nfl/powerindex"
SUMMARY = "https://site.api.espn.com/apis/site/v2/sports/football/nfl/summary"
LEADER_NAMES = {"passingYards": "Pase", "rushingYards": "Carrera", "receivingYards": "Recepción",
                "sacks": "Sacks", "totalTackles": "Placajes"}


def _rank_num(text):
    m = re.search(r"\d+", str(text or ""))
    return int(m.group()) if m else None


def fpi(season):
    """Football Power Index de ESPN: {team_id: {...}} con eficiencias (EPA) y proyecciones."""
    r = requests.get(FPI_URL, params={"region": "us", "lang": "en", "season": season}, timeout=30)
    r.raise_for_status()
    out = {}
    for t in r.json()["teams"]:
        cats = {c["name"]: c for c in t["categories"]}
        def get(cat, name):
            names = {"fpi": ["fpi", "epaoffense", "epadefense", "epaspecialteams", "fpirank", "accomplishmentrank",
                             "avgsosrank", "sosremainingrank"],
                     "projections": ["projectedw", "projectedl", "probwinout", "probwinconf", "probwindiv",
                                     "probmakeplayoffs"],
                     "efficiencies": ["totefficiency", "totefficiencyrank", "offefficiency", "offefficiencyrank",
                                      "defefficiency", "defefficiencyrank", "stefficiency", "stefficiencyrank"]}[cat]
            values = cats.get(cat, {}).get("values") or []
            i = names.index(name)
            return values[i] if i < len(values) else None
        out[t["team"]["id"]] = {
            "fpi": get("fpi", "fpi"), "fpi_rank": get("fpi", "fpirank"),
            "sos_rest_rank": get("fpi", "sosremainingrank"),
            "tot_eff": get("efficiencies", "totefficiency"), "tot_rank": get("efficiencies", "totefficiencyrank"),
            "off_eff": get("efficiencies", "offefficiency"), "off_rank": get("efficiencies", "offefficiencyrank"),
            "def_eff": get("efficiencies", "defefficiency"), "def_rank": get("efficiencies", "defefficiencyrank"),
            "st_eff": get("efficiencies", "stefficiency"), "st_rank": get("efficiencies", "stefficiencyrank"),
            "proj_w": get("projections", "projectedw"), "proj_l": get("projections", "projectedl"),
            "playoffs_pct": get("projections", "probmakeplayoffs"),
        }
    return out


def game_summary(event_id):
    """Del resumen de ESPN de un partido: pronóstico de victoria, lesiones y líderes de cada equipo."""
    r = requests.get(SUMMARY, params={"event": event_id}, timeout=30)
    r.raise_for_status()
    s = r.json()
    pred = s.get("predictor") or {}
    predictor = {side: float(pred[side]["gameProjection"]) for side in ("homeTeam", "awayTeam")
                 if (pred.get(side) or {}).get("gameProjection")}
    injuries = {}
    for team in s.get("injuries", []):
        injuries[team["team"]["abbreviation"]] = [
            {"jugador": i["athlete"]["displayName"],
             "posicion": (i["athlete"].get("position") or {}).get("abbreviation", ""),
             "estado": i.get("status", "")}
            for i in team.get("injuries", []) if i.get("status") in ("Out", "Doubtful", "Questionable", "Injured Reserve")]
    leaders = {}
    for team in s.get("leaders", []):
        leaders[team["team"]["abbreviation"]] = [
            {"categoria": LEADER_NAMES.get(cat["name"], cat["name"]),
             "jugador": cat["leaders"][0]["athlete"]["displayName"], "valor": cat["leaders"][0]["displayValue"]}
            for cat in team.get("leaders", []) if cat.get("leaders")]
    return {"predictor": {"home": predictor.get("homeTeam"), "away": predictor.get("awayTeam")},
            "injuries": injuries, "leaders": leaders}


def all_summaries(games):
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(zip((g["id"] for g in games), pool.map(lambda g: game_summary(g["id"]), games)))


def strengths_weaknesses(stats, fpi_team):
    """Puntos fuertes (top 8 de la liga) y débiles (puesto 25 o peor) según las estadísticas de ESPN."""
    items = [(label, value, _rank_num(rank)) for label, (value, rank) in stats.items()]
    if fpi_team:
        for key, label in (("off_rank", "Eficiencia ofensiva (EPA)"), ("def_rank", "Eficiencia defensiva (EPA)"),
                           ("st_rank", "Eficiencia equipos especiales (EPA)")):
            if fpi_team.get(key):
                items.append((label, "", int(fpi_team[key])))
    strong = sorted([i for i in items if i[2] and i[2] <= 8], key=lambda i: i[2])
    weak = sorted([i for i in items if i[2] and i[2] >= 25], key=lambda i: -i[2])
    return strong, weak


def _side(competitor):
    team = competitor["team"]
    records = {r.get("type") or r.get("name"): r.get("summary") for r in competitor.get("records", [])}
    summaries = [r.get("summary") for r in competitor.get("records", [])]
    return {
        "id": team["id"],
        "abbr": team["abbreviation"],
        "name": team["displayName"],
        "short": team.get("shortDisplayName") or team["name"],
        "color": "#" + (team.get("color") or "334155"),
        "alt": "#" + (team.get("alternateColor") or "94A3B8"),
        "record": summaries[0] if summaries else "",
        "home_record": records.get("home") or (summaries[1] if len(summaries) > 1 else ""),
        "away_record": records.get("road") or (summaries[2] if len(summaries) > 2 else ""),
        "score": int(competitor["score"]) if str(competitor.get("score", "")).isdigit() else None,
        "winner": competitor.get("winner"),
    }


def team_colors():
    """Colores de los 32 equipos NFL según ESPN: {abreviatura: (color principal, color secundario)}."""
    r = requests.get("https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams", timeout=30)
    r.raise_for_status()
    teams = [t["team"] for t in r.json()["sports"][0]["leagues"][0]["teams"]]
    return {t["abbreviation"]: ("#" + (t.get("color") or "334155"), "#" + (t.get("alternateColor") or "FFFFFF"))
            for t in teams}


def week_games(season, week):
    """Partidos de la jornada (regular season) y equipos que descansan."""
    r = requests.get(SCOREBOARD, params={"week": week, "seasontype": 2, "dates": season}, timeout=30)
    r.raise_for_status()
    data = r.json()
    games = []
    for event in data["events"]:
        comp = event["competitions"][0]
        sides = {c["homeAway"]: _side(c) for c in comp["competitors"]}
        odds = (comp.get("odds") or [{}])[0]
        kickoff = datetime.fromisoformat(event["date"].replace("Z", "+00:00")).astimezone(ZoneInfo("Europe/Madrid"))
        games.append({
            "id": event["id"],
            "kickoff": kickoff,
            "venue": comp.get("venue", {}).get("fullName", ""),
            "tv": ", ".join(n for b in comp.get("broadcasts", []) for n in b.get("names", [])),
            "status": comp["status"]["type"]["name"],
            "status_text": comp["status"]["type"].get("shortDetail", ""),
            "period": comp["status"].get("period"),
            "clock": comp["status"].get("clock"),
            "home": sides["home"],
            "away": sides["away"],
            "spread": odds.get("details", ""),
            "over_under": odds.get("overUnder"),
        })
    byes = [t["abbreviation"] for t in (data.get("week") or {}).get("teamsOnBye", [])]
    return sorted(games, key=lambda g: g["kickoff"]), byes


def team_stats(season, team_id):
    """{etiqueta: (valor, puesto en la liga)} con las estadísticas clave de un equipo."""
    r = requests.get(TEAM_STATS.format(season=season, team_id=team_id), timeout=30)
    r.raise_for_status()
    found = {}
    for cat in r.json()["splits"]["categories"]:
        for s in cat["stats"]:
            found[(cat["name"], s["name"])] = (s.get("displayValue", ""), s.get("rankDisplayValue", ""))
    return {label: found[(cat, name)] for cat, name, label in KEY_STATS if (cat, name) in found}


def all_team_stats(season, games):
    ids = {g[side]["id"] for g in games for side in ("home", "away")}
    with ThreadPoolExecutor(max_workers=8) as pool:
        return dict(zip(ids, pool.map(lambda tid: team_stats(season, tid), ids)))


def _fmt_fpi(f):
    if not f:
        return "sin datos FPI"
    return (f"FPI {f['fpi']:.1f} (puesto {f['fpi_rank']:.0f}); eficiencia total {f['tot_eff']:.1f} "
            f"(puesto {f['tot_rank']:.0f}), ofensiva {f['off_eff']:.1f} (puesto {f['off_rank']:.0f}), defensiva "
            f"{f['def_eff']:.1f} (puesto {f['def_rank']:.0f}), equipos especiales {f['st_eff']:.1f} "
            f"(puesto {f['st_rank']:.0f}); proyección {f['proj_w']:.1f}-{f['proj_l']:.1f}, "
            f"{f['playoffs_pct']:.0f}% de llegar a playoffs; dificultad del calendario restante: puesto {f['sos_rest_rank']:.0f}")


def build_prompt(season, week, games, stats, fpi_data, summaries, transcripts):
    lines = []
    for g in games:
        a, h = g["away"], g["home"]
        summ = summaries.get(g["id"], {})
        pred = summ.get("predictor", {})
        lines.append(f"### Partido {g['id']}: {a['name']} ({a['abbr']}) en {h['name']} ({h['abbr']})")
        lines.append(f"Fecha (hora de España): {g['kickoff']:%d/%m %H:%M} · Estadio: {g['venue']} · "
                     f"Línea de apuestas: {g['spread'] or 'sin línea'} · Over/Under: {g['over_under'] or '-'} · "
                     f"Predicción de ESPN: {a['abbr']} {pred.get('away') or '?'}% - {h['abbr']} {pred.get('home') or '?'}%")
        for side, label in ((a, "Visitante"), (h, "Local")):
            st = "; ".join(f"{k}: {v} ({rank})" for k, (v, rank) in stats.get(side["id"], {}).items())
            strong, weak = strengths_weaknesses(stats.get(side["id"], {}), fpi_data.get(side["id"]))
            leaders = "; ".join(f"{x['categoria']}: {x['jugador']} ({x['valor']})"
                                for x in summ.get("leaders", {}).get(side["abbr"], []))
            injuries = "; ".join(f"{x['jugador']} ({x['posicion']}, {x['estado']})"
                                 for x in summ.get("injuries", {}).get(side["abbr"], [])) or "ninguna destacada"
            lines.append(f"- {label} {side['abbr']}: récord {side['record']} (casa {side['home_record']}, "
                         f"fuera {side['away_record']}).")
            lines.append(f"  Estadísticas ESPN: {st}")
            lines.append(f"  Estadísticas avanzadas ESPN: {_fmt_fpi(fpi_data.get(side['id']))}")
            lines.append(f"  Puntos fuertes: {', '.join(f'{l} ({r}º)' for l, _, r in strong) or 'ninguno destacado'}. "
                         f"Puntos débiles: {', '.join(f'{l} ({r}º)' for l, _, r in weak) or 'ninguno destacado'}")
            lines.append(f"  Líderes: {leaders}")
            lines.append(f"  Lesiones: {injuries}")
        lines.append("")
    videos = "\n\n".join(f"### {t['source']} — «{t['title']}» ({t['published']:%A %d/%m})\n{t['text']}"
                         for t in transcripts) or "(Todavía no hay vídeos de esta semana.)"
    return f"""Eres un analista experto de la NFL. Responde en español de España.
Hoy es {datetime.now():%d/%m/%Y}. Temporada {season}, semana {week}. Tus conocimientos pueden estar desfasados:
usa la BÚSQUEDA WEB para comprobar informes de entrenamientos de última hora, rachas recientes y enfrentamientos
directos. Abre con WebFetch https://www.cbssports.com/nfl/picks/experts/ para ver los pronósticos de los expertos
de CBS Sports y tenlos en cuenta. El FPI y las eficiencias EPA de ESPN miden la calidad real de cada unidad
(ataque, defensa, equipos especiales): úsalos para explicar dónde se decide cada partido, cruzando la fortaleza
de un equipo con la debilidad del rival.

## Partidos de la semana (datos reales de ESPN, con el puesto de cada equipo en la liga entre paréntesis)
{chr(10).join(lines)}
## Lo que dicen los analistas en los vídeos de esta semana (TRENDZONE de Mundo NFL y 100Yardas)
{videos}

## Lo que necesito
Para CADA partido, un pronóstico basado en estadística y en las opiniones de las fuentes. Responde ÚNICAMENTE con un
array JSON válido (sin texto antes ni después, sin ```), con un objeto por partido y exactamente estas claves:
- "id": el id del partido tal cual aparece arriba (texto).
- "ganador": abreviatura del equipo que prevés que gane.
- "confianza": entero de 50 a 95 (probabilidad estimada de que gane).
- "marcador": marcador estimado "Visitante-Local", p. ej. "20-24".
- "resumen": una frase con el veredicto.
- "argumentos": lista de 3 o 4 frases, cada una apoyada en una estadística o dato concreto (cita cifras).
- "factor_clave": una frase con el factor que decidirá el partido.
- "destacados": objeto con la abreviatura de cada equipo como clave y, como valor, una lista de 2 jugadores
  {{"jugador": nombre, "posicion": "QB/RB/WR/TE/DEF...", "motivo": frase corta con datos}}.
- "expertos": una frase sobre qué opinan CBS, TRENDZONE y 100Yardas de este partido (o "Sin opinión disponible").
- "fuentes": lista de URLs consultadas para ese partido.
Comprueba que los jugadores destacados están sanos y siguen en ese equipo."""


def parse_picks(text):
    """Extrae el array JSON de la respuesta de Claude: {id_partido: pronóstico}."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    start, end = text.find("["), text.rfind("]")
    picks = json.loads(text[start:end + 1])
    return {str(p["id"]): p for p in picks}


def save_picks(season, week, picks):
    PICKS_DIR.mkdir(parents=True, exist_ok=True)
    path = PICKS_DIR / f"{season}_semana_{week:02d}.json"
    path.write_text(json.dumps({"made": datetime.now().isoformat(timespec="minutes"), "picks": picks},
                               ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def load_picks(season, week):
    path = PICKS_DIR / f"{season}_semana_{week:02d}.json"
    if not path.exists():
        return None, {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return datetime.fromisoformat(data["made"]), data["picks"]
