"""Proyección de un enfrentamiento fantasy: puntos esperados por jugador y probabilidad de victoria."""
import math

# Sleeper y ESPN usan abreviaturas distintas para algún equipo
ESPN_ABBR = {"WAS": "WSH"}
# Desviación típica de los puntos de un jugador respecto a su proyección (aprox. 60 %)
PLAYER_SD = 0.6


def projected_points(proj, scoring):
    """Puntos fantasy proyectados con las reglas de puntuación de la liga (incluye IDP y pateadores)."""
    stats = (proj or {}).get("stats") or {}
    return sum(value * scoring[key] for key, value in stats.items() if key in scoring)


def game_by_team(games):
    """{abreviatura ESPN: partido} para saber si el partido de cada jugador no ha empezado, va en juego o acabó."""
    out = {}
    for g in games:
        out[g["home"]["abbr"]] = g
        out[g["away"]["abbr"]] = g
    return out


def remaining_fraction(game):
    """Parte del partido que queda por jugar (1 = no ha empezado, 0 = terminado)."""
    if game is None:
        return 0.0
    status = game["status"]
    if status in ("STATUS_SCHEDULED", "STATUS_POSTPONED", "STATUS_DELAYED"):
        return 1.0
    if status in ("STATUS_FINAL", "STATUS_FINAL_OVERTIME"):
        return 0.0
    if status == "STATUS_HALFTIME":
        return 0.5
    period, clock = game.get("period") or 1, game.get("clock") or 0
    return max(0.0, min(1.0, ((4 - min(period, 4)) * 900 + clock) / 3600))


def team_outlook(starters, slots, players_points, projections, players, scoring, games_by_team):
    """Proyección de un equipo: filas por titular y totales (actual, proyectado final y varianza)."""
    rows, actual_total, final_total, variance = [], 0.0, 0.0, 0.0
    for slot, pid in zip(slots, starters):
        if pid == "0":
            rows.append({"slot": slot, "pid": None, "actual": 0, "proj": 0, "final": 0, "state": "vacío"})
            continue
        team = (players.get(pid, {}).get("team") or "")
        game = games_by_team.get(ESPN_ABBR.get(team, team))
        proj = projected_points(projections.get(pid), scoring) if game else 0.0
        left = remaining_fraction(game)
        actual = players_points.get(pid, 0) or 0
        final = actual + proj * left
        if game is None:
            state = "bye"
        elif left == 1:
            state = "pendiente"
        elif left == 0:
            state = "final"
        else:
            state = "en juego"
        rows.append({"slot": slot, "pid": pid, "actual": actual, "proj": proj, "final": final, "state": state,
                     "game": game})
        actual_total += actual
        final_total += final
        variance += (PLAYER_SD * proj * left) ** 2
    return {"rows": rows, "actual": actual_total, "final": final_total, "var": variance}


def win_probability(a, b):
    """Probabilidad de que gane A (aproximación normal de la diferencia de puntos finales)."""
    sd = math.sqrt(a["var"] + b["var"])
    diff = a["final"] - b["final"]
    if sd == 0:
        return 1.0 if diff > 0 else 0.0 if diff < 0 else 0.5
    return 0.5 * (1 + math.erf(diff / (sd * math.sqrt(2))))
