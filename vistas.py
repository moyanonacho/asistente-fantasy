"""Vistas en HTML: clasificación con movimientos, mercado de waivers y enfrentamiento."""
import base64
import html
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

INJURY_ICON = {"Out": "🔴", "IR": "🏥", "PUP": "🔴", "Sus": "🔴", "Doubtful": "🟠", "Questionable": "🟡"}
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def _e(text):
    return html.escape(str(text))


# --- Clasificación -------------------------------------------------------------
def season_table(rosters, matchups_by_week, upto):
    """Récord, puntos y resultados de cada equipo sumando las jornadas 1..upto: {roster_id: {...}}."""
    table = {r["roster_id"]: {"w": 0, "l": 0, "t": 0, "pf": 0.0, "pa": 0.0, "res": []} for r in rosters}
    for wk in range(1, upto + 1):
        games = {}
        for m in matchups_by_week.get(wk, []):
            if m.get("matchup_id"):
                games.setdefault(m["matchup_id"], []).append(m)
        for pair in games.values():
            if len(pair) != 2:
                continue
            for me, rival in (pair, pair[::-1]):
                row = table[me["roster_id"]]
                mine, theirs = me.get("points") or 0, rival.get("points") or 0
                row["pf"] += mine
                row["pa"] += theirs
                result = "V" if mine > theirs else "D" if mine < theirs else "E"
                row["res"].append(result)
                row[{"V": "w", "D": "l", "E": "t"}[result]] += 1
    order = sorted(table, key=lambda rid: (table[rid]["w"] + 0.5 * table[rid]["t"], table[rid]["pf"]), reverse=True)
    for i, rid in enumerate(order):
        table[rid]["rank"] = i + 1
    return table


def streak(results):
    """Racha actual, p. ej. ("V", 3)."""
    if not results:
        return None, 0
    n = 1
    while n < len(results) and results[-n - 1] == results[-1]:
        n += 1
    return results[-1], n


def render_standings(cur, prev, names, playoff_teams, selected_rid, my_rid, week_done):
    """Clasificación tipo marcador de liga: podio con medallas, barras de puntos, movimientos, rachas y zona de playoffs.
    `names`: {roster_id: (equipo, manager, url_avatar)}."""
    order = sorted(cur, key=lambda r: cur[r]["rank"])
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    rows = []
    for rid in order:
        c = cur[rid]
        team, manager, avatar = names[rid]
        move = prev[rid]["rank"] - c["rank"] if prev else 0
        mv = (f'<span class="fx-lb-mv up">▲{move}</span>' if move > 0 else
              f'<span class="fx-lb-mv down">▼{-move}</span>' if move < 0 else '<span class="fx-lb-mv same">=</span>')
        kind, n = streak(c["res"])
        racha = f'<span class="fx-lb-streak {kind}">{"🔥" if kind == "V" and n >= 3 else "🧊" if kind == "D" and n >= 3 else ""}{kind}{n}</span>' if kind else ""
        dots = "".join(f'<span class="fx-dot {r}"></span>' for r in c["res"][-5:])
        games = c["w"] + c["l"] + c["t"]
        pct = 100 * (c["w"] + 0.5 * c["t"]) / games if games else 0
        img = f'<img src="{_e(avatar)}">' if avatar else '<span class="fx-lb-noav">🏈</span>'
        zone = "in" if c["rank"] <= playoff_teams else "last" if c["rank"] == len(order) else "out"
        classes = f"fx-lb-row {zone}" + (" sel" if rid == selected_rid else "") + (" me" if rid == my_rid else "")
        rows.append(f"""<div class="{classes}">
  <div class="fx-lb-rank r{c['rank']}">{medals.get(c['rank'], c['rank'])}</div>
  {mv}
  <div class="fx-lb-team">{img}<div><b>{'⭐ ' if rid == my_rid else ''}{_e(team)}{' 🥄' if zone == 'last' else ''}</b>
    <small>{_e(manager)}</small></div></div>
  <div class="fx-lb-rec"><b>{c['w']}-{c['l']}{'-' + str(c['t']) if c['t'] else ''}</b><small>{pct:.0f}% victorias</small></div>
  <div class="fx-lb-pts">
    <div><b>{c['pf']:.1f}</b><small>A favor</small></div>
    <div><b>{c['pa']:.1f}</b><small>En contra</small></div>
    <div class="{'pos' if c['pf'] >= c['pa'] else 'neg'}"><b>{c['pf'] - c['pa']:+.1f}</b><small>Diferencia</small></div>
  </div>
  <div class="fx-lb-form">{racha}<div class="fx-lb-dots">{dots}</div></div>
</div>""")
        if c["rank"] == playoff_teams:
            rows.append('<div class="fx-lb-line"><span>✂️ LÍNEA DE PLAYOFFS</span></div>')
    return f"""<div class="fx-lb">
  <div class="fx-lb-head"><div>#</div><div></div><div>Equipo</div><div>Récord</div><div>Puntos de la temporada</div><div>Forma</div></div>
  {''.join(rows)}
</div>
<div class="fx-legend">Movimiento respecto a la jornada {week_done - 1} · A favor: puntos que ha anotado el equipo ·
En contra: puntos que le han anotado sus rivales · Diferencia: a favor menos en contra · 🔥 3+ victorias seguidas · 🧊 3+ derrotas seguidas · 🥄 farolillo rojo</div>"""


# --- Mercado de waivers --------------------------------------------------------
def next_waiver_run(day_of_week, now=None):
    """Próximo cierre de waivers de Sleeper (aprox. a medianoche hora del Pacífico), en hora de España."""
    pt = ZoneInfo("America/Los_Angeles")
    now = (now or datetime.now(pt)).astimezone(pt)
    run = (now + timedelta(days=(day_of_week - now.weekday()) % 7)).replace(hour=0, minute=0, second=0, microsecond=0)
    if run <= now:
        run += timedelta(days=7)
    return run.astimezone(ZoneInfo("Europe/Madrid"))


def _k(n):
    return f"{n / 1000:.1f}K" if n >= 1000 else str(n)


