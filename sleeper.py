"""Conexión con la API pública de Sleeper (no necesita contraseña)."""
import json
import time
from pathlib import Path

import requests

API = "https://api.sleeper.app/v1"
CACHE_DIR = Path(__file__).parent / "data"
PLAYERS_CACHE = CACHE_DIR / "sleeper_players.json"


def _get(path):
    r = requests.get(f"{API}{path}", timeout=30)
    r.raise_for_status()
    return r.json()


def get_user(username):
    return _get(f"/user/{username}")


def get_state():
    """Temporada y semana actuales de la NFL."""
    return _get("/state/nfl")


def get_leagues(user_id, season):
    return _get(f"/user/{user_id}/leagues/nfl/{season}")


def get_league(league_id):
    return _get(f"/league/{league_id}")


def get_rosters(league_id):
    return _get(f"/league/{league_id}/rosters")


def get_users(league_id):
    return _get(f"/league/{league_id}/users")


def get_matchups(league_id, week):
    return _get(f"/league/{league_id}/matchups/{week}")


def get_trending(kind="add", hours=24, limit=50):
    """Jugadores más añadidos ("add") o soltados ("drop") en todo Sleeper."""
    return _get(f"/players/nfl/trending/{kind}?lookback_hours={hours}&limit={limit}")


PROJ_POSITIONS = ["QB", "RB", "WR", "TE", "K", "DEF", "DL", "LB", "DB"]


def get_projections(season, week):
    """Proyecciones de la semana por jugador (estadísticas previstas): {player_id: {...}}."""
    r = requests.get(f"https://api.sleeper.app/projections/nfl/{season}/{week}",
                     params=[("season_type", "regular")] + [("position[]", p) for p in PROJ_POSITIONS], timeout=30)
    r.raise_for_status()
    return {p["player_id"]: p for p in r.json()}


def get_players(max_age_hours=12):
    """Base de datos de todos los jugadores NFL.

    Pesa varios MB, así que Sleeper pide no descargarla más de una vez al día:
    la guardamos en disco y solo la refrescamos cuando tiene más de `max_age_hours`.
    """
    if PLAYERS_CACHE.exists() and time.time() - PLAYERS_CACHE.stat().st_mtime < max_age_hours * 3600:
        return json.loads(PLAYERS_CACHE.read_text(encoding="utf-8"))
    players = _get("/players/nfl")
    CACHE_DIR.mkdir(exist_ok=True)
    PLAYERS_CACHE.write_text(json.dumps(players), encoding="utf-8")
    return players
