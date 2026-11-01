"""Fuentes de análisis: vídeos de YouTube convertidos a texto y noticias de Rotowire."""
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
import yt_dlp
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi

BROWSER_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                                 "(KHTML, like Gecko) Chrome/130.0 Safari/537.36"}

TRANSCRIPTS_DIR = Path(__file__).parent / "data" / "transcripciones"
MADRID = ZoneInfo("Europe/Madrid")

# Listas de YouTube que seguimos. Para añadir otra fuente, añade una línea aquí.
PLAYLISTS = {
    "Los Fantásticos (Mundo NFL)": "https://www.youtube.com/playlist?list=PLZRL6fV-iO1U",
}


def latest_videos(playlist_url, n=2):
    """Últimos `n` vídeos de una lista: [{"id", "title"}]."""
    opts = {"extract_flat": True, "playlistend": n, "quiet": True, "no_warnings": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(playlist_url, download=False)
    return [{"id": e["id"], "title": e["title"]} for e in info["entries"]]


def transcript(video_id):
    """Texto completo de un vídeo (se guarda en disco para no descargarlo dos veces)."""
    path = TRANSCRIPTS_DIR / f"{video_id}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8")
    parts = YouTubeTranscriptApi().fetch(video_id, languages=["es", "es-419", "es-ES", "en"])
    text = " ".join(p.text for p in parts)
    TRANSCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return text


def collect(n_per_playlist=2):
    """Transcripciones recientes de todas las fuentes: [{"source", "title", "url", "text"}]."""
    out = []
    for source, url in PLAYLISTS.items():
        for v in latest_videos(url, n_per_playlist):
            try:
                text = transcript(v["id"])
            except Exception:
                continue  # vídeo sin subtítulos todavía
            out.append({"source": source, "title": v["title"],
                        "url": f"https://www.youtube.com/watch?v={v['id']}", "text": text})
    return out


# --- Vídeos de la semana para los Partidos NFL -----------------------------------
# Cada fuente indica qué vídeos de la semana se usan: de 100Yardas, los de los viernes (su "Previa");
# de TRENDZONE (Mundo NFL), que no publica los viernes, su vídeo semanal de PICKS.
NFL_WEEK_SOURCES = [
    {"source": "TRENDZONE (Mundo NFL)",
     "feed": "https://www.youtube.com/feeds/videos.xml?playlist_id=PLcfQmCtP_FdXsnk8INQayVJb-P7JEMlTD",
     "usar": lambda title, published: "PICKS" in title.upper()},
    {"source": "100Yardas",
     "feed": "https://www.youtube.com/feeds/videos.xml?channel_id=UCIvm9lEvhlbpmLkshkjQwXg",
     "usar": lambda title, published: published.weekday() == 4},  # 4 = viernes
]
_ATOM = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}


def feed_videos(feed_url):
    """Últimos vídeos de un canal o lista (feed RSS de YouTube): [{"id", "title", "published"}], hora de España."""
    r = requests.get(feed_url, headers=BROWSER_HEADERS, timeout=30)
    r.raise_for_status()
    root = ET.fromstring(r.content)
    return [{"id": e.find("yt:videoId", _ATOM).text, "title": e.find("a:title", _ATOM).text,
             "published": datetime.fromisoformat(e.find("a:published", _ATOM).text).astimezone(MADRID)}
            for e in root.findall("a:entry", _ATOM)]


def nfl_week_start(now=None):
    """Inicio de la semana NFL actual: el martes más reciente a las 00:00 (hora de España)."""
    now = now or datetime.now(MADRID)
    return (now - timedelta(days=(now.weekday() - 1) % 7)).replace(hour=0, minute=0, second=0, microsecond=0)


def nfl_week_videos():
    """Transcripciones de los vídeos de esta semana NFL elegidos en NFL_WEEK_SOURCES."""
    since = nfl_week_start()
    out = []
    for src in NFL_WEEK_SOURCES:
        try:
            videos = feed_videos(src["feed"])
        except requests.RequestException:
            continue
        for v in videos:
            if v["published"] < since or not src["usar"](v["title"], v["published"]):
                continue
            try:
                text = transcript(v["id"])
            except Exception:
                continue  # aún sin subtítulos
            out.append({"source": src["source"], "title": v["title"], "published": v["published"],
                        "url": f"https://www.youtube.com/watch?v={v['id']}", "text": text})
    return out


# --- Rotowire -----------------------------------------------------------------
def _parse_rotowire(html, n):
    """Extrae las `n` noticias más recientes de una página de Rotowire."""
    items = []
    for block in BeautifulSoup(html, "html.parser").select("div.news-update")[:n]:
        def text(cls):
            el = block.select_one(f".news-update__{cls}")
            return el.get_text(" ", strip=True) if el else ""
        analysis = text("analysis").removeprefix("ANALYSIS").strip()
        if "Subscribe now" in analysis:
            analysis = ""  # análisis de pago
        items.append({"player": text("player-link"), "date": text("timestamp"),
                      "headline": text("headline"), "news": text("news"), "analysis": analysis})
    return items


def rotowire_player_news(rotowire_id, n=2):
    """Últimas noticias (con análisis) de un jugador en Rotowire."""
    r = requests.get(f"https://www.rotowire.com/football/player.php?id={rotowire_id}",
                     headers=BROWSER_HEADERS, timeout=30)
    r.raise_for_status()
    return _parse_rotowire(r.text, n)


def rotowire_news_for(players, player_ids, n=2):
    """Noticias de Rotowire para una lista de jugadores de Sleeper: {player_id: [noticias]}."""
    def fetch(pid):
        rid = players.get(pid, {}).get("rotowire_id")
        if not rid:
            return pid, []
        try:
            return pid, rotowire_player_news(rid, n)
        except requests.RequestException:
            return pid, []

    with ThreadPoolExecutor(max_workers=6) as pool:
        return {pid: news for pid, news in pool.map(fetch, player_ids) if news}


def rotowire_latest(n=25):
    """Últimas noticias generales de la NFL en Rotowire."""
    r = requests.get("https://www.rotowire.com/football/news.php", headers=BROWSER_HEADERS, timeout=30)
    r.raise_for_status()
    return _parse_rotowire(r.text, n)