def render_market(players, free_agents, drops, waiver_run, faab_left, faab_total):
    """Waivers como un tablero de bolsa: demanda, variación neta, señal y cuenta atrás hasta el cierre."""
    left = waiver_run - datetime.now(ZoneInfo("Europe/Madrid"))
    hours, minutes = int(left.total_seconds() // 3600), int(left.total_seconds() % 3600 // 60)
    countdown = f"{hours // 24}d {hours % 24}h {minutes}m" if hours >= 24 else f"{hours}h {minutes}m"
    max_adds = max((c for _, c in free_agents), default=1)

    ticker, rows = [], []
    for i, (pid, adds) in enumerate(free_agents):
        p = players.get(pid, {})
        name = p.get("full_name") or pid
        dropped = drops.get(pid, 0)
        net = adds - dropped
        status = p.get("injury_status") or ""
        if status:
            signal = '<span class="fx-sig risk">⚠️ RIESGO</span>'
        elif i < 3:
            signal = '<span class="fx-sig hot">🔥 COMPRA FUERTE</span>'
        elif i < 8:
            signal = '<span class="fx-sig buy">✅ COMPRA</span>'
        else:
            signal = '<span class="fx-sig watch">👀 VIGILAR</span>'
        symbol = (p.get("last_name") or name).upper()[:6]
        ticker.append(f'<span class="fx-tick"><b>{_e(symbol)}</b> {_e(p.get("position", ""))} '
                      f'<i class="{"up" if net >= 0 else "down"}">{"▲" if net >= 0 else "▼"} {_k(abs(net))}</i></span>')
        bar = int(100 * adds / max_adds)
        rows.append(f"""<tr>
  <td class="fx-mk-rank">{i + 1}</td>
  <td><div class="fx-mk-name">{_e(name)} {INJURY_ICON.get(status, '')}</div>
      <div class="fx-mk-sub">{_e(p.get('position', ''))} · {_e(p.get('team') or 'FA')}</div></td>
  <td><div class="fx-mk-up">▲ {_k(adds)}</div><div class="fx-bar"><span style="width:{bar}%"></span></div></td>
  <td class="fx-mk-down">▼ {_k(dropped)}</td>
  <td class="{'fx-mk-up' if net >= 0 else 'fx-mk-down'}">{'+' if net >= 0 else '−'}{_k(abs(net))}</td>
  <td>{signal}</td>
</tr>""")
    tape = "".join(ticker) * 2  # duplicado para que la cinta gire sin cortes
    return f"""<div class="fx-market">
  <div class="fx-mk-head">
    <div class="fx-mk-title"><span class="fx-live"></span> MERCADO DE WAIVERS</div>
    <div class="fx-mk-chip">⏳ Cierre en <b>{countdown}</b><small>{DIAS[waiver_run.weekday()]} {waiver_run:%d/%m · %H:%M} (aprox.)</small></div>
    <div class="fx-mk-chip">💰 Saldo FAAB <b>${faab_left}</b><small>de ${faab_total}</small></div>
  </div>
  <div class="fx-tape"><div class="fx-tape-inner">{tape}</div></div>
  <div class="fx-mk-scroll"><table class="fx-mk-table">
    <thead><tr><th>#</th><th>Jugador</th><th>Altas 24 h</th><th>Bajas 24 h</th><th>Neto</th><th>Señal</th></tr></thead>
    <tbody>{''.join(rows)}</tbody>
  </table></div>
  <div class="fx-mk-foot">Altas y bajas en todas las ligas de Sleeper en las últimas 24 h · solo jugadores libres en tu liga</div>
</div>"""


# --- Mi equipo (tarjetas de jugador) ---------------------------------------------
POS_COLORS = {"QB": "#E5484D", "RB": "#2EAD6B", "WR": "#3B82F6", "TE": "#F59E0B", "K": "#A855F7",
              "DL": "#E07B39", "LB": "#14B8A6", "DB": "#EC4899"}
OFFENSE_SLOTS = {"QB", "RB", "WR", "TE", "FLEX", "SUPER_FLEX", "REC_FLEX", "WRRB_FLEX"}
DEFENSE_SLOTS = {"DL", "LB", "DB", "IDP_FLEX", "DEF"}


def weekly_points(history):
    """Puntos de cada jugador en cada jornada jugada: {player_id: {semana: puntos}}."""
    out = {}
    for wk, matchups in history.items():
        for m in matchups:
            for pid, pts in (m.get("players_points") or {}).items():
                out.setdefault(pid, {})[wk] = pts
    return out


def _fantasy_pos(p):
    fp = p.get("fantasy_positions") or []
    for pos in ("QB", "RB", "WR", "TE", "K", "DL", "LB", "DB"):
        if pos in fp:
            return pos
    return p.get("position", "?")


def _sparkline(values):
    if len(values) < 2:
        return ""
    top = max(max(values), 1)
    step = 90 / (len(values) - 1)
    pts = " ".join(f"{i * step:.1f},{22 - 20 * v / top:.1f}" for i, v in enumerate(values))
    last_x, last_y = pts.split()[-1].split(",")
    return (f'<svg class="fx-spark" viewBox="-2 0 96 24"><polyline points="{pts}" fill="none" '
            f'stroke="currentColor" stroke-width="2" stroke-linejoin="round"/>'
            f'<circle cx="{last_x}" cy="{last_y}" r="2.6" fill="currentColor"/></svg>')


def _card(pid, players, weekly, slot=None, on_ir=False):
    p = players.get(pid, {})
    pos = _fantasy_pos(p)
    color = POS_COLORS.get(pos, "#7F8794")
    status = p.get("injury_status") or ""
    pts = weekly.get(pid, {})
    played = [pts[w] for w in sorted(pts)]
    total = sum(played)
    scored = [p for p in played if p]  # la media no cuenta las jornadas en que no jugó (lesión, descanso)
    avg = total / len(scored) if scored else 0
    last = played[-1] if played else 0
    trend = "up" if len(played) > 1 and last >= avg else "down"
    chip = (f'<span class="fx-card-status">{INJURY_ICON.get(status, "")} {_e(status)}</span>' if status else
            '<span class="fx-card-status ok">✔ Disponible</span>')
    badge = slot.replace("_", " ") if slot else ("IR" if on_ir else "BANQUILLO")
    photo = f"https://sleepercdn.com/content/nfl/players/thumb/{pid}.jpg"
    return f"""<div class="fx-card" style="--pos:{color}">
  <div class="fx-card-top">
    <div class="fx-card-photo" style="background-image:url('{photo}'), linear-gradient(135deg, {color}, #1A2233)"></div>
    <div class="fx-card-id">
      <div class="fx-card-name">{'🏥 ' if on_ir else ''}{_e(p.get('full_name') or pid)}</div>
      <div class="fx-card-meta"><span class="fx-pos">{_e(pos)}</span> {_e(p.get('team') or 'FA')}
        {f"· #{_e(p['number'])}" if p.get('number') else ''}</div>
    </div>
    <div class="fx-card-slot">{_e(badge)}</div>
  </div>
  {chip}
  <div class="fx-card-stats">
    <div><b>{avg:.1f}</b><span>Media</span></div>
    <div><b class="{trend}">{last:.1f}</b><span>Última</span></div>
    <div><b>{total:.0f}</b><span>Total</span></div>
    <div class="fx-card-spark {trend}">{_sparkline(played[-6:])}<span>Tendencia</span></div>
  </div>
</div>"""


POS_GROUPS = [("QB", "🎯 Quarterbacks"), ("RB", "🏃 Running backs"), ("WR", "🙌 Wide receivers"),
              ("TE", "💪 Tight ends"), ("K", "🦶 Kickers"), ("DL", "🛡️ Línea defensiva"),
              ("LB", "🧱 Linebackers"), ("DB", "🔒 Secundaria")]


def render_roster(roster, slots, players, weekly):
    """Plantilla como tarjetas agrupadas por posición: en cada grupo, titulares, luego banquillo y luego IR."""
    on_ir = set(roster.get("reserve") or [])
    slot_of = {pid: slot for slot, pid in zip(slots, roster["starters"]) if pid != "0"}
    groups = {pos: [] for pos, _ in POS_GROUPS}
    others = []
    for pid in roster["players"]:
        order = 0 if pid in slot_of else 2 if pid in on_ir else 1
        card = (order, _card(pid, players, weekly, slot=slot_of.get(pid), on_ir=pid in on_ir))
        # Un titular va al grupo de su hueco si es de una posición concreta (p. ej. un DL/LB alineado de LB)
        pos = slot_of.get(pid) if slot_of.get(pid) in groups else _fantasy_pos(players.get(pid, {}))
        groups.get(pos, others).append(card)
    titles = dict(POS_GROUPS)
    html_groups = []
    for pos, cards in list(groups.items()) + [("?", others)]:
        if not cards:
            continue
        starters = sum(1 for o, _ in cards if o == 0)
        html_groups.append(
            f'<div class="fx-group" style="--pos:{POS_COLORS.get(pos, "#7F8794")}">'
            f'<div class="fx-group-title">{titles.get(pos, "Otros")}<span>{len(cards)} · {starters} titular'
            f'{"es" if starters != 1 else ""}</span></div>'
            f'<div class="fx-cards">{"".join(c for _, c in sorted(cards, key=lambda x: x[0]))}</div></div>')
    return "".join(html_groups)


# --- Partidos NFL ----------------------------------------------------------------
DIAS_CORTOS = ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"]
GAME_STATS = ["Puntos por partido", "Yardas por partido", "Yardas de carrera por partido",
              "% conversión en 3er down", "Diferencial de pérdidas"]


def _rank(text):
    m = re.search(r"\d+", text or "")
    return int(m.group()) if m else 99


def _team_block(t, side):
    rec = f"{t['record']} · {'fuera' if side == 'away' else 'en casa'} {t['away_record'] if side == 'away' else t['home_record']}"
    score = f'<div class="fx-g-score">{t["score"]}</div>' if t["score"] is not None else ""
    return f"""<div class="fx-g-team {side}" style="--c:{_e(t['color'])}">
  <div class="fx-g-abbr">{_e(t['abbr'])}</div><div class="fx-g-name">{_e(t['name'])}</div>
  <div class="fx-g-rec">{_e(rec)}</div>{score}
</div>"""


def _stats_compare(a_stats, h_stats):
    rows = []
    for label in GAME_STATS:
        if label not in a_stats or label not in h_stats:
            continue
        (va, ra), (vh, rh) = a_stats[label], h_stats[label]
        wa, wh = _rank(ra) < _rank(rh), _rank(rh) < _rank(ra)
        rows.append(f"""<div class="fx-g-stat">
  <div class="v {'win' if wa else ''}">{_e(va)}<small>{_e(ra)}</small></div>
  <div class="l">{_e(label)}</div>
  <div class="v {'win' if wh else ''}">{_e(vh)}<small>{_e(rh)}</small></div>
</div>""")
    return f'<div class="fx-g-stats">{"".join(rows)}</div>' if rows else ""


def _pick_block(pick, game):
    if not pick:
        return '<div class="fx-g-nopick">🔮 Sin pronóstico todavía</div>'
    a, h = game["away"], game["home"]
    winner = h if pick.get("ganador") == h["abbr"] else a
    conf = max(50, min(95, int(pick.get("confianza") or 50)))
    result = ""
    if game["status"] == "STATUS_FINAL" and a["score"] is not None:
        real = h if (h["score"] or 0) > (a["score"] or 0) else a
        ok = real["abbr"] == winner["abbr"]
        result = (f'<div class="fx-g-result {"ok" if ok else "ko"}">{"✅ ACIERTO" if ok else "❌ FALLO"} · '
                  f'Resultado final {a["abbr"]} {a["score"]} - {h["score"]} {h["abbr"]}</div>')
    args = "".join(f"<li>{_e(x)}</li>" for x in pick.get("argumentos", []))
    stars = ""
    for t in (a, h):
        items = "".join(f'<li><b>{_e(p.get("jugador", ""))}</b> <span class="fx-g-pos">{_e(p.get("posicion", ""))}</span>'
                        f'<br><small>{_e(p.get("motivo", ""))}</small></li>'
                        for p in (pick.get("destacados") or {}).get(t["abbr"], []))
        stars += f'<div class="fx-g-stars" style="--c:{_e(t["color"])}"><div class="h">{_e(t["abbr"])}</div><ul>{items}</ul></div>'
    urls = [str(u) for u in pick.get("fuentes", []) if str(u).startswith("http")]
    sources = "".join(f'<a href="{_e(u)}" target="_blank">{_e(re.sub(r"^https?://(www[.])?", "", u)[:60])}</a>'
                      for u in urls)
    return f"""{result}
<div class="fx-g-pick" style="--c:{_e(winner['color'])}">
  <div class="fx-g-verdict">🏆 Ganador previsto: <b>{_e(winner['name'])}</b>
    <span class="fx-g-marcador">{_e(pick.get('marcador', ''))}</span></div>
  <div class="fx-g-conf"><span style="width:{conf}%"></span></div>
  <div class="fx-g-conf-l">Confianza {conf}%</div>
  <p class="fx-g-sum">{_e(pick.get('resumen', ''))}</p>
  <ul class="fx-g-args">{args}</ul>
  <div class="fx-g-key">🔑 <b>Factor clave:</b> {_e(pick.get('factor_clave', ''))}</div>
  <div class="fx-g-starsrow">{stars}</div>
  <div class="fx-g-experts">🎙️ {_e(pick.get('expertos', ''))}</div>
  {f'<details class="fx-g-src"><summary>📚 Fuentes</summary>{sources}</details>' if sources else ''}
</div>"""


def _advanced(game, stats, fpi_data, summary, strengths_fn):
    """Bloque de estadísticas avanzadas ESPN: predicción, FPI/eficiencias, fortalezas, debilidades y lesiones."""
    a, h = game["away"], game["home"]
    pred = (summary or {}).get("predictor") or {}
    bar = ""
    if pred.get("home") is not None and pred.get("away") is not None:
        pa = pred["away"] / ((pred["away"] + pred["home"]) or 1) * 100
        bar = f"""<div class="fx-g-espn">
  <div class="fx-g-espn-l">📈 Predicción ESPN</div>
  <div class="fx-g-espn-bar"><span style="width:{pa:.1f}%;background:{_e(a['color'])}">{_e(a['abbr'])} {pred['away']:.0f}%</span>
    <span style="width:{100 - pa:.1f}%;background:{_e(h['color'])}">{_e(h['abbr'])} {pred['home']:.0f}%</span></div>
</div>"""

    def col(t):
        f = fpi_data.get(t["id"]) or {}
        strong, weak = strengths_fn(stats.get(t["id"], {}), f)
        units = "".join(f'<span class="fx-u {"good" if (f.get(k) or 99) <= 8 else "bad" if (f.get(k) or 0) >= 25 else ""}">'
                        f'{lbl} {f[k]:.0f}º</span>' for k, lbl in (("off_rank", "Ataque"), ("def_rank", "Defensa"),
                                                                    ("st_rank", "Esp."))
                        if f.get(k))
        fpi_line = (f'<div class="fx-g-fpi">FPI <b>{f["fpi"]:.1f}</b> · {f["fpi_rank"]:.0f}º de la liga · '
                    f'{f["playoffs_pct"]:.0f}% playoffs</div>' if f.get("fpi") is not None else "")
        chips_s = "".join(f'<li>💪 {_e(l)} <b>{r}º</b></li>' for l, _, r in strong[:3]) or "<li>—</li>"
        chips_w = "".join(f'<li>⚠️ {_e(l)} <b>{r}º</b></li>' for l, _, r in weak[:3]) or "<li>—</li>"
        injuries = (summary or {}).get("injuries", {}).get(t["abbr"], [])
        inj = "".join(f'<span class="fx-inj {_e(x["estado"].split()[0].lower())}">{_e(x["jugador"])} '
                      f'<small>{_e(x["posicion"])} · {_e(x["estado"])}</small></span>' for x in injuries[:5])
        return f"""<div class="fx-g-advcol" style="--c:{_e(t['color'])}">
  <div class="fx-g-advh">{_e(t['abbr'])}</div>{fpi_line}<div class="fx-g-units">{units}</div>
  <div class="fx-g-sw"><div class="t">Puntos fuertes</div><ul>{chips_s}</ul></div>
  <div class="fx-g-sw"><div class="t">Puntos débiles</div><ul>{chips_w}</ul></div>
  {f'<div class="fx-g-sw"><div class="t">🚑 Lesiones</div>{inj}</div>' if inj else ''}
</div>"""

    return f"""{bar}<details class="fx-g-adv" open><summary>📊 Estadísticas avanzadas ESPN</summary>
<div class="fx-g-advgrid">{col(a)}{col(h)}</div></details>"""


def render_games(week, games, byes, stats, picks, fpi_data=None, summaries=None, strengths_fn=None):
    """Tarjeta por partido: equipos con sus colores, estadísticas avanzadas, cara a cara y pronóstico de Claude."""
    fpi_data, summaries = fpi_data or {}, summaries or {}
    finals = [g for g in games if g["status"] == "STATUS_FINAL" and str(g["id"]) in picks]
    hits = 0
    for g in finals:
        a, h = g["away"], g["home"]
        real = h["abbr"] if (h["score"] or 0) > (a["score"] or 0) else a["abbr"]
        hits += picks[str(g["id"])].get("ganador") == real
    accuracy = (f'<div class="fx-g-acc">🎯 Aciertos: <b>{hits}/{len(finals)}</b> '
                f'({100 * hits / len(finals):.0f}%)</div>') if finals else ""
    cards = []
    for g in games:
        a, h = g["away"], g["home"]
        line = " · ".join(x for x in (f"📊 Línea: {_e(g['spread'])}" if g["spread"] else "",
                                       f"O/U {_e(g['over_under'])}" if g["over_under"] else "") if x)
        when = g["status_text"] if g["status"] != "STATUS_SCHEDULED" else \
            f"{DIAS_CORTOS[g['kickoff'].weekday()]} {g['kickoff']:%d/%m · %H:%M}"
        cards.append(f"""<div class="fx-game">
  <div class="fx-g-head">
    {_team_block(a, 'away')}
    <div class="fx-g-mid"><div class="fx-g-at">@</div><div class="fx-g-when">{_e(when)}</div>
      <div class="fx-g-tv">{_e(g['tv'])}</div></div>
    {_team_block(h, 'home')}
  </div>
  <div class="fx-g-meta">🏟️ {_e(g['venue'])}{' · ' + line if line else ''}</div>
  {_advanced(g, stats, fpi_data, summaries.get(g['id']), strengths_fn) if strengths_fn else ''}
  {_stats_compare(stats.get(a['id'], {}), stats.get(h['id'], {}))}
  {_pick_block(picks.get(str(g['id'])), g)}
</div>""")
    return f"""<div class="fx-g-top">
  <div><div class="fx-g-title">🏟️ Jornada {week}</div>
  <div class="fx-g-subtitle">{len(games)} partidos{' · Descansan: ' + ', '.join(byes) if byes else ''} · horas de España</div></div>
  {accuracy}
</div>
<div class="fx-games">{''.join(cards)}</div>"""


# --- Enfrentamiento ------------------------------------------------------------
def _side(team, manager, avatar, stats, score, css, projected=None, win=None):
    img = f'<img src="{_e(avatar)}">' if avatar else '<div class="fx-vs-noav">🏈</div>'
    proj = f'<div class="fx-vs-proj">Proyección <b>{projected:.1f}</b></div>' if projected is not None else ""
    pct = f'<div class="fx-vs-pct">{100 * win:.0f}%<small>de victoria</small></div>' if win is not None else ""
    return f"""<div class="fx-vs-side {css}">
  {img}<div class="fx-vs-team">{_e(team)}</div><div class="fx-vs-mgr">{_e(manager)}</div>
  <div class="fx-vs-rec">{stats['w']}-{stats['l']} · {stats['rank']}º</div>
  <div class="fx-vs-score">{score:.2f}</div>{proj}{pct}
</div>"""


def _luminance(hex_color):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.299 * r + 0.587 * g + 0.114 * b


def jersey(colors, number):
    """Camiseta en SVG con los colores del equipo y el dorsal del jugador (como imagen, para que Streamlit no la filtre)."""
    main, alt = colors or ("#4A5D82", "#FFFFFF")
    if abs(_luminance(main) - _luminance(alt)) < 0.25:  # secundario poco visible sobre el principal
        alt = "#FFFFFF" if _luminance(main) < 0.5 else "#1A2233"
    num = _e(str(number)) if number not in (None, "") else ""
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">
  <path d="M20 6 L28 4 Q32 9 36 4 L44 6 L60 16 L54 28 L48 25 L48 60 L16 60 L16 25 L10 28 L4 16 Z"
        fill="{main}" stroke="rgba(0,0,0,0.45)" stroke-width="1.5" stroke-linejoin="round"/>
  <path d="M8 20 L13 24 M56 20 L51 24" stroke="{alt}" stroke-width="3" stroke-linecap="round"/>
  <path d="M28 4 Q32 9 36 4" stroke="{alt}" stroke-width="2.5" fill="none"/>
  <text x="32" y="46" text-anchor="middle" font-family="Arial Black, Arial, sans-serif" font-weight="900"
        font-size="{20 if len(num) > 1 else 24}" fill="{alt}" stroke="rgba(0,0,0,0.35)" stroke-width="0.8">{num}</text>
</svg>"""
    return (f'<img class="fx-jersey" alt="#{num}" '
            f'src="data:image/svg+xml;base64,{base64.b64encode(svg.encode()).decode()}">')


def _state_chip(row):
    state = row["state"]
    if state == "bye":
        return '<span class="fx-st bye">BYE</span>'
    if state == "final":
        return '<span class="fx-st final">FINAL</span>'
    if state == "en juego":
        return '<span class="fx-st live">● EN JUEGO</span>'
    if state == "pendiente":
        k = row["game"]["kickoff"]
        return f'<span class="fx-st next">{DIAS_CORTOS[k.weekday()]} {k:%H:%M}</span>'
    return ""


def _compare(label, a, b, fmt="{:.1f}", lower_is_better=False):
    total = (a + b) or 1
    pa = 50 if a == b else int(100 * a / total)
    if lower_is_better and a != b:
        pa = 100 - pa
    win_a = (a < b) if lower_is_better else (a > b)
    win_b = (b < a) if lower_is_better else (b > a)
    return f"""<div class="fx-cmp">
  <div class="fx-cmp-val {'win' if win_a else ''}">{fmt.format(a)}</div>
  <div class="fx-cmp-mid"><div class="fx-cmp-label">{label}</div>
    <div class="fx-cmp-bar"><span class="a" style="width:{pa}%"></span><span class="b" style="width:{100 - pa}%"></span></div></div>
  <div class="fx-cmp-val {'win' if win_b else ''}">{fmt.format(b)}</div>
</div>"""


def render_matchup(week, slots, players, a, b, win_a, team_colors=None):
    """a / b: dict con team, manager, avatar, matchup (Sleeper), stats (season_table) y outlook (proyecciones).
    win_a: probabilidad de victoria de a. team_colors: {abreviatura NFL: (principal, secundario)}."""
    team_colors = team_colors or {}
    sa, sb = a["matchup"].get("points") or 0, b["matchup"].get("points") or 0
    oa, ob = a["outlook"], b["outlook"]
    if sa == sb == 0:
        status = "🕒 Aún no ha empezado la jornada · los puntos irán sumando en directo"
    elif sa == sb:
        status = "⚖️ Empate en el marcador"
    else:
        leader = a if sa > sb else b
        status = f"🔥 Va ganando <b>{_e(leader['team'])}</b> por {abs(sa - sb):.2f}"
    fav = a if win_a >= 0.5 else b
    verdict = (f"🔮 Proyección final: <b>{oa['final']:.1f} – {ob['final']:.1f}</b> · "
               f"favorito <b>{_e(fav['team'])}</b> ({100 * max(win_a, 1 - win_a):.0f}%)")
    win_bar = f"""<div class="fx-wp">
  <div class="fx-wp-bar"><span class="a" style="width:{100 * win_a:.1f}%">{100 * win_a:.0f}%</span>
    <span class="b" style="width:{100 - 100 * win_a:.1f}%">{100 - 100 * win_a:.0f}%</span></div>
  <div class="fx-wp-l">Probabilidad de victoria según las proyecciones y los puntos ya conseguidos</div>
</div>"""

    # Avisos: titulares que no van a jugar (bye) o están descartados
    warnings = []
    for side in (a, b):
        dead = [r for r in side["outlook"]["rows"] if r["pid"] and (
            r["state"] == "bye" or (players.get(r["pid"], {}).get("injury_status") in ("Out", "IR", "PUP", "Sus")
                                    and r["state"] == "pendiente"))]
        if dead:
            names = ", ".join(f"{players.get(r['pid'], {}).get('full_name', r['pid'])} "
                              f"({'bye' if r['state'] == 'bye' else players[r['pid']]['injury_status']})" for r in dead)
            warnings.append(f"⚠️ <b>{_e(side['team'])}</b> tiene titulares que no sumarán: {_e(names)}")
    alert = f'<div class="fx-vs-alert">{"<br>".join(warnings)}</div>' if warnings else ""

    ga, gb = max(len(a["stats"]["res"]), 1), max(len(b["stats"]["res"]), 1)
    tape = "".join([
        _compare("Puntos por jornada", a["stats"]["pf"] / ga, b["stats"]["pf"] / gb),
        _compare("Puntos a favor", a["stats"]["pf"], b["stats"]["pf"]),
        _compare("Puntos en contra", a["stats"]["pa"], b["stats"]["pa"], lower_is_better=True),
        _compare("Victorias", a["stats"]["w"], b["stats"]["w"], fmt="{:.0f}"),
    ])

    duels = []
    for ra, rb in zip(oa["rows"], ob["rows"]):
        def player(r, side, won):
            if not r["pid"]:
                return f'<div class="fx-du-player {side} empty">— vacío —</div>'
            p = players.get(r["pid"], {})
            inj = INJURY_ICON.get(p.get("injury_status") or "", "")
            team = p.get("team") or ""
            shirt = jersey(team_colors.get({"WAS": "WSH"}.get(team, team)), p.get("number"))
            text = (f'<div class="t"><div class="n">{_e(p.get("full_name") or r["pid"])} {inj}</div>'
                    f'<div class="m">{_e(p.get("position", ""))} · {_e(team or "FA")} {_state_chip(r)}</div></div>')
            classes = f'fx-du-player {side}{" dead" if r["state"] == "bye" else ""}{" won" if won else ""}'
            # La camiseta va en el lado libre de la tarjeta: a la izquierda en tu equipo, a la derecha en el rival
            return f'<div class="{classes}">{shirt + text if side == "a" else text + shirt}</div>'

        def numbers(r, win, side):
            act = f'<div class="fx-du-num act"><b>{r["actual"]:.1f}</b><small>Actual</small></div>'
            proj = f'<div class="fx-du-num proj{" win" if win else ""}"><b>{r["final"]:.1f}</b><small>Proyección</small></div>'
            return act + proj if side == "a" else proj + act
        # Gana el duelo quien más puntos suma al final (antes del partido, quien más proyecta)
        wa, wb = ra["final"] > rb["final"], rb["final"] > ra["final"]
        winner = "a" if wa else "b" if wb else "tie"
        arrow = "◀ GANA" if wa else "GANA ▶" if wb else "= EMPATE"
        duels.append(f"""<div class="fx-du-row">
  {player(ra, 'a', wa)}{numbers(ra, wa, 'a')}
  <div class="fx-du-slot {winner}"><span class="pos">{_e(ra['slot'].replace('_', ' '))}</span><span class="w">{arrow}</span></div>
  {numbers(rb, wb, 'b')}{player(rb, 'b', wb)}
</div>""")
    won_a = sum(1 for ra, rb in zip(oa["rows"], ob["rows"]) if ra["final"] > rb["final"])
    won_b = sum(1 for ra, rb in zip(oa["rows"], ob["rows"]) if rb["final"] > ra["final"])

    return f"""<div class="fx-vs">
  <div class="fx-vs-banner">
    {_side(a['team'], a['manager'], a['avatar'], a['stats'], sa, 'left', oa['final'], win_a)}
    <div class="fx-vs-center"><div class="fx-vs-week">SEMANA {week}</div><div class="fx-vs-badge">VS</div></div>
    {_side(b['team'], b['manager'], b['avatar'], b['stats'], sb, 'right', ob['final'], 1 - win_a)}
  </div>
  {win_bar}
  <div class="fx-vs-status">{status}<br>{verdict}</div>
  {alert}
  <div class="fx-vs-section">⚔️ Duelos puesto a puesto <span class="fx-vs-count">{won_a} – {won_b} en proyección</span></div>
  <div class="fx-du">{''.join(duels)}</div>
  <div class="fx-vs-section">📊 Cara a cara en la temporada</div>
  <div class="fx-cmp-box">{tape}</div>
  <div class="fx-legend">Actual: puntos conseguidos esta jornada · Proyección: puntos finales esperados (lo ya
  sumado + lo previsto para lo que queda de su partido) · La flecha del centro señala quién gana ese duelo.
  Proyecciones de Sleeper/Rotowire calculadas con la puntuación de tu liga.</div>
</div>"""


# --- Matchups de toda la liga (estilo Sleeper) -----------------------------------
def _mu_team(side, win, align):
    img = f'<img src="{_e(side["avatar"])}">' if side["avatar"] else '<span class="fx-mu-noav">🏈</span>'
    st_ = side["stats"]
    info = (f'<div class="fx-mu-info"><b>{_e(side["team"])}</b>'
            f'<small>{_e(side["manager"])} · {st_["w"]}-{st_["l"]} · {st_["rank"]}º</small></div>')
    return f'<div class="fx-mu-team {align}{" fav" if win >= 0.5 else ""}">{img + info if align == "l" else info + img}</div>'


def render_league_matchups(week, cards, my_rid):
    """cards: [(matchup_id, lado_a, lado_b, prob_victoria_a, es_del_equipo_seleccionado)]."""
    out = []
    for _, a, b, win_a, selected in cards:
        sa, sb = a["matchup"].get("points") or 0, b["matchup"].get("points") or 0
        pa, pb = a["outlook"]["final"], b["outlook"]["final"]
        fav = max(win_a, 1 - win_a)
        if fav >= 0.85:
            tag = '<span class="fx-mu-tag boom">💣 Paliza prevista</span>'
        elif fav <= 0.6:
            tag = '<span class="fx-mu-tag close">🔥 Duelo igualado</span>'
        else:
            tag = ""
        live = any(r["state"] in ("en juego", "final") for r in a["outlook"]["rows"] + b["outlook"]["rows"])
        lead_a, lead_b = (sa > sb, sb > sa) if live else (pa > pb, pb > pa)
        mine = " mine" if my_rid in (a["roster_id"], b["roster_id"]) else ""
        out.append(f"""<div class="fx-mu{' sel' if selected else ''}{mine}">
  {tag}
  <div class="fx-mu-main">
    {_mu_team(a, win_a, 'l')}
    <div class="fx-mu-score">
      <div class="fx-mu-pts"><span class="{'lead' if lead_a else ''}">{sa:.1f}</span><i>–</i><span class="{'lead' if lead_b else ''}">{sb:.1f}</span></div>
      <div class="fx-mu-proj">Proy. <b>{pa:.1f}</b> – <b>{pb:.1f}</b></div>
    </div>
    {_mu_team(b, 1 - win_a, 'r')}
  </div>
  <div class="fx-mu-bar"><span class="a" style="width:{100 * win_a:.1f}%">{100 * win_a:.0f}%</span>
    <span class="b" style="width:{100 - 100 * win_a:.1f}%">{100 - 100 * win_a:.0f}%</span></div>
</div>""")
    return f"""<div class="fx-mu-top"><div class="fx-mu-title">💣 Matchups · Semana {week}</div>
  <div class="fx-mu-sub">Todos los enfrentamientos de la liga · puntos en directo, proyección y % de victoria</div></div>
<div class="fx-mus">{''.join(out)}</div>"""


CSS = """
<style>
/* ---------- Matchups de la liga ---------- */
.fx-mu-top { margin-bottom: 14px; }
.fx-mu-title { font-family: 'Oswald', sans-serif; font-size: 1.7rem; color: #FFFFFF; text-transform: uppercase; letter-spacing: 0.05em; }
.fx-mu-sub { color: #A9B6CC; font-size: 0.85rem; }
.fx-mus { display: grid; grid-template-columns: repeat(auto-fill, minmax(460px, 1fr)); gap: 14px; margin-bottom: 18px; }
.fx-mu { position: relative; border-radius: 16px; padding: 14px 16px 12px;
         background: linear-gradient(160deg, rgba(255, 255, 255, 0.10), rgba(255, 255, 255, 0.03));
         border: 1px solid rgba(255, 255, 255, 0.18); box-shadow: 0 6px 18px rgba(0, 0, 0, 0.3);
         transition: transform 0.15s ease; }
.fx-mu:hover { transform: translateY(-3px); }
.fx-mu.sel { border: 2px solid #FFD23F; box-shadow: 0 0 0 1px #FFD23F, 0 8px 22px rgba(255, 210, 63, 0.25); }
.fx-mu-tag { position: absolute; top: -10px; left: 50%; transform: translateX(-50%); font-size: 0.68rem; font-weight: 800;
             padding: 2px 10px; border-radius: 999px; white-space: nowrap; letter-spacing: 0.04em; }
.fx-mu-tag.boom { background: #D9480F; color: #FFFFFF; box-shadow: 0 0 10px rgba(217, 72, 15, 0.7); }
.fx-mu-tag.close { background: #FFD23F; color: #1A2233; box-shadow: 0 0 10px rgba(255, 210, 63, 0.6); }
.fx-mu-main { display: grid; grid-template-columns: minmax(0, 1fr) auto minmax(0, 1fr); align-items: center; gap: 10px; }
.fx-mu-team { display: flex; align-items: center; gap: 10px; min-width: 0; }
.fx-mu-team.r { justify-content: flex-end; text-align: right; }
.fx-mu-team img, .fx-mu-noav { width: 46px; height: 46px; border-radius: 50%; object-fit: cover; flex-shrink: 0;
                               border: 2px solid rgba(255, 255, 255, 0.5); }
.fx-mu-noav { display: flex; align-items: center; justify-content: center; background: rgba(0, 0, 0, 0.3); font-size: 1.3rem; }
.fx-mu-team.l img, .fx-mu-team.l .fx-mu-noav { border-color: #E5252A; }
.fx-mu-team.r img, .fx-mu-team.r .fx-mu-noav { border-color: #1F6FB2; }
.fx-mu-info { min-width: 0; }
.fx-mu-info b { display: block; color: #FFFFFF; font-size: 0.98rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fx-mu-info small { color: #A9B6CC; font-size: 0.7rem; }
.fx-mu-team.fav .fx-mu-info b::after { content: " ★"; color: #FFD23F; }
.fx-mu-score { text-align: center; }
.fx-mu-pts { font-family: 'Oswald', sans-serif; font-size: 1.7rem; color: rgba(255, 255, 255, 0.75); white-space: nowrap; }
.fx-mu-pts i { font-style: normal; margin: 0 6px; color: #7F8BA3; }
.fx-mu-pts .lead { color: #FFFFFF; text-shadow: 0 0 10px rgba(255, 255, 255, 0.35); }
.fx-mu-proj { font-size: 0.72rem; color: #A9B6CC; white-space: nowrap; }
.fx-mu-proj b { color: #FFD23F; font-family: 'Oswald', sans-serif; font-size: 0.95rem; font-weight: 500; }
.fx-mu-bar { display: flex; height: 18px; border-radius: 999px; overflow: hidden; margin-top: 10px;
             border: 1px solid rgba(255, 255, 255, 0.4); }
.fx-mu-bar span { display: flex; align-items: center; justify-content: center; color: #FFFFFF; font-size: 0.7rem;
                  font-weight: 800; white-space: nowrap; overflow: hidden; min-width: 0; }
.fx-mu-bar .a { background: linear-gradient(90deg, #5E1013, #E5252A); }
.fx-mu-bar .b { background: linear-gradient(90deg, #1F6FB2, #10306B); }
@media (max-width: 640px) {
    .fx-mus { grid-template-columns: 1fr; }
    .fx-mu { padding: 14px 10px 10px; }
    .fx-mu-team img, .fx-mu-noav { width: 32px; height: 32px; }
    .fx-mu-info b { font-size: 0.78rem; }
    .fx-mu-info small { display: none; }
    .fx-mu-pts { font-size: 1.2rem; }
}
/* ---------- Clasificación ---------- */
.fx-standings td { vertical-align: middle; }
.fx-standings .fx-rank { font-family: 'Oswald', sans-serif; font-size: 1.25rem; text-align: center; width: 44px; }
.fx-standings tr.fx-in .fx-rank { color: #1E7A46 !important; }
.fx-mv { display: inline-block; min-width: 46px; text-align: center; padding: 2px 8px; border-radius: 999px;
         font-weight: 800; font-size: 0.8rem; }
.fx-mv.up { background: #D4F4DF; color: #157A3E !important; }
.fx-mv.down { background: #FADBDD; color: #B3141C !important; }
.fx-mv.same { color: #9AA1AC !important; }
.fx-tname { font-weight: 800; color: #1A2233; }
.fx-tmgr { font-size: 0.75rem; color: #5B6575; font-weight: 400; }
.fx-rec { font-family: 'Oswald', sans-serif; font-size: 1.05rem; }
.fx-streak { display: inline-block; padding: 2px 9px; border-radius: 6px; font-weight: 800; font-size: 0.8rem; color: #FFFFFF !important; }
.fx-streak.V { background: #2E8B57; } .fx-streak.D { background: #C0262C; } .fx-streak.E { background: #7F8794; }
.fx-dot { display: inline-block; width: 11px; height: 11px; border-radius: 50%; margin-right: 4px; background: #9AA1AC; }
.fx-dot.V { background: #2E8B57; } .fx-dot.D { background: #C0262C; }
.fx-standings tr.fx-sel td { background: #FFF4D6 !important; }
.fx-standings tr.fx-sel td:first-child { box-shadow: inset 5px 0 0 #E5A200; }
.fx-po-line td {
    background: repeating-linear-gradient(90deg, #C0262C 0 10px, transparent 10px 18px) bottom / 100% 2px no-repeat,
                #F7E3E4 !important;
    color: #B3141C !important; font-weight: 800; font-size: 0.72rem; text-transform: uppercase;
    letter-spacing: 0.12em; text-align: center; padding: 4px !important;
}
.fx-legend { font-size: 0.8rem; color: #D6DDE8; margin-top: -4px; }
.fx-legend .fx-dot { width: 9px; height: 9px; margin: 0 2px 0 8px; }

/* ---------- Mercado de waivers ---------- */
.fx-market {
    background: linear-gradient(180deg, #0B1120, #111A2E); border: 1px solid #2A3A5C; border-radius: 16px;
    padding: 16px 18px; box-shadow: 0 8px 26px rgba(0, 0, 0, 0.45); font-family: 'Consolas', 'Courier New', monospace;
}
.fx-mk-head { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.fx-mk-title { font-family: 'Oswald', sans-serif; font-size: 1.5rem; letter-spacing: 0.08em; color: #FFFFFF; flex: 1; }
@keyframes fx-blink { 0%, 100% { opacity: 1; } 50% { opacity: 0.2; } }
.fx-live { display: inline-block; width: 11px; height: 11px; border-radius: 50%; background: #FF3B3B;
           box-shadow: 0 0 10px #FF3B3B; animation: fx-blink 1.2s infinite; margin-right: 6px; }
.fx-mk-chip { background: #16223A; border: 1px solid #2E4470; border-radius: 10px; padding: 6px 12px;
              color: #B8C4D9; font-size: 0.85rem; text-align: center; }
.fx-mk-chip b { color: #FFD23F; font-size: 1.05rem; margin-left: 4px; }
.fx-mk-chip small { display: block; font-size: 0.7rem; opacity: 0.8; }
@keyframes fx-scroll { from { transform: translateX(0); } to { transform: translateX(-50%); } }
.fx-tape { overflow: hidden; white-space: nowrap; background: #050A14; border-top: 1px solid #1F2E4D;
           border-bottom: 1px solid #1F2E4D; padding: 6px 0; margin-bottom: 12px; }
.fx-tape-inner { display: inline-block; animation: fx-scroll 40s linear infinite; }
.fx-tick { margin: 0 22px; color: #B8C4D9; font-size: 0.85rem; }
.fx-tick b { color: #FFFFFF; }
.fx-tick i { font-style: normal; font-weight: 700; }
.fx-tick i.up { color: #2BD576; } .fx-tick i.down { color: #FF4D4D; }
.fx-mk-scroll { overflow-x: auto; }
.fx-mk-table { width: 100%; border-collapse: collapse; background: transparent !important; box-shadow: none !important;
               border: none !important; font-size: 0.9rem; }
.fx-mk-table th { background: #16223A !important; color: #8FA3C7 !important; border: none !important;
                  border-bottom: 1px solid #2E4470 !important; font-size: 0.72rem; letter-spacing: 0.1em; }
.fx-mk-table td { background: transparent !important; color: #DCE4F2 !important; border: none !important;
                  border-bottom: 1px solid #1C2A45 !important; padding: 9px 12px; }
.fx-mk-table tbody tr:nth-child(even) td { background: rgba(255, 255, 255, 0.02) !important; }
.fx-mk-table tbody tr:hover td { background: rgba(43, 213, 118, 0.08) !important; }
.fx-mk-rank { color: #6F84AB !important; text-align: center; }
.fx-mk-name { font-weight: 700; color: #FFFFFF; font-family: 'Segoe UI', sans-serif; }
.fx-mk-sub { font-size: 0.75rem; color: #8FA3C7; }
.fx-mk-up { color: #2BD576 !important; font-weight: 700; }
.fx-mk-down { color: #FF4D4D !important; font-weight: 700; }
.fx-bar { height: 5px; background: #1C2A45; border-radius: 3px; margin-top: 4px; width: 110px; }
.fx-bar span { display: block; height: 100%; border-radius: 3px; background: linear-gradient(90deg, #1E9E57, #2BD576); }
.fx-sig { display: inline-block; padding: 3px 9px; border-radius: 6px; font-size: 0.75rem; font-weight: 800;
          font-family: 'Segoe UI', sans-serif; white-space: nowrap; }
.fx-sig.hot { background: rgba(255, 122, 0, 0.18); color: #FF9A3C !important; border: 1px solid #FF7A00; }
.fx-sig.buy { background: rgba(43, 213, 118, 0.14); color: #2BD576 !important; border: 1px solid #1E9E57; }
.fx-sig.watch { background: rgba(143, 163, 199, 0.12); color: #B8C4D9 !important; border: 1px solid #4A5D82; }
.fx-sig.risk { background: rgba(255, 210, 63, 0.12); color: #FFD23F !important; border: 1px solid #B8961F; }
.fx-mk-foot { font-size: 0.72rem; color: #6F84AB; margin-top: 10px; }

/* ---------- Enfrentamiento ---------- */
.fx-vs-banner {
    display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; border-radius: 18px; overflow: hidden;
    background: linear-gradient(105deg, #9B1C1F 0%, #5E1013 45%, #0B1426 50%, #10306B 55%, #1F6FB2 100%);
    border: 2px solid rgba(255, 255, 255, 0.5); box-shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
}
.fx-vs-side { padding: 22px 16px; text-align: center; }
.fx-vs-side img, .fx-vs-noav { width: 76px; height: 76px; border-radius: 50%; border: 3px solid #FFFFFF;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.5); object-fit: cover; margin: 0 auto 8px; }
.fx-vs-noav { display: flex; align-items: center; justify-content: center; font-size: 2.2rem; background: rgba(0, 0, 0, 0.3); }
.fx-vs-team { font-family: 'Oswald', sans-serif; font-size: 1.6rem; font-weight: 600; color: #FFFFFF; line-height: 1.1;
              text-transform: uppercase; text-shadow: 0 2px 6px rgba(0, 0, 0, 0.5); }
.fx-vs-mgr { color: rgba(255, 255, 255, 0.75); font-size: 0.85rem; }
.fx-vs-rec { display: inline-block; margin-top: 6px; padding: 2px 10px; border-radius: 999px;
             background: rgba(0, 0, 0, 0.3); color: #FFFFFF; font-size: 0.85rem; font-weight: 700; }
.fx-vs-score { font-family: 'Oswald', sans-serif; font-size: 3rem; font-weight: 600; color: #FFFFFF; line-height: 1.1;
               margin-top: 6px; text-shadow: 0 3px 10px rgba(0, 0, 0, 0.6); }
.fx-vs-center { text-align: center; padding: 0 6px; }
.fx-vs-week { font-size: 0.7rem; letter-spacing: 0.2em; color: rgba(255, 255, 255, 0.8); font-weight: 800; margin-bottom: 6px; }
@keyframes fx-pulse { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.1); } }
.fx-vs-badge {
    width: 78px; height: 78px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
    font-family: 'Oswald', sans-serif; font-size: 2rem; font-weight: 600; color: #1A2233;
    background: radial-gradient(circle at 35% 30%, #FFF6C9, #FFD23F 55%, #C99A00); border: 4px solid #FFFFFF;
    box-shadow: 0 0 25px rgba(255, 210, 63, 0.8); animation: fx-pulse 1.6s ease-in-out infinite;
}
.fx-vs-status { text-align: center; margin: 14px 0 6px; font-size: 1.05rem; color: #FFFFFF; }
.fx-vs-section { font-family: 'Oswald', sans-serif; font-size: 1.15rem; letter-spacing: 0.08em; text-transform: uppercase;
                 color: #FFFFFF; margin: 22px 0 10px; padding-bottom: 6px; border-bottom: 1px solid rgba(255, 255, 255, 0.2); }
.fx-cmp-box { background: rgba(255, 255, 255, 0.06); border: 1px solid rgba(255, 255, 255, 0.18); border-radius: 14px; padding: 8px 16px; }
.fx-cmp { display: grid; grid-template-columns: 90px 1fr 90px; align-items: center; gap: 12px; padding: 8px 0; }
.fx-cmp + .fx-cmp { border-top: 1px solid rgba(255, 255, 255, 0.08); }
.fx-cmp-val { font-family: 'Oswald', sans-serif; font-size: 1.2rem; color: rgba(255, 255, 255, 0.7); text-align: center; }
.fx-cmp-val.win { color: #FFD23F; font-size: 1.35rem; }
.fx-cmp-label { text-align: center; font-size: 0.75rem; letter-spacing: 0.1em; text-transform: uppercase; color: #D6DDE8; margin-bottom: 4px; }
.fx-cmp-bar { display: flex; height: 10px; border-radius: 999px; overflow: hidden; background: rgba(0, 0, 0, 0.3); }
.fx-cmp-bar .a { background: linear-gradient(90deg, #5E1013, #E5252A); }
.fx-cmp-bar .b { background: linear-gradient(90deg, #1F6FB2, #10306B); }
.fx-duels { width: 100%; border-collapse: separate !important; border-spacing: 0 6px !important;
             background: transparent !important; box-shadow: none !important; border: none !important; }
.fx-duels td { padding: 8px 12px; border: none !important; color: #1A2233 !important; }
.fx-duels .fx-d-player { background: #E9ECF0 !important; width: 38%; font-weight: 400 !important; }
.fx-duels .fx-d-player.left { text-align: right; border-radius: 10px 0 0 10px; border-left: 5px solid #C0262C !important; }
.fx-duels .fx-d-player:not(.left) { border-radius: 0 10px 10px 0; border-right: 5px solid #1F6FB2 !important; }
.fx-duels .fx-d-player small { display: block; font-size: 0.72rem; color: #5B6575; }
.fx-duels .fx-d-pts { background: #DDE2E8 !important; font-family: 'Oswald', sans-serif; font-size: 1.1rem; text-align: center; width: 9%; }
.fx-duels .win { background: #D4F4DF !important; }
.fx-duels .fx-d-pts.win { color: #157A3E !important; font-weight: 600; }
.fx-duels .fx-d-slot { background: #1A2233 !important; color: #FFFFFF !important; text-align: center; font-weight: 800;
                       font-size: 0.75rem; letter-spacing: 0.06em; width: 6%; }
.fx-empty { color: #9AA1AC; font-style: italic; }

/* ---------- Mi equipo: tarjetas ---------- */
.fx-group { margin-bottom: 22px; }
.fx-group-title { font-family: 'Oswald', sans-serif; font-size: 1.25rem; letter-spacing: 0.06em; text-transform: uppercase;
                  color: #FFFFFF; margin-bottom: 10px; display: flex; align-items: center; gap: 10px;
                  padding-left: 10px; border-left: 5px solid var(--pos, #7F8794); }
.fx-group-title span { font-family: 'Segoe UI', sans-serif; font-size: 0.75rem; background: rgba(255, 255, 255, 0.18);
                       padding: 1px 9px; border-radius: 999px; }
.fx-cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px; }
.fx-card {
    background: #E9ECF0; border-radius: 14px; overflow: hidden; border-top: 5px solid var(--pos);
    box-shadow: 0 5px 16px rgba(0, 0, 0, 0.3); padding: 12px 14px; transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.fx-card:hover { transform: translateY(-3px); box-shadow: 0 10px 24px rgba(0, 0, 0, 0.4); }
.fx-card-top { display: flex; align-items: center; gap: 10px; }
.fx-card-photo { width: 52px; height: 52px; border-radius: 50%; flex-shrink: 0; background-size: cover, cover;
                 background-position: center top, center; border: 3px solid var(--pos); }
.fx-card-id { flex: 1; min-width: 0; }
.fx-card-name { font-weight: 800; color: #1A2233; font-size: 1rem; line-height: 1.2;
                white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fx-card-meta { font-size: 0.78rem; color: #5B6575; margin-top: 2px; }
.fx-pos { display: inline-block; background: var(--pos); color: #FFFFFF; font-weight: 800; font-size: 0.7rem;
          padding: 1px 7px; border-radius: 5px; margin-right: 3px; }
.fx-card-slot { font-size: 0.65rem; font-weight: 800; letter-spacing: 0.06em; color: #FFFFFF; background: #1A2233;
                padding: 3px 8px; border-radius: 6px; white-space: nowrap; }
.fx-card-status { display: inline-block; margin: 9px 0 6px; font-size: 0.75rem; font-weight: 700; padding: 2px 9px;
                  border-radius: 999px; background: #FDECC8; color: #8A5A00; }
.fx-card-status.ok { background: #D4F4DF; color: #157A3E; }
.fx-card-stats { display: grid; grid-template-columns: 1fr 1fr 1fr 1.4fr; gap: 6px; border-top: 1px solid #D3D8DF; padding-top: 8px; }
.fx-card-stats > div { text-align: center; }
.fx-card-stats b { display: block; font-family: 'Oswald', sans-serif; font-size: 1.15rem; font-weight: 500; color: #1A2233; }
.fx-card-stats b.up { color: #157A3E; } .fx-card-stats b.down { color: #B3141C; }
.fx-card-stats span { font-size: 0.62rem; letter-spacing: 0.06em; text-transform: uppercase; color: #5B6575; }
.fx-card-spark.up { color: #2E8B57; } .fx-card-spark.down { color: #C0262C; }
.fx-spark { width: 100%; height: 24px; display: block; }
.fx-summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin-bottom: 20px; }
.fx-summary > div { background: linear-gradient(180deg, rgba(255, 255, 255, 0.2), rgba(255, 255, 255, 0.1));
                    border: 1px solid rgba(255, 255, 255, 0.3); border-radius: 12px; padding: 10px 14px; text-align: center; }
.fx-summary b { display: block; font-family: 'Oswald', sans-serif; font-size: 1.5rem; font-weight: 500; color: #FFFFFF; }
.fx-summary span { font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase; color: #D6DDE8; }

/* ---------- Clasificación tipo marcador de liga ---------- */
.fx-lb { display: flex; flex-direction: column; gap: 7px; margin-bottom: 10px; }
.fx-lb-head, .fx-lb-row { display: grid; grid-template-columns: 52px 48px minmax(170px, 2.2fr) 1fr 1.8fr 1.3fr;
                          align-items: center; gap: 10px; }
.fx-lb-head { padding: 0 14px; font-size: 0.68rem; letter-spacing: 0.12em; text-transform: uppercase; color: #9FB0CC; }
.fx-lb-row {
    padding: 9px 14px; border-radius: 14px; position: relative; transition: transform 0.15s ease, box-shadow 0.15s ease;
    background: linear-gradient(90deg, rgba(255, 255, 255, 0.10), rgba(255, 255, 255, 0.04));
    border: 1px solid rgba(255, 255, 255, 0.14); border-left: 6px solid #4A5D82;
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.25);
}
.fx-lb-row:hover { transform: translateX(4px); box-shadow: 0 6px 16px rgba(0, 0, 0, 0.35); }
.fx-lb-row.in { border-left-color: #2BD576; background: linear-gradient(90deg, rgba(43, 213, 118, 0.16), rgba(255, 255, 255, 0.04)); }
.fx-lb-row.last { border-left-color: #E5252A; background: linear-gradient(90deg, rgba(229, 37, 42, 0.18), rgba(255, 255, 255, 0.03)); }
.fx-lb-row.sel { border-color: #FFD23F; box-shadow: 0 0 0 2px #FFD23F, 0 6px 18px rgba(255, 210, 63, 0.25); }
.fx-lb-rank { font-family: 'Oswald', sans-serif; font-size: 1.4rem; color: #FFFFFF; text-align: center;
              width: 40px; height: 40px; line-height: 40px; border-radius: 50%; background: rgba(0, 0, 0, 0.3); }
.fx-lb-rank.r1, .fx-lb-rank.r2, .fx-lb-rank.r3 { font-size: 1.6rem; background: transparent; }
.fx-lb-mv { font-weight: 800; font-size: 0.8rem; text-align: center; padding: 2px 6px; border-radius: 999px; }
.fx-lb-mv.up { background: rgba(43, 213, 118, 0.2); color: #2BD576; }
.fx-lb-mv.down { background: rgba(229, 37, 42, 0.22); color: #FF6B6B; }
.fx-lb-mv.same { color: #7F8BA3; }
.fx-lb-team { display: flex; align-items: center; gap: 10px; min-width: 0; }
.fx-lb-team img, .fx-lb-noav { width: 40px; height: 40px; border-radius: 50%; object-fit: cover; flex-shrink: 0;
                               border: 2px solid rgba(255, 255, 255, 0.6); }
.fx-lb-noav { display: flex; align-items: center; justify-content: center; background: rgba(0, 0, 0, 0.3); font-size: 1.2rem; }
.fx-lb-team b { display: block; color: #FFFFFF; font-size: 1rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fx-lb-team small, .fx-lb-rec small, .fx-lb-pf small { display: block; color: #A9B6CC; font-size: 0.72rem; }
.fx-lb-rec b { font-family: 'Oswald', sans-serif; font-size: 1.35rem; font-weight: 500; color: #FFFFFF; }
.fx-lb-pts { display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }
.fx-lb-pts > div { text-align: center; background: rgba(0, 0, 0, 0.25); border-radius: 8px; padding: 3px 4px; }
.fx-lb-pts b { display: block; font-family: 'Oswald', sans-serif; font-size: 1.05rem; font-weight: 500; color: #FFFFFF; }
.fx-lb-pts small { display: block; font-size: 0.58rem; letter-spacing: 0.08em; text-transform: uppercase; color: #A9B6CC; }
.fx-lb-pts .pos b { color: #2BD576; } .fx-lb-pts .neg b { color: #FF6B6B; }
.fx-lb-form { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.fx-lb-streak { font-weight: 800; font-size: 0.78rem; padding: 2px 8px; border-radius: 6px; color: #FFFFFF; }
.fx-lb-streak.V { background: #1E7A46; } .fx-lb-streak.D { background: #A3171C; } .fx-lb-streak.E { background: #5B6575; }
.fx-lb-dots .fx-dot { margin-right: 3px; }
.fx-lb-line { display: flex; align-items: center; gap: 10px; margin: 4px 0; color: #FFD23F; font-weight: 800;
              font-size: 0.72rem; letter-spacing: 0.14em; }
.fx-lb-line::before, .fx-lb-line::after { content: ""; flex: 1; height: 0; border-top: 2px dashed #FFD23F;
                                          filter: drop-shadow(0 0 4px rgba(255, 210, 63, 0.7)); }

/* ---------- Enfrentamiento: proyección y probabilidad ---------- */
.fx-vs-proj { color: rgba(255, 255, 255, 0.85); font-size: 0.85rem; }
.fx-vs-proj b { color: #FFD23F; font-family: 'Oswald', sans-serif; font-size: 1.1rem; }
.fx-vs-pct { display: inline-block; margin-top: 6px; padding: 3px 12px; border-radius: 999px; background: rgba(0, 0, 0, 0.35);
             border: 1px solid rgba(255, 255, 255, 0.5); color: #FFFFFF; font-family: 'Oswald', sans-serif; font-size: 1.2rem; }
.fx-vs-pct small { font-family: 'Segoe UI', sans-serif; font-size: 0.65rem; margin-left: 4px; opacity: 0.8; }
.fx-wp { margin: 14px 0 4px; }
.fx-wp-bar { display: flex; height: 30px; border-radius: 999px; overflow: hidden; border: 2px solid rgba(255, 255, 255, 0.6);
             box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35); }
.fx-wp-bar span { display: flex; align-items: center; justify-content: center; color: #FFFFFF; font-family: 'Oswald', sans-serif;
                  font-size: 1rem; white-space: nowrap; overflow: hidden; min-width: 0; }
.fx-wp-bar .a { background: linear-gradient(90deg, #5E1013, #E5252A); }
.fx-wp-bar .b { background: linear-gradient(90deg, #1F6FB2, #10306B); }
.fx-wp-l { text-align: center; font-size: 0.72rem; color: #A9B6CC; margin-top: 4px; }
.fx-vs-alert { background: rgba(255, 210, 63, 0.12); border: 1px solid #FFD23F; border-radius: 12px; padding: 8px 14px;
               color: #FFFFFF; font-size: 0.88rem; margin: 10px 0; line-height: 1.6; }
.fx-vs-count { float: right; font-family: 'Segoe UI', sans-serif; font-size: 0.8rem; letter-spacing: 0; text-transform: none;
               background: rgba(255, 255, 255, 0.12); padding: 2px 10px; border-radius: 999px; }
/* Duelos puesto a puesto: [jugador A][actual][proyección][hueco][proyección][actual][jugador B] */
.fx-du { display: flex; flex-direction: column; gap: 6px; }
.fx-du-row { display: grid; grid-template-columns: minmax(0, 2.4fr) 0.8fr 1fr 82px 1fr 0.8fr minmax(0, 2.4fr);
             align-items: stretch; gap: 5px; }
.fx-du-player { border-radius: 10px; padding: 6px 10px; background: rgba(255, 255, 255, 0.07);
                border: 1px solid rgba(255, 255, 255, 0.12); display: flex; align-items: center; gap: 10px; min-width: 0;
                transition: box-shadow 0.15s ease; }
.fx-du-player .t { flex: 1; min-width: 0; }
.fx-du-player.a { border-left: 5px solid #E5252A; text-align: right; }
.fx-du-player.b { border-right: 5px solid #1F6FB2; }
.fx-du-player.a.won { background: linear-gradient(270deg, rgba(229, 37, 42, 0.30), rgba(229, 37, 42, 0.06));
                      box-shadow: 0 0 0 1px rgba(229, 37, 42, 0.7); }
.fx-du-player.b.won { background: linear-gradient(90deg, rgba(31, 111, 178, 0.38), rgba(31, 111, 178, 0.08));
                      box-shadow: 0 0 0 1px rgba(31, 111, 178, 0.8); }
.fx-jersey { width: 40px; height: 40px; flex-shrink: 0; filter: drop-shadow(0 2px 3px rgba(0, 0, 0, 0.5)); }
.fx-du-player .n { color: #FFFFFF; font-weight: 700; font-size: 0.92rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.fx-du-player .m { color: #A9B6CC; font-size: 0.72rem; margin-top: 2px; }
.fx-du-player.dead { background: rgba(229, 37, 42, 0.18); border-color: rgba(229, 37, 42, 0.5); }
.fx-du-player.dead .n { text-decoration: line-through; opacity: 0.8; }
.fx-du-player.empty { color: #7F8BA3; font-style: italic; justify-content: center; }
.fx-du-num { border-radius: 10px; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 4px 2px; }
.fx-du-num b { font-family: 'Oswald', sans-serif; font-weight: 500; line-height: 1.1; }
.fx-du-num small { font-size: 0.55rem; letter-spacing: 0.1em; text-transform: uppercase; color: #A9B6CC; }
.fx-du-num.act { background: rgba(0, 0, 0, 0.3); }
.fx-du-num.act b { font-size: 1.15rem; color: #FFFFFF; }
.fx-du-num.proj { background: rgba(255, 210, 63, 0.10); border: 1px solid rgba(255, 210, 63, 0.35); }
.fx-du-num.proj b { font-size: 1.45rem; color: #FFD23F; }
.fx-du-num.proj.win { background: rgba(43, 213, 118, 0.18); border-color: #2BD576; box-shadow: 0 0 10px rgba(43, 213, 118, 0.35); }
.fx-du-num.proj.win b { color: #2BD576; }
/* Casilla central: el color y la flecha señalan quién gana el duelo */
.fx-du-slot { border-radius: 10px; border: 2px solid rgba(255, 255, 255, 0.3); color: #FFFFFF; background: #0B1426;
              display: flex; flex-direction: column; align-items: center; justify-content: center; text-align: center; padding: 2px; }
.fx-du-slot .pos { font-weight: 800; font-size: 0.66rem; letter-spacing: 0.05em; }
.fx-du-slot .w { font-family: 'Oswald', sans-serif; font-size: 0.72rem; letter-spacing: 0.06em; margin-top: 2px;
                 padding: 0 6px; border-radius: 999px; background: rgba(0, 0, 0, 0.35); white-space: nowrap; }
.fx-du-slot.a { background: linear-gradient(135deg, #E5252A, #7A1518); border-color: #FFFFFF;
                box-shadow: -4px 0 14px rgba(229, 37, 42, 0.6); }
.fx-du-slot.b { background: linear-gradient(135deg, #2E86D4, #10306B); border-color: #FFFFFF;
                box-shadow: 4px 0 14px rgba(31, 111, 178, 0.7); }
.fx-du-slot.tie { background: #3B4556; }
.fx-du-slot.tie .w { color: #D6DDE8; }
@media (max-width: 640px) {
    .fx-du-row { grid-template-columns: minmax(0, 1fr) 0.9fr 52px 0.9fr minmax(0, 1fr); gap: 3px; }
    .fx-du-num.act { display: none; }
    .fx-du-player { padding: 5px 6px; }
    .fx-du-player .n { font-size: 0.72rem; }
    .fx-du-player .m { font-size: 0.6rem; }
    .fx-du-num.proj b { font-size: 1.05rem; }
    .fx-du-slot .pos { font-size: 0.5rem; }
    .fx-du-slot .w { font-size: 0.55rem; padding: 0 3px; }
    .fx-jersey { width: 26px; height: 26px; }
    .fx-du-player { gap: 4px; }
}
.fx-st { display: inline-block; margin-left: 4px; padding: 0 6px; border-radius: 4px; font-size: 0.6rem; font-weight: 800;
         letter-spacing: 0.04em; vertical-align: 1px; color: #FFFFFF !important; }
.fx-st.bye { background: #C0262C; } .fx-st.final { background: #5B6575; }
.fx-st.live { background: #1E9E57; } .fx-st.next { background: #1F6FB2; }
@media (max-width: 640px) {
    .fx-lb-head { display: none; }
    .fx-lb-row { grid-template-columns: 36px 1fr auto; gap: 8px; padding: 8px 10px; }
    .fx-lb-mv, .fx-lb-dots { display: none; }
    .fx-lb-pts { grid-column: 1 / 4; }
    .fx-lb-form { grid-column: 2 / 4; }
    .fx-lb-rank { width: 32px; height: 32px; line-height: 32px; font-size: 1.1rem; }
    .fx-lb-team img, .fx-lb-noav { width: 32px; height: 32px; }
    .fx-vs-pct { font-size: 0.95rem; }
    .fx-vs-count { float: none; display: inline-block; margin-top: 4px; }
}

/* ---------- Partidos NFL ---------- */
.fx-g-top { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 14px; }
.fx-g-title { font-family: 'Oswald', sans-serif; font-size: 1.8rem; color: #FFFFFF; text-transform: uppercase; letter-spacing: 0.05em; }
.fx-g-subtitle { color: #D6DDE8; font-size: 0.85rem; }
.fx-g-acc { background: linear-gradient(135deg, #2E8B57, #145232); border: 2px solid #FFFFFF; border-radius: 12px;
            padding: 8px 16px; color: #FFFFFF; font-size: 1rem; box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35); }
.fx-games { display: grid; grid-template-columns: repeat(auto-fill, minmax(420px, 1fr)); gap: 18px; }
.fx-game { background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.2); border-radius: 16px;
           overflow: hidden; box-shadow: 0 8px 22px rgba(0, 0, 0, 0.35); }
.fx-g-head { display: grid; grid-template-columns: 1fr auto 1fr; align-items: stretch; }
.fx-g-team { padding: 14px 12px; text-align: center; color: #FFFFFF;
             background: linear-gradient(160deg, var(--c), rgba(0, 0, 0, 0.55)); }
.fx-g-abbr { font-family: 'Oswald', sans-serif; font-size: 2.1rem; font-weight: 600; line-height: 1;
             text-shadow: 0 2px 6px rgba(0, 0, 0, 0.5); }
.fx-g-name { font-size: 0.8rem; font-weight: 700; margin-top: 4px; }
.fx-g-rec { font-size: 0.72rem; opacity: 0.85; margin-top: 2px; }
.fx-g-score { font-family: 'Oswald', sans-serif; font-size: 2rem; margin-top: 4px; }
.fx-g-mid { background: #0B1426; padding: 10px 12px; display: flex; flex-direction: column; justify-content: center;
            align-items: center; min-width: 96px; }
.fx-g-at { width: 40px; height: 40px; border-radius: 50%; display: flex; align-items: center; justify-content: center;
           background: radial-gradient(circle at 35% 30%, #FFF6C9, #FFD23F 55%, #C99A00); color: #1A2233;
           font-family: 'Oswald', sans-serif; font-size: 1.3rem; font-weight: 600; border: 2px solid #FFFFFF; }
.fx-g-when { color: #FFFFFF; font-size: 0.75rem; font-weight: 700; margin-top: 6px; text-align: center; }
.fx-g-tv { color: #9CC3FF; font-size: 0.68rem; text-align: center; }
.fx-g-meta { padding: 8px 14px; font-size: 0.8rem; color: #D6DDE8; background: rgba(0, 0, 0, 0.2);
             border-bottom: 1px solid rgba(255, 255, 255, 0.1); }
.fx-g-stats { padding: 8px 14px; }
.fx-g-stat { display: grid; grid-template-columns: 1fr 1.6fr 1fr; align-items: center; padding: 4px 0;
             border-bottom: 1px dashed rgba(255, 255, 255, 0.08); }
.fx-g-stat .l { text-align: center; font-size: 0.68rem; letter-spacing: 0.05em; text-transform: uppercase; color: #D6DDE8; }
.fx-g-stat .v { text-align: center; font-family: 'Oswald', sans-serif; font-size: 1.05rem; color: rgba(255, 255, 255, 0.75); }
.fx-g-stat .v small { display: block; font-family: 'Segoe UI', sans-serif; font-size: 0.62rem; opacity: 0.8; }
.fx-g-stat .v.win { color: #FFD23F; }
.fx-g-nopick { padding: 14px; text-align: center; color: #D6DDE8; font-style: italic; }
.fx-g-result { margin: 10px 14px 0; padding: 6px 10px; border-radius: 8px; font-weight: 800; font-size: 0.85rem; text-align: center; }
.fx-g-result.ok { background: #D4F4DF; color: #157A3E; }
.fx-g-result.ko { background: #FADBDD; color: #B3141C; }
/* Pronóstico: tarjeta oscura con el color del ganador, texto claro y acentos dorados */
.fx-g-pick { margin: 10px 14px 14px; padding: 14px 16px; border-radius: 14px; color: #E8ECF4;
             background: linear-gradient(160deg, rgba(11, 20, 38, 0.92), rgba(22, 34, 59, 0.92));
             border: 1px solid rgba(255, 255, 255, 0.18); border-left: 6px solid var(--c);
             box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.2), 0 6px 16px rgba(0, 0, 0, 0.35); }
.fx-g-pick, .fx-g-pick p, .fx-g-pick li, .fx-g-pick div, .fx-g-pick span, .fx-g-pick b, .fx-g-pick summary { color: #E8ECF4 !important; }
.fx-g-verdict { font-size: 1.02rem; display: flex; justify-content: space-between; align-items: center; gap: 8px; flex-wrap: wrap; }
.fx-g-verdict b { color: #FFD23F !important; font-family: 'Oswald', sans-serif; font-size: 1.15rem; letter-spacing: 0.03em; }
.fx-g-pick .fx-g-marcador { font-family: 'Oswald', sans-serif; font-size: 1.25rem; padding: 1px 12px; border-radius: 8px;
                 background: #FFD23F; color: #1A2233 !important; box-shadow: 0 2px 8px rgba(255, 210, 63, 0.35); }
.fx-g-conf { height: 8px; background: rgba(255, 255, 255, 0.15); border-radius: 999px; margin-top: 10px; overflow: hidden; }
.fx-g-conf span { display: block; height: 100%; background: linear-gradient(90deg, #E5A200, #2BD576); border-radius: 999px; }
.fx-g-pick .fx-g-conf-l { font-size: 0.72rem; font-weight: 700; margin-top: 3px; color: #9FB0CC !important; letter-spacing: 0.05em; }
.fx-g-pick .fx-g-sum { font-weight: 700; margin: 10px 0 6px; font-size: 0.95rem; color: #FFFFFF !important; }
.fx-g-args { margin: 0 0 8px 18px; padding: 0; font-size: 0.86rem; }
.fx-g-args li { margin-bottom: 4px; line-height: 1.4; }
.fx-g-args li::marker { color: #FFD23F; }
.fx-g-key { font-size: 0.86rem; background: rgba(255, 210, 63, 0.12); border: 1px solid rgba(255, 210, 63, 0.45);
            border-radius: 10px; padding: 7px 11px; margin: 8px 0; }
.fx-g-key b { color: #FFD23F !important; }
.fx-g-starsrow { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px; }
.fx-g-stars { background: rgba(255, 255, 255, 0.06); border-radius: 10px; border: 1px solid rgba(255, 255, 255, 0.12);
              border-top: 4px solid var(--c); padding: 7px 10px; }
.fx-g-stars .h { font-family: 'Oswald', sans-serif; font-size: 0.95rem; letter-spacing: 0.08em; color: #FFFFFF !important; }
.fx-g-stars .h::before { content: "⭐ "; }
.fx-g-stars ul { list-style: none; margin: 4px 0 0; padding: 0; font-size: 0.82rem; }
.fx-g-stars li { margin-bottom: 6px; }
.fx-g-stars li b { color: #FFFFFF !important; }
.fx-g-stars small { color: #A9B6CC !important; }
.fx-g-pick .fx-g-pos { display: inline-block; font-size: 0.6rem; font-weight: 800; padding: 0 5px; border-radius: 4px;
            background: #FFD23F; color: #1A2233 !important; vertical-align: 1px; }
.fx-g-pick .fx-g-experts { font-size: 0.82rem; font-style: italic; margin-top: 10px; padding-top: 8px;
                border-top: 1px dashed rgba(255, 255, 255, 0.15); color: #C9D4E6 !important; }
.fx-g-src { margin-top: 8px; font-size: 0.75rem; }
.fx-g-src summary { cursor: pointer; font-weight: 700; color: #9CC3FF !important; }
.fx-g-src a { display: block; color: #9CC3FF !important; }
.fx-g-espn { padding: 10px 14px 4px; }
.fx-g-espn-l { font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase; color: #D6DDE8; margin-bottom: 4px; }
.fx-g-espn-bar { display: flex; height: 22px; border-radius: 999px; overflow: hidden; border: 1px solid rgba(255, 255, 255, 0.4); }
.fx-g-espn-bar span { display: flex; align-items: center; justify-content: center; color: #FFFFFF; font-size: 0.72rem;
                      font-weight: 800; white-space: nowrap; overflow: hidden; text-shadow: 0 1px 2px rgba(0, 0, 0, 0.6); }
.fx-g-adv { margin: 8px 14px 4px; }
.fx-g-adv summary { cursor: pointer; font-family: 'Oswald', sans-serif; letter-spacing: 0.06em; color: #FFFFFF;
                    font-size: 0.95rem; text-transform: uppercase; }
.fx-g-advgrid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 8px; }
.fx-g-advcol { background: rgba(0, 0, 0, 0.25); border-radius: 10px; border-top: 4px solid var(--c); padding: 8px 10px; }
.fx-g-advh { font-family: 'Oswald', sans-serif; font-size: 1.1rem; color: #FFFFFF; }
.fx-g-fpi { font-size: 0.72rem; color: #D6DDE8; margin: 2px 0 4px; }
.fx-g-fpi b { color: #FFD23F; }
.fx-g-units { display: flex; gap: 4px; flex-wrap: wrap; margin-bottom: 4px; }
.fx-u { font-size: 0.66rem; font-weight: 800; padding: 1px 6px; border-radius: 5px; background: rgba(255, 255, 255, 0.15); color: #FFFFFF; }
.fx-u.good { background: #1E7A46; } .fx-u.bad { background: #A3171C; }
.fx-g-sw { margin-top: 4px; }
.fx-g-sw .t { font-size: 0.62rem; letter-spacing: 0.08em; text-transform: uppercase; color: #9FB0CC; }
.fx-g-sw ul { list-style: none; margin: 2px 0 0; padding: 0; font-size: 0.74rem; color: #FFFFFF; }
.fx-g-sw li { margin-bottom: 1px; }
.fx-inj { display: block; font-size: 0.72rem; color: #FFFFFF; }
.fx-inj small { color: #FFB3B3; }
.fx-inj.questionable small { color: #FFD23F; }
@media (max-width: 640px) {
    .fx-games { grid-template-columns: 1fr; }
    .fx-g-abbr { font-size: 1.6rem; }
    .fx-g-mid { min-width: 74px; padding: 8px 6px; }
    .fx-g-starsrow { grid-template-columns: 1fr; }
}
</style>
"""
