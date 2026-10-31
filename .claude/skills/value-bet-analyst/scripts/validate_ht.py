#!/usr/bin/env python3
"""Valida el modelo de 1T con resultados reales al descanso (timelines ESPN).
Uso: python3 validate_ht.py datos.json [dias=300]
Compara fracción de goles en 1T y P(1X2 al descanso) predicha vs real."""
import sys, json, math, subprocess, numpy as np
from concurrent.futures import ThreadPoolExecutor
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from model import DC, Dist
from datetime import datetime, timezone
P = lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
d = json.load(open(sys.argv[1])); ms = sorted(d["matches"], key=lambda m: m["date"])
end = P(ms[-1]["date"]).timestamp() - (int(sys.argv[2]) if len(sys.argv) > 2 else 300)*86400
test = [m for m in ms if P(m["date"]).timestamp() > end]
def tl(m):
    r = subprocess.run(["sports-skills","football","get_event_timeline",f"--event_id={m['id']}"],capture_output=True,text=True,timeout=120)
    try: ev = json.loads(r.stdout)["data"]["timeline"]
    except Exception: return None
    h = a = hh = ha = 0
    for e in ev:
        if e["type"] not in ("goal","penalty_goal","own_goal") or not e.get("team"): continue
        home = e["team"]["id"] == m["home_id"]
        h += home; a += not home
        if e["minute"] <= 45: hh += home; ha += not home
    if (h, a) != (m["hg"], m["ag"]):
        # probar own_goal invertido
        h = a = hh = ha = 0
        for e in ev:
            if e["type"] not in ("goal","penalty_goal","own_goal") or not e.get("team"): continue
            home = (e["team"]["id"] == m["home_id"]) != (e["type"] == "own_goal")
            h += home; a += not home
            if e["minute"] <= 45: hh += home; ha += not home
        if (h, a) != (m["hg"], m["ag"]): return None
    return (hh, ha)
with ThreadPoolExecutor(8) as ex: hts = list(ex.map(tl, test))
ok = [(m, h) for m, h in zip(test, hts) if h]
print("partidos con HT válido:", len(ok), "de", len(test))
g1 = sum(h[0]+h[1] for _, h in ok); gt = sum(m["hg"]+m["ag"] for m, _ in ok)
print(f"fracción de goles en 1T: {g1/gt:.3f}")
rows = []
for day in sorted({m["date"][:10] for m, _ in ok}):
    ref = P(day+"T00:00Z"); tr = [m for m in ms if P(m["date"]) < ref]
    dc = DC(tr, ref, 0.003, 0.2); p = dc.fit()
    for m, h in ((m, h) for m, h in ok if m["date"][:10] == day):
        if m["home_id"] not in dc.idx or m["away_id"] not in dc.idx: continue
        l, u, r = dc.rates(p, m["home_id"], m["away_id"])
        q = Dist(l, u, r, 0.45).phtx2(); f = Dist(l, u, r, 0.45).p1x2()
        rows.append((q["1"], q["X"], q["2"], h[0] > h[1], h[0] == h[1], h[0] < h[1], f["2"]))
r = np.array(rows, float)
print(f"1T pred: L {r[:,0].mean():.1%} X {r[:,1].mean():.1%} V {r[:,2].mean():.1%} | real: L {r[:,3].mean():.1%} X {r[:,4].mean():.1%} V {r[:,5].mean():.1%}")
und = r[:,6] < 0.25
print(f"Visitante no favorito (P final <25%, n={und.sum()}): pred gana 1T {r[und,2].mean():.1%}, real {r[und,5].mean():.1%}")
