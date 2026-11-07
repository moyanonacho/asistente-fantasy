"""Waivers a medida: qué posiciones necesita reforzar cada equipo y qué agentes libres le mejoran.

Se basa en las estadísticas reales de cada jornada de Sleeper (también de los jugadores libres),
puntuadas con las reglas de la liga.
"""
import re
import unicodedata

from analisis import player_value
from proyecciones import projected_points

POSITIONS = ["QB", "RB", "WR", "TE", "K", "DL", "LB", "DB"]
# Estados con los que un titular no va a jugar: su hueco cuenta como vacío
UNAVAILABLE = {"IR", "Out", "PUP", "Sus", "Doubtful"}
LEVELS = {  # orden de importancia, etiqueta y clase CSS
    "urgente": (0, "🚨 Urgente"),
    "prioridad": (1, "🔴 Prioridad"),
    "mejorable": (2, "🟡 Mejorable"),
    "cubierta": (3, "🟢 Cubierta"),
}


def position_of(p):
    """Posición fantasy principal de un jugador (QB, RB, WR, TE, K, DL, LB o DB)."""
    fp = p.get("fantasy_positions") or []
    return next((pos for pos in POSITIONS if pos in fp), p.get("position", "?"))


def weekly_from_stats(stats_by_week, scoring):
    """Puntos de cada jugador en cada jornada con la puntuación de la liga: {player_id: {semana: puntos}}."""
    out = {}
    for wk, rows in stats_by_week.items():
        for pid, row in rows.items():
            out.setdefault(pid, {})[wk] = projected_points(row, scoring)
    return out


def rating(v):
    """Valor de un jugador: mitad media de la temporada, mitad forma reciente (3 últimos partidos).
    Con menos de 3 partidos se rebaja, para que un único partidazo no parezca una tendencia."""
    if not v["games"]:
        return 0.0
    return (v["avg"] + v["last3"]) / 2 * min(1.0, (v["games"] + 1) / 4)


def _value(pid, weekly, players):
    v = player_value(pid, weekly)
    out = (players.get(pid, {}).get("injury_status") or "") in UNAVAILABLE
    return {**v, "rating": rating(v), "out": out}


def free_agent_pool(players, rosters, usable, weekly, projections, scoring, adds):
    """Agentes libres de la liga con valor real, del mejor al peor."""
    rostered = {pid for r in rosters for pid in (r["players"] or [])}
    candidates = (set(weekly) | set(projections) | set(adds)) - rostered
    pool = []
    for pid in candidates:
        p = players.get(pid)
        if not p or not p.get("team") or position_of(p) not in usable:
            continue
        v = _value(pid, weekly, players)
        proj = projected_points(projections.get(pid), scoring)
        if v["games"] == 0 and proj < 1:
            continue
        pool.append({"pid": pid, "pos": position_of(p), **v, "proj": proj, "adds": adds.get(pid, 0)})
    return sorted(pool, key=lambda f: (f["rating"], f["proj"]), reverse=True)


def _starters_by_pos(roster, slots, players):
    out = {}
    for slot, pid in zip(slots, roster["starters"] or []):
        if pid and pid != "0":
            out.setdefault(position_of(players.get(pid, {})), []).append(pid)
    return out


def team_needs(league, roster, rosters, players, weekly, pool):
    """Para cada posición: el titular más flojo del equipo, su puesto en la liga y el mejor libre que le mejora."""
    slots = [s for s in league["roster_positions"] if s != "BN"]
    usable = {f["pos"] for f in pool} | {s for s in slots if s in POSITIONS}
    value = lambda pid: _value(pid, weekly, players)
    # Fuerza de cada equipo en cada posición: media del valor de sus titulares (lesionados cuentan 0)
    strength = {}
    for r in rosters:
        for pos, pids in _starters_by_pos(r, slots, players).items():
            vals = [0.0 if value(pid)["out"] else value(pid)["rating"] for pid in pids]
            strength.setdefault(pos, {})[r["roster_id"]] = sum(vals) / len(vals)
    mine = _starters_by_pos(roster, slots, players)
    reserve = set(roster.get("reserve") or [])
    bench = [pid for pid in roster["players"] or [] if pid not in (roster["starters"] or []) and pid not in reserve]
    needs = []
    for pos in POSITIONS:
        if pos not in usable:
            continue
        starters = [(pid, value(pid)) for pid in mine.get(pos, [])]
        # Si un titular no va a jugar, primero se cubre con el mejor suplente sano de esa posición
        healthy_bench = sorted(((pid, value(pid)) for pid in bench
                                if position_of(players.get(pid, {})) == pos and not value(pid)["out"]),
                               key=lambda s: -s[1]["rating"])
        out_starters = [pid for pid, v in starters if v["out"]]
        lineup = [(pid, v) for pid, v in starters if not v["out"]] + healthy_bench[:len(out_starters)]
        weakest = min(lineup, key=lambda s: s[1]["rating"]) if lineup else None
        hole = pos in slots and len(lineup) < max(slots.count(pos), len(starters))  # hueco que nadie cubre
        bar = 0.0 if hole or not weakest else weakest[1]["rating"]
        teams = strength.get(pos, {})
        mine_strength = teams.get(roster["roster_id"], 0.0)
        rank = 1 + sum(1 for rid, s in teams.items() if s > mine_strength and rid != roster["roster_id"])
        best = next((f for f in pool if f["pos"] == pos and not f["out"]), None)
        gain = best["rating"] - bar if best else 0.0
        if hole and best:
            level = "urgente"
        elif gain >= 3 or (gain >= 1 and rank > len(rosters) / 2):
            level = "prioridad"
        elif gain > 0.3:
            level = "mejorable"
        else:
            level = "cubierta"
        needs.append({"pos": pos, "starters": starters, "weakest": weakest, "hole": hole, "bar": bar,
                      "out_starters": out_starters,
                      "rank": rank, "teams": len(rosters), "best": best, "gain": gain, "level": level})
    return needs


