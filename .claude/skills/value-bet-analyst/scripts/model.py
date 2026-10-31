#!/usr/bin/env python3
"""Modelo Dixon-Coles + Monte Carlo (bootstrap) + de-vig + EV para un partido.

Uso:
  python3 model.py --data datos.json --odds cuotas.json [--out resultado.json]
         [--xi 0.003] [--prior-sd 0.35] [--boot 300] [--ht-share 0.45]
         [--adj-home 1.0 --adj-away 1.0 --adj-reason "texto"]

- datos.json: salida de fetch_data.py
- cuotas.json: cuotas reales copiadas de la casa (ver SKILL.md para el formato).
  Nunca se inventan: si no hay cuota, el mercado no se evalúa.

El modelo:
  1. Ajusta Dixon-Coles (ataque/defensa por equipo, ventaja local, rho) por máxima
     verosimilitud con decaimiento temporal exp(-xi*días) y prior normal (ridge) que
     encoge equipos con pocos datos hacia la media.
  2. Matriz de marcadores con corrección DC para 0-0, 1-0, 0-1, 1-1.
  3. Incertidumbre: re-ajusta el modelo sobre remuestreos bootstrap de los partidos
     (Monte Carlo sobre parámetros) -> percentiles P10/P90 de cada probabilidad y EV.
  4. Córners/tarjetas: binomial negativa con media y dispersión de los últimos partidos
     de ambos equipos (bootstrap sobre esos partidos).
  5. Quita el margen (método power) y calcula EV con la cuota real.
"""
import argparse
import json
import math
import sys
from datetime import datetime, timezone

import numpy as np
from scipy.optimize import minimize
from scipy.special import gammaln
from scipy.stats import nbinom, poisson

MAXG = 10
RNG = np.random.default_rng(7)


# ---------------------------------------------------------------- odds utils
def to_decimal(o):
    o = float(o)
    if abs(o) >= 100:  # americana
        return 1 + o / 100 if o > 0 else 1 + 100 / abs(o)
    if o <= 1:
        raise ValueError(f"Cuota inválida: {o}")
    return o


def fmt_odds(o):
    d = to_decimal(o)
    am = f"{float(o):+.0f}" if abs(float(o)) >= 100 else (f"+{(d-1)*100:.0f}" if d >= 2 else f"{-100/(d-1):.0f}")
    return f"{d:.2f} ({am})"


def devig_power(decs):
    """Método power: p_i = (1/d_i)^k con sum p_i = 1. Corrige sesgo favorito/longshot."""
    inv = np.array([1 / d for d in decs])
    if len(inv) == 1:
        return None, None
    lo, hi = 0.5, 5.0
    for _ in range(100):
        k = (lo + hi) / 2
        s = (inv ** k).sum()
        lo, hi = (k, hi) if s > 1 else (lo, k)
    return list(inv ** k), inv.sum() - 1


