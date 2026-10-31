#!/usr/bin/env python3
"""Recoge datos de un partido con la skill football-data (CLI `sports-skills`).

Uso:
  python3 fetch_data.py --competition liga-mx --home "Guadalajara" --away "Atlante" \
      --out /ruta/datos.json [--seasons 3] [--stats 10]

Genera un JSON con:
  - matches: todos los partidos cerrados de las temporadas pedidas (para ajustar el modelo)
  - fixture: el partido a analizar (si está en el calendario)
  - table: tabla de la temporada actual calculada desde los resultados
  - form: últimos 5/10, splits local/visitante, dificultad de rivales, descanso
  - h2h: enfrentamientos directos en las temporadas cargadas
  - match_stats: córners/tarjetas/tiros de los últimos N partidos de cada equipo (--stats N)
Todo sale de la fuente; nada se estima aquí.
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone


def cli(cmd, **kw):
    args = ["sports-skills", "football", cmd] + [f"--{k}={v}" for k, v in kw.items()]
    r = subprocess.run(args, capture_output=True, text=True, timeout=180)
    try:
        d = json.loads(r.stdout)
    except json.JSONDecodeError:
        raise SystemExit(f"Fallo en {' '.join(args)}: {r.stderr[:500]}")
    if not d.get("status"):
        raise SystemExit(f"Error de la fuente en {cmd}: {d.get('message')}")
    return d.get("data") or {}, d.get("message", "")


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)


def norm_event(e, season_id):
    c = {x["qualifier"]: x for x in e.get("competitors", [])}
    if "home" not in c or "away" not in c:
        return None
    return {
        "id": e["id"], "date": e["start_time"], "status": e["status"], "season": season_id,
        "home_id": c["home"]["team"]["id"], "home": c["home"]["team"]["name"],
        "away_id": c["away"]["team"]["id"], "away": c["away"]["team"]["name"],
        "hg": e.get("scores", {}).get("home"), "ag": e.get("scores", {}).get("away"),
        "venue": (e.get("venue") or {}).get("name", ""),
    }


def resolve_team(name, comp):
    data, _ = cli("search_team", query=name)
    res = data.get("results", [])
    same = [r for r in res if (r.get("competition") or {}).get("id") == comp]
    pick = (same or res or [None])[0]
    if not pick:
        raise SystemExit(f"Equipo no encontrado: {name}")
    return pick["team"]["id"], pick["team"]["name"]


def table_from(matches):
    t = {}
    for m in matches:
        for side, gf, ga in (("home", m["hg"], m["ag"]), ("away", m["ag"], m["hg"])):
            tid = m[f"{side}_id"]
            r = t.setdefault(tid, {"team": m[side], "pj": 0, "g": 0, "e": 0, "p": 0, "gf": 0, "gc": 0, "pts": 0})
            r["pj"] += 1; r["gf"] += gf; r["gc"] += ga
            if gf > ga: r["g"] += 1; r["pts"] += 3
            elif gf == ga: r["e"] += 1; r["pts"] += 1
            else: r["p"] += 1
    rows = sorted(t.items(), key=lambda kv: (-kv[1]["pts"], -(kv[1]["gf"] - kv[1]["gc"]), -kv[1]["gf"]))
    out = {}
    for i, (tid, r) in enumerate(rows, 1):
        r["pos"] = i; r["ppg"] = round(r["pts"] / r["pj"], 2); r["dg"] = r["gf"] - r["gc"]
        out[tid] = r
    return out


def team_games(matches, tid, venue=None):
    g = [m for m in matches if (venue in (None, "home") and m["home_id"] == tid) or (venue in (None, "away") and m["away_id"] == tid)]
    return sorted(g, key=lambda m: m["date"])


def summarize(games, tid, table):
    pts = gf = ga = 0; res = []; opp_ppg = []; btts = o25 = cs = 0
    for m in games:
        home = m["home_id"] == tid
        f, a = (m["hg"], m["ag"]) if home else (m["ag"], m["hg"])
        opp = m["away_id"] if home else m["home_id"]
        oname = m["away"] if home else m["home"]
        gf += f; ga += a
        r = "G" if f > a else "E" if f == a else "P"
        pts += {"G": 3, "E": 1, "P": 0}[r]
        btts += f > 0 and a > 0; o25 += f + a > 2; cs += a == 0
        if opp in table: opp_ppg.append(table[opp]["ppg"])
        res.append(f"{m['date'][:10]} {'L' if home else 'V'} vs {oname} {f}-{a} ({r})")
    n = len(games) or 1
    return {
        "n": len(games), "pts": pts, "ppg": round(pts / n, 2), "gf": gf, "gc": ga,
        "gf_pg": round(gf / n, 2), "gc_pg": round(ga / n, 2),
        "btts_pct": round(btts / n, 2), "over25_pct": round(o25 / n, 2), "cs_pct": round(cs / n, 2),
        "opp_avg_ppg": round(sum(opp_ppg) / len(opp_ppg), 2) if opp_ppg else None,
        "results": res,
    }


def event_stats(eid):
    try:
        data, _ = cli("get_event_statistics", event_id=eid)
    except SystemExit:
        return None
    out = {}
    for t in data.get("teams", []):
        s = t.get("statistics", {})
        def num(k):
            try: return float(s.get(k))
            except (TypeError, ValueError): return None
        out[t["qualifier"]] = {k: num(k) for k in ("corner_kicks", "yellow_cards", "red_cards", "shots_total", "shots_on_target", "ball_possession", "fouls")}
    return out if "home" in out and "away" in out else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--competition", required=True)
    ap.add_argument("--home", required=True)
    ap.add_argument("--away", required=True)
    ap.add_argument("--seasons", type=int, default=3, help="temporadas a cargar (actual + anteriores)")
    ap.add_argument("--stats", type=int, default=10, help="últimos N partidos con estadísticas de córners/tarjetas (0 = no)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    cur, _ = cli("get_current_season", competition_id=a.competition)
    cur_id = cur["season"]["id"]
    year = int(cur["season"]["year"])
    season_ids = [cur_id] + [cur_id.replace(str(year), str(year - k)) for k in range(1, a.seasons)]

    hid, hname = resolve_team(a.home, a.competition)
    aid, aname = resolve_team(a.away, a.competition)

    allm, fixture, warnings = [], None, []
    for sid in season_ids:
        data, msg = cli("get_season_schedule", season_id=sid)
        evs = data.get("schedules") or data.get("events") or []
        if not evs:
            warnings.append(f"Sin calendario para {sid}: {msg}")
        for e in evs:
            m = norm_event(e, sid)
            if not m: continue
            if m["status"] == "closed" and m["hg"] is not None:
                allm.append(m)
            elif sid == cur_id and {m["home_id"], m["away_id"]} == {hid, aid} and m["status"] != "closed" and fixture is None:
                fixture = m
    allm.sort(key=lambda m: m["date"])
    cur_m = [m for m in allm if m["season"] == cur_id]
    table = table_from(cur_m)

    ref = ts(fixture["date"]) if fixture else datetime.now(timezone.utc)
    if fixture and fixture["home_id"] != hid:
        warnings.append(f"El calendario dice que el local es {fixture['home']}, no {hname}. Revisa el orden.")

    form = {}
    for tid, name, ven in ((hid, hname, "home"), (aid, aname, "away")):
        all_g = [m for m in team_games(allm, tid) if ts(m["date"]) < ref]
        cur_g = [m for m in team_games(cur_m, tid) if ts(m["date"]) < ref]
        ven_g = [m for m in team_games(cur_m, tid, ven) if ts(m["date"]) < ref]
        # descanso: último partido en cualquier competición (calendario del equipo)
        tsched, _ = cli("get_team_schedule", team_id=tid)
        prev = [ts(e["start_time"]) for e in tsched.get("events", []) if e.get("status") == "closed" and ts(e["start_time"]) < ref]
        nxt = [ts(e["start_time"]) for e in tsched.get("events", []) if ts(e["start_time"]) > ref]
        form[name] = {
            "team_id": tid,
            "table": table.get(tid),
            "last5": summarize(all_g[-5:], tid, table),
            "last10": summarize(all_g[-10:], tid, table),
            "season": summarize(cur_g, tid, table),
            f"season_{ven}": summarize(ven_g, tid, table),
            "rest_days": round((ref - max(prev)).total_seconds() / 86400, 1) if prev else None,
            "days_to_next": round((min(nxt) - ref).total_seconds() / 86400, 1) if nxt else None,
        }

    h2h = [m for m in allm if {m["home_id"], m["away_id"]} == {hid, aid}]
    h2h_lines = [f"{m['date'][:10]} {m['home']} {m['hg']}-{m['ag']} {m['away']} ({m['season']})" for m in h2h]

    match_stats = {}
    if a.stats > 0:
        for tid, name in ((hid, hname), (aid, aname)):
            rows = []
            for m in [m for m in team_games(allm, tid) if ts(m["date"]) < ref][-a.stats:]:
                st = event_stats(m["id"])
                if not st: continue
                me, op = ("home", "away") if m["home_id"] == tid else ("away", "home")
                rows.append({"date": m["date"][:10], "event_id": m["id"], "for": st[me], "against": st[op]})
            match_stats[name] = rows

    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "ESPN via sports-skills football-data",
        "competition": a.competition, "seasons": season_ids,
        "home": {"id": hid, "name": hname}, "away": {"id": aid, "name": aname},
        "fixture": fixture, "warnings": warnings,
        "table": sorted(table.values(), key=lambda r: r["pos"]),
        "form": form, "h2h": h2h_lines, "match_stats": match_stats,
        "matches": allm,
    }
    with open(a.out, "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    # resumen legible
    print(f"Partido: {hname} (L) vs {aname} (V) | fixture: {fixture['date'] if fixture else 'no encontrado'}")
    print(f"Partidos cargados para el modelo: {len(allm)} ({', '.join(season_ids)})")
    for w in warnings: print("AVISO:", w)
    for name, f in form.items():
        t = f["table"] or {}
        print(f"\n== {name}: pos {t.get('pos')} | {t.get('pts')} pts en {t.get('pj')} | GF {t.get('gf')} GC {t.get('gc')} | descanso {f['rest_days']} d | siguiente en {f['days_to_next']} d")
        for k in ("last5", "last10", "season_home", "season_away"):
            if k in f:
                s = f[k]
                print(f"  {k}: {s['n']} PJ, {s['ppg']} pts/PJ, GF {s['gf_pg']} GC {s['gc_pg']} /PJ, BTTS {s['btts_pct']:.0%}, O2.5 {s['over25_pct']:.0%}, rivales {s['opp_avg_ppg']} pts/PJ")
        for r in f["last10"]["results"]: print("   ", r)
    print(f"\nH2H ({len(h2h_lines)}):"); [print("  ", l) for l in h2h_lines[-10:]]
    for name, rows in match_stats.items():
        if rows:
            n = len(rows)
            avg = lambda side, k: sum((r[side][k] or 0) for r in rows) / n
            print(f"\n{name} (últimos {n} con stats): córners a favor {avg('for','corner_kicks'):.1f} / en contra {avg('against','corner_kicks'):.1f} | amarillas {avg('for','yellow_cards'):.1f} / rival {avg('against','yellow_cards'):.1f} | tiros a puerta {avg('for','shots_on_target'):.1f} / {avg('against','shots_on_target'):.1f}")
    print(f"\nGuardado en {a.out}")


if __name__ == "__main__":
    main()