def drop_candidate(roster, players, weekly, projections, scoring):
    """Suplente sano con menos valor: el primero en salir si se ficha a alguien.
    Cuenta también su proyección de la semana, para no señalar a quien acaba de volver de una lesión."""
    reserve = set(roster.get("reserve") or [])
    starters = set(roster["starters"] or [])
    bench = [pid for pid in roster["players"] or []
             if pid not in starters and pid not in reserve
             and (players.get(pid, {}).get("injury_status") or "") not in UNAVAILABLE]
    if not bench:
        return None
    worth = lambda pid: max(_value(pid, weekly, players)["rating"], projected_points(projections.get(pid), scoring))
    pid = min(bench, key=worth)
    return pid, _value(pid, weekly, players)


# Cuánto pesa la opinión de Los Fantásticos al ordenar (en puntos de valor; no cambia el valor mostrado)
OPINION_BONUS = {"fichar": 2.0, "vigilar": 0.5, "evitar": -2.0}


def _norm(name):
    name = re.sub(r"[^a-z ]", "", unicodedata.normalize("NFKD", name.lower()).encode("ascii", "ignore").decode())
    return "".join(w for w in name.split() if w not in ("jr", "sr", "ii", "iii", "iv", "v"))


def match_opinions(data, players):
    """Asocia cada jugador que nombran Los Fantásticos con su ficha de Sleeper: {player_id: opinión}."""
    if not data:
        return {}
    index = {}
    for pid, p in players.items():
        if p.get("full_name") and position_of(p) in POSITIONS:
            key = _norm(p["full_name"])
            # Si dos jugadores se llaman igual, nos quedamos con el que tiene equipo NFL
            if key not in index or (p.get("team") and not players[index[key]].get("team")):
                index[key] = pid
    out = {}
    for item in data.get("jugadores", []):
        pid = index.get(_norm(item.get("nombre", "")))
        if pid and item.get("veredicto") in OPINION_BONUS:
            out[pid] = item
    return out


def with_gain(pool, needs, opinions=None):
    """Añade a cada libre cuánto mejora al titular más flojo de su posición en este equipo, la opinión de
    Los Fantásticos y una nota para ordenar (mejora + opinión).
    Los lesionados que no van a jugar no mejoran nada de momento: van al final de su posición."""
    opinions = opinions or {}
    bars = {n["pos"]: n for n in needs}
    out = []
    for f in pool:
        n = bars.get(f["pos"])
        gain = f["rating"] - n["bar"] if n and not f["out"] else 0.0
        replaces = None if not n or n["hole"] or not n["weakest"] else n["weakest"][0]
        opinion = opinions.get(f["pid"])
        bonus = OPINION_BONUS[opinion["veredicto"]] if opinion else 0.0
        out.append({**f, "gain": gain, "replaces": replaces, "hole": bool(n and n["hole"]),
                    "opinion": opinion, "score": gain + bonus, "pos_score": f["rating"] + bonus})
    return sorted(out, key=lambda f: (f["out"], -f["pos_score"]))


def needs_text(needs, players):
    """Resumen de necesidades para el prompt de Claude."""
    name = lambda pid: players.get(pid, {}).get("full_name") or pid
    lines = ["", "NECESIDADES POR POSICIÓN (valor = mitad media de la temporada, mitad media de los 3 últimos partidos, "
             "con la puntuación de la liga):"]
    for n in sorted(needs, key=lambda n: LEVELS[n["level"]][0]):
        weak = (f"titular más flojo {name(n['weakest'][0])} (valor {n['weakest'][1]['rating']:.1f})"
                if n["weakest"] and not n["hole"] else "hueco sin titular disponible")
        best = (f"mejor libre {name(n['best']['pid'])} (valor {n['best']['rating']:.1f}, {n['gain']:+.1f})"
                if n["best"] else "sin libres con puntos")
        lines.append(f"- {n['pos']}: {LEVELS[n['level']][1]} · puesto {n['rank']}/{n['teams']} de la liga · {weak} · {best}")
    return lines