# ---------------------------------------------------------------- Dixon-Coles
class DC:
    def __init__(self, matches, ref, xi, prior_sd):
        self.teams = sorted({m["home_id"] for m in matches} | {m["away_id"] for m in matches})
        self.idx = {t: i for i, t in enumerate(self.teams)}
        self.names = {}
        for m in matches:
            self.names[m["home_id"]] = m["home"]; self.names[m["away_id"]] = m["away"]
        self.h = np.array([self.idx[m["home_id"]] for m in matches])
        self.a = np.array([self.idx[m["away_id"]] for m in matches])
        self.x = np.array([m["hg"] for m in matches], dtype=float)
        self.y = np.array([m["ag"] for m in matches], dtype=float)
        days = np.array([(ref - datetime.strptime(m["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)).total_seconds() / 86400 for m in matches])
        self.w0 = np.exp(-xi * days)
        self.n = len(self.teams)
        self.prec = 1 / prior_sd ** 2
        self.const = gammaln(self.x + 1) + gammaln(self.y + 1)
        self.count = np.bincount(np.r_[self.h, self.a], minlength=self.n)

    def unpack(self, p):
        n = self.n
        return p[:n], p[n:2 * n], p[2 * n], p[2 * n + 1], p[2 * n + 2]  # att, dfn, c, home, rho

    def nll(self, p, w):
        n = self.n
        att, dfn, c, home, rho = self.unpack(p)
        ll_lam = c + home + att[self.h] + dfn[self.a]
        ll_mu = c + att[self.a] + dfn[self.h]
        lam, mu = np.exp(ll_lam), np.exp(ll_mu)
        x, y = self.x, self.y
        t = np.ones_like(lam); g_l = np.zeros_like(lam); g_m = np.zeros_like(lam); g_r = np.zeros_like(lam)
        m00 = (x == 0) & (y == 0); m01 = (x == 0) & (y == 1); m10 = (x == 1) & (y == 0); m11 = (x == 1) & (y == 1)
        t[m00] = 1 - lam[m00] * mu[m00] * rho
        t[m01] = 1 + lam[m01] * rho
        t[m10] = 1 + mu[m10] * rho
        t[m11] = 1 - rho
        t = np.maximum(t, 1e-10)
        g_l[m00] = -lam[m00] * mu[m00] * rho / t[m00]; g_m[m00] = g_l[m00]; g_r[m00] = -lam[m00] * mu[m00] / t[m00]
        g_l[m01] = lam[m01] * rho / t[m01]; g_r[m01] = lam[m01] / t[m01]
        g_m[m10] = mu[m10] * rho / t[m10]; g_r[m10] = mu[m10] / t[m10]
        g_r[m11] = -1 / t[m11]
        ll = w * (np.log(t) + x * ll_lam - lam + y * ll_mu - mu - self.const)
        gl = w * (x - lam + g_l)
        gm = w * (y - mu + g_m)
        grad = np.zeros_like(p)
        grad[:n] = np.bincount(self.h, gl, n) + np.bincount(self.a, gm, n)
        grad[n:2 * n] = np.bincount(self.a, gl, n) + np.bincount(self.h, gm, n)
        grad[2 * n] = gl.sum() + gm.sum()
        grad[2 * n + 1] = gl.sum()
        grad[2 * n + 2] = (w * g_r).sum()
        pen = 0.5 * self.prec * (att @ att + dfn @ dfn)
        f = -ll.sum() + pen
        g = -grad
        g[:2 * n] += self.prec * p[:2 * n]
        return f, g

    def fit(self, w=None, x0=None):
        w = self.w0 if w is None else w
        if x0 is None:
            x0 = np.zeros(2 * self.n + 3); x0[2 * self.n] = math.log(max(self.y.mean(), 0.3))
        bounds = [(None, None)] * (2 * self.n + 2) + [(-0.25, 0.25)]
        r = minimize(self.nll, x0, args=(w,), jac=True, method="L-BFGS-B", bounds=bounds)
        return r.x

    def rates(self, p, hid, aid):
        att, dfn, c, home, rho = self.unpack(p)
        i, j = self.idx[hid], self.idx[aid]
        return math.exp(c + home + att[i] + dfn[j]), math.exp(c + att[j] + dfn[i]), rho


def score_matrix(lam, mu, rho, dc=True):
    g = np.arange(MAXG + 1)
    M = np.outer(poisson.pmf(g, lam), poisson.pmf(g, mu))
    if dc:
        M[0, 0] *= max(1 - lam * mu * rho, 1e-10); M[0, 1] *= 1 + lam * rho
        M[1, 0] *= 1 + mu * rho; M[1, 1] *= 1 - rho
    return M / M.sum()


# ---------------------------------------------------------------- settlement
def split_line(line):
    q = round(line * 4)
    if q % 2:  # cuarto de línea -> media apuesta en cada línea vecina
        return [line - 0.25, line + 0.25]
    return [line]


def settle(values, probs, line, sign):
    """values: distribución discreta de v; apuesta gana si sign*(v) + line > 0.
    Devuelve lista de (p_win, p_push, p_loss) por cada media apuesta."""
    out = []
    for l in split_line(line):
        x = sign * values + l
        out.append((probs[x > 1e-9].sum(), probs[np.abs(x) <= 1e-9].sum(), probs[x < -1e-9].sum()))
    return out


def ev_from(parts, d):
    return float(np.mean([pw * (d - 1) - pl for pw, pp, pl in parts]))


def pwin(parts):
    """Probabilidad de ganar excluyendo pushes (comparable con implícita del mercado)."""
    pw = np.mean([p[0] for p in parts]); pl = np.mean([p[2] for p in parts])
    return float(pw / (pw + pl)) if pw + pl > 0 else 0.0


# ---------------------------------------------------------------- distributions
class Dist:
    """Todas las distribuciones necesarias para un conjunto de parámetros."""
    def __init__(self, lam, mu, rho, ht_share, corners=None, cards=None):
        self.M = score_matrix(lam, mu, rho)
        g = np.arange(MAXG + 1)
        G1, G2 = np.meshgrid(g, g, indexing="ij")
        self.diff_v, self.diff_p = self._collapse((G1 - G2).ravel(), self.M.ravel())
        self.tot_v, self.tot_p = self._collapse((G1 + G2).ravel(), self.M.ravel())
        self.Mht = score_matrix(lam * ht_share, mu * ht_share, 0, dc=False)
        self.htd_v, self.htd_p = self._collapse((G1 - G2).ravel(), self.Mht.ravel())
        self.htt_v, self.htt_p = self._collapse((G1 + G2).ravel(), self.Mht.ravel())
        self.corners = corners; self.cards = cards
        self.lam, self.mu = lam, mu

    @staticmethod
    def _collapse(v, p):
        u = np.unique(v)
        return u.astype(float), np.array([p[v == k].sum() for k in u])

    def p1x2(self):
        return {"1": float(np.tril(self.M, -1).sum()), "X": float(np.trace(self.M)), "2": float(np.triu(self.M, 1).sum())}

    def phtx2(self):
        M = self.Mht
        return {"1": float(np.tril(M, -1).sum()), "X": float(np.trace(M)), "2": float(np.triu(M, 1).sum())}


def count_dist(mean, phi, maxn=40):
    v = np.arange(maxn + 1)
    if phi <= 1.05:
        p = poisson.pmf(v, mean)
    else:
        r = mean / (phi - 1); p = nbinom.pmf(v, r, r / (r + mean))
    return v.astype(float), p / p.sum()


def stat_model(rows_h, rows_a, key, boot):
    """Media y dispersión de totales por partido para córners/tarjetas, con bootstrap."""
    def est(rh, ra):
        hf = np.mean([r["for"][key] for r in rh]); ha = np.mean([r["against"][key] for r in rh])
        af = np.mean([r["for"][key] for r in ra]); aa = np.mean([r["against"][key] for r in ra])
        mean = (hf + aa) / 2 + (af + ha) / 2
        tots = [r["for"][key] + r["against"][key] for r in rh + ra]
        phi = max(np.var(tots, ddof=1) / max(np.mean(tots), 1e-6), 1.0)
        return mean, phi
    rh = [r for r in rows_h if r["for"].get(key) is not None and r["against"].get(key) is not None]
    ra = [r for r in rows_a if r["for"].get(key) is not None and r["against"].get(key) is not None]
    if len(rh) < 5 or len(ra) < 5:
        return None
    base = est(rh, ra)
    sims = [est([rh[i] for i in RNG.integers(0, len(rh), len(rh))], [ra[i] for i in RNG.integers(0, len(ra), len(ra))]) for _ in range(boot)]
    return {"base": base, "sims": sims, "n": (len(rh), len(ra))}


# ---------------------------------------------------------------- markets
def selections(market, D, fair_1x2=None):
    """Devuelve lista de (nombre, cuota_original, parts_fn) donde parts_fn(D)->(p_display, parts)."""
    t = market["type"]; o = market["odds"]; L = market.get("line")
    sel = []
    def simple(pfun):
        return lambda D: (lambda p: (p, [(p, 0.0, 1 - p)]))(pfun(D))
    if t == "1x2":
        for k, nm in (("1", "Local"), ("X", "Empate"), ("2", "Visitante")):
            if k in o: sel.append((f"1X2: {nm}", o[k], simple(lambda D, k=k: D.p1x2()[k])))
    elif t == "dc":
        comb = {"1X": ("1", "X"), "12": ("1", "2"), "X2": ("X", "2")}
        for k, ks in comb.items():
            if k in o: sel.append((f"Doble oportunidad {k}", o[k], simple(lambda D, ks=ks: sum(D.p1x2()[q] for q in ks))))
    elif t == "btts":
        def by(D): return float(1 - D.M[0, :].sum() - D.M[:, 0].sum() + D.M[0, 0])
        if "yes" in o: sel.append(("Ambos anotan: Sí", o["yes"], simple(by)))
        if "no" in o: sel.append(("Ambos anotan: No", o["no"], simple(lambda D: 1 - by(D))))
    elif t in ("total", "ht_total", "corners_total", "cards_total"):
        src = {"total": ("tot_v", "tot_p", "Goles"), "ht_total": ("htt_v", "htt_p", "Goles 1T")}
        for side, sign, nm in (("over", 1, "Más de"), ("under", -1, "Menos de")):
            if side not in o: continue
            if t in src:
                vk, pk, lab = src[t]
                fn = lambda D, vk=vk, pk=pk, sign=sign: (lambda parts: (pwin(parts), parts))(settle(getattr(D, vk), getattr(D, pk), -sign * L, sign))
            else:
                attr = "corners" if t == "corners_total" else "cards"
                lab = "Córners" if attr == "corners" else "Tarjetas"
                fn = lambda D, attr=attr, sign=sign: (lambda parts: (pwin(parts), parts))(settle(*getattr(D, attr), -sign * L, sign)) if getattr(D, attr) else (None, None)
            sel.append((f"{lab} {nm} {L}", o[side], fn))
    elif t == "corners_3way":
        for side, nm in (("over", f"Más de {L}"), ("exact", f"Exactamente {L}"), ("under", f"Menos de {L}")):
            if side not in o: continue
            def fn(D, side=side):
                if not D.corners: return None, None
                v, p = D.corners
                q = p[v > L].sum() if side == "over" else p[v == L].sum() if side == "exact" else p[v < L].sum()
                return float(q), [(float(q), 0.0, float(1 - q))]
            sel.append((f"Córners 3 opciones: {nm}", o[side], fn))
    elif t == "ah":
        for side, sign, nm in (("home", 1, "Local"), ("away", -1, "Visitante")):
            if side not in o: continue
            line = L if side == "home" else -L
            sel.append((f"Hándicap asiático {nm} {line:+g}", o[side],
                        lambda D, sign=sign, line=line: (lambda parts: (pwin(parts), parts))(settle(D.diff_v, D.diff_p, line, sign))))
    elif t == "ht_1x2":
        for k, nm in (("1", "Local"), ("X", "Empate"), ("2", "Visitante")):
            if k in o: sel.append((f"1T 1X2: {nm}", o[k], simple(lambda D, k=k: D.phtx2()[k])))
    elif t == "correct_score":
        for k, od in o.items():
            a, b = (int(z) for z in k.split("-"))
            sel.append((f"Marcador exacto {k}", od, simple(lambda D, a=a, b=b: float(D.M[a, b]))))
    elif t == "single":
        key = market["key"]
        pf = {"ht_1": lambda D: D.phtx2()["1"], "ht_X": lambda D: D.phtx2()["X"], "ht_2": lambda D: D.phtx2()["2"]}
        if key.startswith("cs:"):
            a, b = (int(z) for z in key[3:].split("-")); f = lambda D, a=a, b=b: float(D.M[a, b])
        elif key in pf:
            f = pf[key]
        else:
            raise SystemExit(f"Clave 'single' no soportada: {key}")
        sel.append((market.get("name", key), o, simple(f)))
    else:
        raise SystemExit(f"Tipo de mercado no soportado: {t}")
    return sel


APPROX = ("ht_total", "ht_1x2", "corners_total", "corners_3way", "cards_total", "single", "correct_score")


def backtest(a, days_back=None, verbose=True):
    """Predicción fuera de muestra: para cada jornada (fecha) de los últimos N días,
    ajusta con los partidos anteriores y evalúa. Mide sesgo en goles y calibración."""
    data = json.load(open(a.data))
    P = lambda s: datetime.strptime(s, "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc)
    ms = sorted(data["matches"], key=lambda m: m["date"])
    days_back = days_back or a.backtest
    end = P(ms[-1]["date"]); start = end.timestamp() - days_back * 86400
    test = [m for m in ms if P(m["date"]).timestamp() > start]
    days = sorted({m["date"][:10] for m in test})
    rps = []; rps_base = []; y_b = []; br_o = []; br_b = []; pred_t = []; real_t = []; p_o = []; y_o = []; ll = []
    for day in days:
        ref = P(day + "T00:00Z")
        train = [m for m in ms if P(m["date"]) < ref]
        dc = DC(train, ref, a.xi, a.prior_sd); p = dc.fit()
        for m in (m for m in test if m["date"][:10] == day):
            if m["home_id"] not in dc.idx or m["away_id"] not in dc.idx: continue
            l, u, r = dc.rates(p, m["home_id"], m["away_id"]); D = Dist(l, u, r, a.ht_share)
            q = D.p1x2(); o = 0 if m["hg"] > m["ag"] else 1 if m["hg"] == m["ag"] else 2
            cp = np.cumsum([q["1"], q["X"], q["2"]])[:2]; co = np.cumsum(np.eye(3)[o])[:2]
            fr = np.bincount([0 if t["hg"] > t["ag"] else 1 if t["hg"] == t["ag"] else 2 for t in train[-600:]], minlength=3) / len(train[-600:])
            rps_base.append(((np.cumsum(fr)[:2] - co) ** 2).sum() / 2)
            rps.append(((cp - co) ** 2).sum() / 2); ll.append(-math.log([q["1"], q["X"], q["2"]][o]))
            po = float(D.tot_p[D.tot_v > 2.5].sum()); yo = m["hg"] + m["ag"] > 2.5
            pb = float(1 - D.M[0, :].sum() - D.M[:, 0].sum() + D.M[0, 0]); yb = m["hg"] > 0 and m["ag"] > 0
            br_o.append((po - yo) ** 2); br_b.append((pb - yb) ** 2); y_b.append(yb)
            pred_t.append(l + u); real_t.append(m["hg"] + m["ag"]); p_o.append(po); y_o.append(yo)
    n = len(rps)
    base_o = np.mean(y_o)
    metrics = {"n": n, "rps": float(np.mean(rps)), "rps_base": float(np.mean(rps_base)),
               "brier_o25": float(np.mean(br_o)), "brier_o25_base": float(base_o * (1 - base_o)),
               "brier_btts": float(np.mean(br_b)), "brier_btts_base": float(np.mean(y_b) * (1 - np.mean(y_b))),
               "goals_pred": float(np.mean(pred_t)), "goals_real": float(np.mean(real_t))}
    if not verbose:
        return metrics
    print(f"RPS base (frecuencias 1/X/2 previas) {metrics['rps_base']:.4f} | BTTS Brier constante {metrics['brier_btts_base']:.4f}")
    print(f"Backtest fuera de muestra: {n} partidos en {len(days)} fechas (últimos {a.backtest} días)")
    print(f"1X2  RPS {np.mean(rps):.4f} | log-loss {np.mean(ll):.4f} (uniforme = {math.log(3):.4f})")
    print(f"Goles: predicho {np.mean(pred_t):.2f}/PJ vs real {np.mean(real_t):.2f}/PJ")
    print(f"Over 2.5: prob media predicha {np.mean(p_o):.1%} vs frecuencia real {base_o:.1%} | Brier {np.mean(br_o):.4f} (constante = {base_o*(1-base_o):.4f})")
    print(f"BTTS Brier {np.mean(br_b):.4f}")
    p_o = np.array(p_o); y_o = np.array(y_o)
    for lo, hi in ((0, .4), (.4, .5), (.5, .6), (.6, 1)):
        s = (p_o >= lo) & (p_o < hi)
        if s.sum(): print(f"  O2.5 pred {lo:.0%}-{hi:.0%}: n={s.sum()}, pred {p_o[s].mean():.1%}, real {y_o[s].mean():.1%}")
    return metrics


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--odds", required=True)
    ap.add_argument("--out")
    ap.add_argument("--xi", type=float, default=0.003, help="decaimiento temporal por día (0.003 ≈ vida media 230 días)")
    ap.add_argument("--prior-sd", type=float, default=0.2, help="sd del prior ridge (0.2 = mejor RPS en backtest Liga MX)")
    ap.add_argument("--boot", type=int, default=300)
    ap.add_argument("--ht-share", type=float, default=0.45, help="fracción de goles esperados en el 1T (estimación)")
    ap.add_argument("--adj-home", type=float, default=1.0, help="multiplicador contextual de goles esperados del local")
    ap.add_argument("--adj-away", type=float, default=1.0)
    ap.add_argument("--adj-reason", default="")
    ap.add_argument("--ev-min", type=float, default=0.03)
    ap.add_argument("--model-weight", type=float, default=0.5,
                    help="peso del modelo frente al mercado al combinar goles esperados (0=solo mercado, 1=solo modelo)")
    ap.add_argument("--backtest", type=int, default=0, help="valida el modelo fuera de muestra en los últimos N días de partidos")
    ap.add_argument("--validate-days", type=int, default=300, help="backtest automático para medir skill por mercado (0 = omitir)")
    a = ap.parse_args()
    if a.backtest:
        return backtest(a)
    for v in (a.adj_home, a.adj_away):
        if not 0.85 <= v <= 1.15:
            raise SystemExit("Los ajustes contextuales están limitados a ±15% (0.85–1.15).")

    data = json.load(open(a.data)); odds = json.load(open(a.odds))
    hid, aid = data["home"]["id"], data["away"]["id"]
    hname, aname = data["home"]["name"], data["away"]["name"]
    fx = data.get("fixture")
    ref = datetime.strptime(fx["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc) if fx else datetime.now(timezone.utc)
    matches = [m for m in data["matches"] if datetime.strptime(m["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc) < ref]

    dc = DC(matches, ref, a.xi, a.prior_sd)
    for t in (hid, aid):
        if t not in dc.idx:
            raise SystemExit(f"Sin partidos para el equipo {t}")
    p0 = dc.fit()
    lam, mu, rho = dc.rates(p0, hid, aid)
    lam *= a.adj_home; mu *= a.adj_away

    # Monte Carlo sobre parámetros: bootstrap de partidos
    n = len(matches); boots = []
    for _ in range(a.boot):
        cnt = np.bincount(RNG.integers(0, n, n), minlength=n)
        pb = dc.fit(w=dc.w0 * cnt, x0=p0)
        l, m_, r = dc.rates(pb, hid, aid)
        boots.append((l * a.adj_home, m_ * a.adj_away, r))

    ms = data.get("match_stats", {})
    cm = stat_model(ms.get(hname, []), ms.get(aname, []), "corner_kicks", a.boot) if ms else None
    km = None
    if ms:
        for side in ("for", "against"):
            for rows in ms.values():
                for r in rows:
                    y, rd = r[side].get("yellow_cards"), r[side].get("red_cards")
                    r[side]["cards"] = None if y is None else y + (rd or 0)
        km = stat_model(ms.get(hname, []), ms.get(aname, []), "cards", a.boot)

    ht_draws = RNG.uniform(a.ht_share - 0.05, a.ht_share + 0.05, a.boot)  # incertidumbre estructural del 1T

    def mk(l, m_, r, i=None):
        cr = count_dist(*(cm["base"] if i is None else cm["sims"][i])) if cm else None
        kd = count_dist(*(km["base"] if i is None else km["sims"][i])) if km else None
        return Dist(l, m_, r, a.ht_share if i is None else ht_draws[i], cr, kd)

    small = min(dc.count[dc.idx[hid]], dc.count[dc.idx[aid]])
    vm = backtest(a, a.validate_days, verbose=False) if a.validate_days else None
    skill = {"1x2": True, "totals": True, "btts": True}
    if vm:
        skill = {"1x2": vm["rps"] < vm["rps_base"], "totals": vm["brier_o25"] < vm["brier_o25_base"],
                 "btts": vm["brier_btts"] < vm["brier_btts_base"]}

    # ---- goles esperados implícitos en el mercado (sin margen) y blend modelo/mercado
    mkt_fair = {}
    for mk_ in odds["markets"]:
        if mk_["type"] == "1x2" and "1x2" not in mkt_fair and all(k in mk_["odds"] for k in ("1", "X", "2")):
            mkt_fair["1x2"] = devig_power([to_decimal(mk_["odds"][k]) for k in ("1", "X", "2")])[0]
        if mk_["type"] == "total" and mk_.get("line") == 2.5 and "o25" not in mkt_fair:
            mkt_fair["o25"] = devig_power([to_decimal(mk_["odds"]["over"]), to_decimal(mk_["odds"]["under"])])[0][0]
    implied = None
    if "1x2" in mkt_fair:
        def loss(v):
            Dm = Dist(math.exp(v[0]), math.exp(v[1]), rho, a.ht_share); q = Dm.p1x2()
            e = sum((q[k] - f) ** 2 for k, f in zip(("1", "X", "2"), mkt_fair["1x2"]))
            if "o25" in mkt_fair:
                e += (float(Dm.tot_p[Dm.tot_v > 2.5].sum()) - mkt_fair["o25"]) ** 2
            return e
        v = minimize(loss, [math.log(lam), math.log(mu)], method="Nelder-Mead", options={"xatol": 1e-6, "fatol": 1e-12}).x
        implied = (math.exp(v[0]), math.exp(v[1]))
    w_sup = a.model_weight if skill["1x2"] else 0.0
    w_tot = a.model_weight if (skill["totals"] and "o25" in mkt_fair) else (0.0 if "o25" in mkt_fair else 1.0)

    def blend(l, m_):
        if not implied:
            return l, m_
        T, sh = l + m_, l / (l + m_)
        Tm, shm = implied[0] + implied[1], implied[0] / (implied[0] + implied[1])
        Tf = T ** w_tot * Tm ** (1 - w_tot); shf = w_sup * sh + (1 - w_sup) * shm
        return Tf * shf, Tf * (1 - shf)

    Dpure = mk(lam, mu, rho)
    lam_f, mu_f = blend(lam, mu)
    D0 = mk(lam_f, mu_f, rho)
    DB = [mk(*blend(l, m_), r, i) for i, (l, m_, r) in enumerate(boots)]
    skill_of = {"1x2": "1x2", "dc": "1x2", "ah": "1x2", "correct_score": "1x2", "single": "1x2", "ht_1x2": "1x2",
                "total": "totals", "ht_total": "totals", "btts": "btts"}
    rows = []; fair_1x2 = None
    for mkt in odds["markets"]:
        sels = selections(mkt, D0)
        if not sels: continue
        decs = [to_decimal(s[1]) for s in sels]
        fair, margin = (devig_power(decs) if mkt["type"] not in ("dc", "correct_score", "single") else (None, None))
        if mkt["type"] == "1x2" and fair and len(fair) == 3:
            fair_1x2 = dict(zip(("1", "X", "2"), fair))
        if mkt["type"] == "dc":
            comb = {"1X": ("1", "X"), "12": ("1", "2"), "X2": ("X", "2")}
            keys = [k for k in comb if k in mkt["odds"]]
            if fair_1x2:
                fair = [sum(fair_1x2[q] for q in comb[k]) for k in keys]
            else:
                inv = [1 / d for d in decs]; s = sum(inv); fair = [2 * v / s for v in inv]
            margin = sum(1 / d for d in decs) / 2 - 1 if len(decs) == 3 else None
        for k, (name, o, fn) in enumerate(sels):
            d = decs[k]
            p, parts = fn(D0)
            p_pure = fn(Dpure)[0]
            if p is None:
                rows.append({"market": name, "odds": fmt_odds(o), "skip": "sin datos suficientes"}); continue
            ev = ev_from(parts, d)
            bp, bev = [], []
            for Db in DB:
                pb, partsb = fn(Db); bp.append(pb); bev.append(ev_from(partsb, d))
            p10, p90 = np.percentile(bp, [10, 90]); ev10 = float(np.percentile(bev, 10))
            pf = fair[k] if fair else None
            width = p90 - p10
            conf = 2 if width < 0.08 else 1 if width < 0.15 else 0
            notes = []
            if mkt["type"] in APPROX:
                conf = min(conf, 1); notes.append("modelo aproximado")
            if small < 20:
                conf = min(conf, 1); notes.append(f"muestra pequeña ({small} PJ)")
            sk = skill_of.get(mkt["type"])
            if sk and not skill[sk]:
                conf = 0; notes.append("el modelo no demostró skill en este mercado (backtest)")
            if pf is not None and abs(p_pure - pf) > 0.12:
                conf = max(conf - 1, 0); notes.append("modelo puro diverge >12pp del mercado: revisar")
            if pf is None:
                notes.append("sin contrapartida: no se puede quitar margen")
            if ev >= a.ev_min and ev10 > 0 and conf >= 1:
                cls = "VALUE BET"
            elif ev > 0:
                cls = "NO BET"
                notes.append("EV marginal" if ev < a.ev_min else "no robusto (P10 EV ≤ 0)" if ev10 <= 0 else "confianza baja")
            else:
                cls = "SIN VALOR"
            kelly = max(ev / (d - 1), 0) / 4 if cls == "VALUE BET" else 0
            rows.append({
                "market": name, "odds": fmt_odds(o), "decimal": round(d, 3),
                "p_model": round(p, 4), "p_pure": round(p_pure, 4), "p10": round(float(p10), 4), "p90": round(float(p90), 4),
                "p_fair": None if pf is None else round(pf, 4), "fair_odds_model": round(1 / p, 2) if p > 0 else None,
                "ev": round(ev, 4), "ev_p10": round(ev10, 4),
                "confidence": ["Baja", "Media", "Alta"][conf], "class": cls,
                "stake_pct": round(min(kelly, 0.02) * 100, 2), "notes": "; ".join(notes),
                "book_margin": None if margin is None else round(margin, 4),
            })

    # ------------------------------------------------------------ informe
    p = Dpure.p1x2(); pf_ = D0.p1x2()
    att, dfn, c, home, _ = dc.unpack(p0)
    print(f"# {hname} vs {aname} — modelo Dixon-Coles")
    print(f"Partidos usados: {n} | decaimiento xi={a.xi}/día | prior sd={a.prior_sd} | bootstrap={a.boot}")
    print(f"Ventaja local estimada: x{math.exp(home):.2f} | rho={rho:+.3f}")
    for t, nm in ((hid, hname), (aid, aname)):
        i = dc.idx[t]
        print(f"  {nm}: ataque {math.exp(att[i]):.2f}, defensa (concede) {math.exp(dfn[i]):.2f}, PJ en datos {dc.count[i]}")
    lb = np.array([b[0] for b in boots]); mb = np.array([b[1] for b in boots])
    print(f"Goles esperados: {hname} {lam:.2f} [P10-P90 {np.percentile(lb,10):.2f}-{np.percentile(lb,90):.2f}] | {aname} {mu:.2f} [{np.percentile(mb,10):.2f}-{np.percentile(mb,90):.2f}]")
    if implied:
        print(f"Mercado (sin margen) implica: {hname} {implied[0]:.2f} | {aname} {implied[1]:.2f} goles")
        print(f"Blend -> {hname} {lam_f:.2f} | {aname} {mu_f:.2f} (peso modelo: reparto {w_sup:.2f}, total {w_tot:.2f})")
    else:
        print("Sin 1X2 en cuotas: se usa el modelo puro (sin blend con mercado).")
    if a.adj_home != 1 or a.adj_away != 1:
        print(f"Ajuste contextual aplicado: local x{a.adj_home}, visitante x{a.adj_away} — {a.adj_reason}")
    print(f"1X2 modelo puro: 1 {p['1']:.1%} ({1/p['1']:.2f}) | X {p['X']:.1%} ({1/p['X']:.2f}) | 2 {p['2']:.1%} ({1/p['2']:.2f})")
    print(f"1X2 final (blend): 1 {pf_['1']:.1%} ({1/pf_['1']:.2f}) | X {pf_['X']:.1%} ({1/pf_['X']:.2f}) | 2 {pf_['2']:.1%} ({1/pf_['2']:.2f})")
    top = sorted(((D0.M[i, j], f"{i}-{j}") for i in range(6) for j in range(6)), reverse=True)[:6]
    print("Marcadores más probables: " + ", ".join(f"{s} {q:.1%}" for q, s in top))
    if vm:
        print(f"Validación fuera de muestra ({vm['n']} partidos, últimos {a.validate_days} días): "
              f"1X2 RPS {vm['rps']:.4f} vs base {vm['rps_base']:.4f} -> {'SKILL' if skill['1x2'] else 'SIN SKILL'} | "
              f"O2.5 Brier {vm['brier_o25']:.4f} vs constante {vm['brier_o25_base']:.4f} -> {'SKILL' if skill['totals'] else 'SIN SKILL'} | "
              f"BTTS Brier {vm['brier_btts']:.4f} vs constante {vm['brier_btts_base']:.4f} -> {'SKILL' if skill['btts'] else 'SIN SKILL'} | "
              f"goles pred {vm['goals_pred']:.2f} vs real {vm['goals_real']:.2f}")
    if cm: print(f"Córners: media total {cm['base'][0]:.1f}, dispersión {cm['base'][1]:.2f} (n={cm['n']})")
    if km: print(f"Tarjetas: media total {km['base'][0]:.1f}, dispersión {km['base'][1]:.2f} (n={km['n']})")

    print("\n| Mercado | Cuota | P. estimada (P10–P90) | P. modelo puro | P. implícita sin margen | EV (P10) | Confianza | Clasificación | Notas |")
    print("|---|---|---|---|---|---|---|---|---|")
    for r in rows:
        if "skip" in r:
            print(f"| {r['market']} | {r['odds']} | — | — | — | — | — | NO BET | {r['skip']} |"); continue
        pf = "n/d" if r["p_fair"] is None else f"{r['p_fair']:.1%}"
        print(f"| {r['market']} | {r['odds']} | {r['p_model']:.1%} ({r['p10']:.0%}–{r['p90']:.0%}) | {r['p_pure']:.1%} | {pf} | {r['ev']:+.1%} ({r['ev_p10']:+.1%}) | {r['confidence']} | **{r['class']}** | {r['notes']} |")
    vb = [r for r in rows if r.get("class") == "VALUE BET"]
    print("\nVALUE BETS: " + (", ".join(f"{r['market']} @ {r['odds']} (EV {r['ev']:+.1%}, stake ¼-Kelly {r['stake_pct']}%)" for r in vb) if vb else "ninguna → NO BET"))

    if a.out:
        json.dump({"lambda_home": lam_f, "lambda_away": mu_f, "lambda_model": [lam, mu], "lambda_market": implied, "rho": rho, "p1x2": p, "rows": rows, "validation": vm, "skill": skill,
                   "settings": vars(a)}, open(a.out, "w"), ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
