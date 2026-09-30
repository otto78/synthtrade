#!/usr/bin/env python3
"""Random-entry test: gli entry del bot valgono qualcosa piu' di un orario casuale?

Domanda (Ibrutin, report ANALISI_SEGNALE_E_PIANO): il 90% degli trade entra con un
override mean-reversion e zero di quelli ha score > 6. Se le regole di uscita sono
quello che sono, l'entry conta o e' solo rumore?

Metodo:
  1. si simula l'uscita con le STESSE funzioni di pricing di produzione
     (app.scalping.pricing) e la stessa ladder break-even/trailing di
     app.scalping.break_even;
  2. validazione: si rigioca sugli orari di entry reali del bot e si confronta la
     distribuzione simulata con quella realmente realizzata in DB. Se il simulatore
     non riproduce i trade reali, il confronto coi random non significa niente;
  3. confronto: stessi orari reali vs orari casuali, stesso simulatore, stessa
     finestra. La differenza tra i due bracci e' il test.

Il test gira due volte, una per bracket. I valori sono stati ricostruiti dai trade
reali e matchano al centesimo (vede _BRACKETS e docs/TASKS.md):

  globale   SL net 0.50 -> lordo -0.3007%   TP net 0.80 -> lordo +1.0019%   (84% dei trade)
  override  SL net 0.30 -> lordo -0.1003%   TP net 0.55 -> lordo +0.7514%   (16% dei trade)

Uso (dentro il container, con l'app su sys.path):
    python scripts/random_entry_test.py --sample 5000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Sequence

import httpx

# --- pricing di produzione: riusate, non reimplementate, per fedelta' ----------
for _p in ("/app", str(Path(__file__).resolve().parents[1] / "synthtrade" / "backend")):
    if Path(_p).is_dir() and _p not in sys.path:
        sys.path.insert(0, _p)
from app.scalping.pricing import (  # noqa: E402
    _expected_net_pct_at_exit,
    _exit_price_ratio,
)

# --- parametri, letti da scalping_runtime_config (verificati) ------------------
EF = XF = 0.001  # taker 0.10% per lato, misurato su entry_commission/exit_commission
BE_TRIGGER_NET = 0.15
BE_LOCK_NET = 0.05
TRAIL_STEP_NET = 0.15
TRAIL_BUFFER_NET = 0.10
TRAIL_SAFETY_NET = 0.10


@dataclass(frozen=True)
class Bracket:
    name: str
    sl_net: float
    tp_net: float

    def sl_price(self, entry: float) -> float:
        return entry * _exit_price_ratio(-abs(self.sl_net), EF, XF)

    def tp_price(self, entry: float) -> float:
        return entry * _exit_price_ratio(self.tp_net, EF, XF)

    def trail_levels(self) -> list[tuple[float, float]]:
        """(trigger netto, nuovo SL netto) per ogni step, come _check_and_apply_trailing.

        Guardia 4 di produzione: il trigger deve stare sotto tp_net - safety.
        """
        cap = self.tp_net - TRAIL_SAFETY_NET
        out, k = [], 1
        while True:
            trigger = BE_TRIGGER_NET + k * TRAIL_STEP_NET
            if trigger >= cap:
                break
            out.append((trigger, trigger - TRAIL_BUFFER_NET))
            k += 1
        return out


BRACKETS = {
    "globale": Bracket("globale", sl_net=0.50, tp_net=0.80),
    "override": Bracket("override", sl_net=0.30, tp_net=0.55),
}

# =============================================================================
# 1. Dati: 1m da /api/v5/market/history-candles
# =============================================================================


async def fetch_candles(base_url: str, inst: str, start: datetime, end: datetime,
                       cache: Path, min_interval: float = 0.12) -> list[dict]:
    if cache.exists():
        raw = json.loads(cache.read_text())
        bars = [{"ts": b[0], "o": b[1], "h": b[2], "l": b[3], "c": b[4]} for b in raw]
        print(f"  cache: {len(bars)} candele 1m da {bars[0]['ts']} a {bars[-1]['ts']}")
        return bars

    bars: dict[int, dict] = {}
    async with httpx.AsyncClient(timeout=25.0) as c:
        # la parte piu' recente vive su /market/candles, quella storica su history-candles
        for path, newest_first in (("/api/v5/market/candles", True),
                                   ("/api/v5/market/history-candles", False)):
            cursor = int(end.timestamp() * 1000)
            for page in range(6000):
                params = {"instId": inst, "bar": "1m", "limit": "100"}
                if page or newest_first:
                    params["after"] = str(cursor)
                for attempt in range(5):
                    r = await c.get(base_url + path, params=params)
                    d = r.json()
                    if d.get("code") == "0":
                        break
                    if d.get("code") == "50011":  # rate limit
                        await asyncio.sleep(0.6 * (attempt + 1))
                        continue
                    raise RuntimeError(f"OKX {path}: {d.get('code')} {d.get('msg')}")
                else:
                    raise RuntimeError(f"OKX {path}: rate limit persistente")
                data = d.get("data") or []
                if not data:
                    break
                oldest = min(int(b[0]) for b in data)
                for b in data:
                    ts = int(b[0])
                    if int(start.timestamp() * 1000) <= ts <= int(end.timestamp() * 1000):
                        bars[ts] = {"ts": ts, "o": float(b[1]), "h": float(b[2]),
                                    "l": float(b[3]), "c": float(b[4])}
                if oldest <= int(start.timestamp() * 1000):
                    break
                cursor = oldest - 60_000
                if path.endswith("history-candles") and not newest_first:
                    pass
                await asyncio.sleep(min_interval)
                if page % 200 == 0 and page:
                    print(f"    {path.rsplit('/', 1)[-1]}: ~{len(bars)} candele")
            if not newest_first:
                # history-candles copre anche il recente: basta la finestra voluta
                break

    out = [bars[k] for k in sorted(bars)]
    if not out:
        raise RuntimeError("nessuna candela scaricata")
    cache.write_text(json.dumps([[b["ts"], b["o"], b["h"], b["l"], b["c"]] for b in out]))
    print(f"  scaricate {len(out)} candele 1m -> {cache.name}")
    return out


# =============================================================================
# 2. Simulatore di uscita (long, come il 100% dei trade reali)
# =============================================================================


def simulate(entry: float, i0: int, bars: Sequence[dict], br: Bracket,
             max_bars: int, use_be: bool = True, use_trail: bool = True) -> dict | None:
    """Esegue il bracket su una long fino a chiusura. None = censurato.

    Ordine per candela, come in produzione:
      1. gli ordini OCO sono vivi durante la candela -> TP/SL possono riempire
         intrabar (high/low);
      2. a candela chiusa si valutano break-even e trailing, che amendano lo SL
         per la candela successiva.
    Se TP e SL cadono nella stessa candela si assume lo SL (caso peggiore):
    su 1m con SL a ~219 EUR il caso e' raro ma va gesto senza ottimismo.

    use_be / use_trail allowscono di misurare il contributo dei due blocchi di
    sicurezza. In produzione il trailing e' subordinato al break-even (Guard 1 di
    _check_and_apply_trailing: senza break_even_triggered non fa nulla), quindi
    "solo trailing" e' un controfattuale che allunga quella guardia.
    """
    sl = br.sl_price(entry)
    tp = br.tp_price(entry)
    levels = br.trail_levels() if use_trail else []
    li = 0
    be_done = False

    for k in range(i0, min(i0 + max_bars, len(bars))):
        b = bars[k]
        if b["h"] >= tp:
            return {"exit": tp, "reason": "take_profit", "bars": k - i0 + 1, "censored": False}
        if b["l"] <= sl:
            reason = "stop_loss_trailing" if li else (
                "stop_loss_breakeven" if be_done else "stop_loss")
            return {"exit": sl, "reason": reason, "bars": k - i0 + 1, "censored": False}

        close = b["c"]
        net = _expected_net_pct_at_exit(entry, close, "BUY", EF, XF)
        # _check_and_apply_break_even: non si allenta mai lo stop, e non si mette
        # uno stop sopra il prezzo corrente
        if use_be and not be_done and net >= BE_TRIGGER_NET:
            cand = entry * _exit_price_ratio(BE_LOCK_NET, EF, XF)
            if cand > sl and cand < close:
                sl, be_done = cand, True
        # _check_and_apply_trailing: un solo step per volta, stesso ordine dei guard
        while li < len(levels):
            trigger, new_net = levels[li]
            if net < trigger:
                break
            cand = entry * _exit_price_ratio(new_net, EF, XF)
            if cand <= sl or cand >= close:
                li += 1  # guardia: scarta lo step, non si tiene indietro
                continue
            sl = cand
            li += 1

    return None


def net_pct(entry: float, exit_price: float) -> float:
    return _expected_net_pct_at_exit(entry, exit_price, "BUY", EF, XF)


# =============================================================================
# 3. Statistiche
# =============================================================================


REASONS = ("take_profit", "stop_loss_trailing", "stop_loss_breakeven", "stop_loss")

# Controfattuali sui due blocchi di sicurezza. In produzione entrambi sono attivi
# e il trailing e' subordinato al break-even; "solo trailing" allunga quella guardia
# solo per misurare il contributo del trailing in isolation.
VARIANTS = {
    "full (produzione)": (True, True),
    "solo break-even": (True, False),
    "solo trailing": (False, True),
    "nessuno": (False, False),
}

# L'override SL/TP per-strategia e' online dal 2026-09-25 15:16 UTC (commit 87a8f03,
# TASK-1256). Prima di allora il bracket era fisso e uguale per tutti, quindi e'
# l'unica era in cui ha senso confrontare trade reali e simulazione sulla stessa
# coppia SL/TP. Dopo, il TP e' +0.751% e il campione non e' confrontabile.
OVERRIDE_ONLINE = datetime(2026, 9, 25, 15, 16, tzinfo=timezone.utc)
TP_GROSS_GLOBAL = 1.0019


def mean(v: Sequence[float]) -> float:
    return sum(v) / len(v) if v else float("nan")


def bootstrap_diff(a: Sequence[float], b: Sequence[float], n: int = 4000,
                   seed: int = 7) -> tuple[float, float, float]:
    """CI 95% e p-value bootstrap per media(a) - media(b)."""
    rng = random.Random(seed)
    diffs = []
    na, nb = len(a), len(b)
    for _ in range(n):
        sa = sum(a[rng.randrange(na)] for _ in range(na)) / na
        sb = sum(b[rng.randrange(nb)] for _ in range(nb)) / nb
        diffs.append(sa - sb)
    diffs.sort()
    lo = diffs[int(0.025 * n)]
    hi = diffs[int(0.975 * n)]
    obs = mean(a) - mean(b)
    p = 2 * min(sum(1 for d in diffs if d <= 0), sum(1 for d in diffs if d >= 0)) / n
    return obs, lo, hi, min(1.0, p)


def describe(name: str, v: Sequence[float], censored: int) -> str:
    if not v:
        return f"  {name:<22} nessun trade risolto"
    s = sorted(v)
    return (f"  {name:<22} n={len(v):<5} media={mean(v):+.4f}%  mediana={s[len(s)//2]:+.4f}%  "
            f"win={sum(1 for x in v if x > 0)/len(v)*100:4.1f}%  "
            f"tot={sum(v)/100*20:+.2f} EUR/20EUR  censurati={censored}")


# =============================================================================
# 4. Orchestrazione
# =============================================================================


def real_entries(fixed_era_only: bool = True) -> list[dict]:
    from supabase import create_client
    u = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_ANON_KEY"])
    rows = u.table("scalping_trades").select(
        "entry_time,entry_price,exit_time,exit_price,pnl_pct,signal_reason,strategy_type,sl_price,tp_price"
    ).eq("status", "closed").execute().data
    out = []
    for r in rows:
        if not (r.get("entry_time") and r.get("exit_time")):
            continue
        t = datetime.fromisoformat(r["entry_time"])
        if fixed_era_only:
            # solo l'era a bracket fisso, e solo i trade il cui TP e' quello globale
            # (esclude 3 outlier con un'altra coppia SL/TP)
            if t >= OVERRIDE_ONLINE:
                continue
            e, tp = float(r["entry_price"]), r.get("tp_price")
            if not e or not tp or abs((float(tp) - e) / e * 100 - TP_GROSS_GLOBAL) > 0.01:
                continue
        out.append({
            "entry_time": t,
            "fill": float(r["entry_price"]),
            "exit_price": float(r["exit_price"] or 0),
            "real_net": float(r["pnl_pct"]) if r.get("pnl_pct") is not None else None,
            "reason": r.get("signal_reason"),
        })
    return out


async def amain() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", type=int, default=5000)
    ap.add_argument("--max-hours", type=float, default=24.0)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--cache", default="")
    ap.add_argument("--grid", action="store_true",
                    help="aggiunge la griglia SL/TP (Parte 3 del report)")
    ap.add_argument("--all-eras", action="store_true",
                    help="includi anche i trade successivi all'override per-strategia")
    args = ap.parse_args()

    from app.config import settings
    base = settings.OKX_BASE_URL.rstrip("/")
    inst = "BTC-EUR"
    rng = random.Random(args.seed)
    max_bars = int(args.max_hours * 60)

    trades = real_entries(fixed_era_only=not args.all_eras)
    lo = min(t["entry_time"] for t in trades) - timedelta(hours=2)
    hi = max(t["entry_time"] for t in trades) + timedelta(hours=2)
    cache = Path(args.cache or f"/tmp/candles_1m_{inst}.json")
    print(f"\n=== 1. DATI  ({lo:%Y-%m-%d %H:%M} .. {hi:%Y-%m-%d %H:%M} UTC) ===")
    bars = await fetch_candles(base, inst, lo, hi, cache)
    idx = {b["ts"]: i for i, b in enumerate(bars)}
    at = lambda t: idx.get(int(t.replace(second=0, microsecond=0).timestamp() * 1000))  # noqa: E731
    print(f"  finestra utilizzabile: {len(bars)} candele")

    # solo orari con abbastanza history davanti, cosi' nessun trade e' censurato
    # per fine-dataset (il bias di coda e' lo stesso nei due bracci)
    limit = len(bars) - max_bars - 1
    real_idx = [(t, at(t["entry_time"])) for t in trades]
    real_idx = [(t, i) for t, i in real_idx if i is not None and 0 <= i < limit]
    print(f"  trade reali con 1m agganciabile e orizzonte pieno: {len(real_idx)}/{len(trades)}")

    for br in [BRACKETS["globale"]]:
        print(f"\n=== 2. VALIDAZIONE — bracket {br.name} "
              f"(SL net {br.sl_net} / TP net {br.tp_net}) ===")
        sim_v, real_v, cens = [], [], 0
        agree = 0
        for t, i in real_idx:
            entry = bars[i]["c"]
            r = simulate(entry, i, bars, br, max_bars)
            if r is None:
                cens += 1
                continue
            sim_v.append(net_pct(entry, r["exit"]))
            if t["real_net"] is not None:
                real_v.append(t["real_net"])
                got = "take_profit" if r["reason"] == "take_profit" else r["reason"]
                if got == (t["reason"] or ""):
                    agree += 1
        print(describe("simulato", sim_v, cens))
        print(describe("realizzato in DB", real_v, 0))
        if sim_v and real_v:
            obs, l, h, p = bootstrap_diff(sim_v, real_v)
            print(f"  simulato - reale = {obs:+.4f}%  CI95 [{l:+.4f}%, {h:+.4f}%]  p={p:.3f}")
            print(f"  motivo d'uscita concordante: {agree}/{len(sim_v)} "
                  f"({agree/len(sim_v)*100:.0f}%)")

    print(f"\n=== 4. CONTROFATTUALI SU BREAK-EVEN E TRAILING ===")
    print("  (era a bracket fisso, bracket globale — unica era confrontabile)")
    br = BRACKETS["globale"]
    rnd_idx = rng.sample(range(0, limit), min(args.sample, limit))
    rows_out = []
    for vname, (use_be, use_trail) in VARIANTS.items():
        a, ca, mix_a = [], 0, {}
        for t, i in real_idx:
            entry = bars[i]["c"]
            r = simulate(entry, i, bars, br, max_bars, use_be, use_trail)
            if r is None:
                ca += 1
            else:
                a.append(net_pct(entry, r["exit"]))
                mix_a[r["reason"]] = mix_a.get(r["reason"], 0) + 1
        b, cb, mix_b = [], 0, {}
        for i in rnd_idx:
            entry = bars[i]["c"]
            r = simulate(entry, i, bars, br, max_bars, use_be, use_trail)
            if r is None:
                cb += 1
            else:
                b.append(net_pct(entry, r["exit"]))
                mix_b[r["reason"]] = mix_b.get(r["reason"], 0) + 1
        rows_out.append((vname, a, ca, mix_a, b, cb, mix_b))

    def split(v: Sequence[float]) -> tuple[float, float]:
        w = [x for x in v if x > 0]
        l = [x for x in v if x <= 0]
        return (mean(w) if w else float("nan")), (mean(l) if l else float("nan"))

    hdr = (f"  {'variante':<18}{'braccio':<9}{'n':>6}{'media':>10}{'win%':>8}"
           f"{'media +':>10}{'media -':>10}{'tot EUR':>10}")
    print("\n  -- entry del bot --")
    print(hdr)
    for vname, a, ca, _, _, _, _ in rows_out:
        mw, ml = split(a)
        print(f"  {vname:<18}{'bot':<9}{len(a):>6}{mean(a):>+9.4f}%{sum(1 for x in a if x>0)/max(1,len(a))*100:>7.1f}%"
              f"{mw:>+9.4f}%{ml:>+9.4f}%{sum(a)/100*20:>+10.2f}")
    print("\n  -- entry casuali --")
    print(hdr)
    for vname, _, _, _, b, cb, _ in rows_out:
        mw, ml = split(b)
        print(f"  {vname:<18}{'casuali':<9}{len(b):>6}{mean(b):>+9.4f}%{sum(1 for x in b if x>0)/max(1,len(b))*100:>7.1f}%"
              f"{mw:>+9.4f}%{ml:>+9.4f}%{sum(b)/100*20:>+10.2f}")

    print("\n  -- bot - casuali, per variante --")
    for vname, a, _, _, b, _, _ in rows_out:
        if a and b:
            obs, l, h, p = bootstrap_diff(a, b)
            verdict = ("batte il caso" if l > 0 else "NON batte" if h < 0 else "indistinguibile")
            print(f"  {vname:<18}{obs:>+9.4f}%  CI95 [{l:+.4f}%, {h:+.4f}%]  p={p:.3f}  {verdict}")

    if args.grid:
        print(f"\n=== 5. GRIGLIA SL/TP ({args.sample} entry casuali, sicurezza ON) ===")
        print("  %-8s%-8s%6s%11s%8s%11s%10s%10s" % (
            "SLnet", "TPnet", "step", "media", "win%", "TP centr.", "media +", "media -"))
        for sl in (0.20, 0.30, 0.50):
            for tp in (0.30, 0.40, 0.55, 0.80):
                g = Bracket("grid", sl_net=sl, tp_net=tp)
                v, ntp = [], 0
                for i in rnd_idx:
                    e = bars[i]["c"]
                    r = simulate(e, i, bars, g, max_bars, True, True)
                    if r:
                        v.append(net_pct(e, r["exit"]))
                        ntp += r["reason"] == "take_profit"
                w = [x for x in v if x > 0]
                l = [x for x in v if x <= 0]
                print("  %-8.2f%-8.2f%6d%10.4f%%%7.1f%%%10.1f%%%9.4f%%%9.4f" % (
                    sl, tp, len(g.trail_levels()), mean(v), len(w)/len(v)*100,
                    ntp/len(v)*100, mean(w), mean(l)))

    print("\n  -- mix motivi d'uscita, braccio bot --")
    print(f"  {'variante':<18}{'TP':>8}{'trail':>8}{'BE':>8}{'SL':>8}")
    for vname, _, _, mix_a, _, _, _ in rows_out:
        n = max(1, sum(mix_a.values()))
        print(f"  {vname:<18}{mix_a.get('take_profit',0)/n*100:>7.1f}%"
              f"{mix_a.get('stop_loss_trailing',0)/n*100:>7.1f}%"
              f"{mix_a.get('stop_loss_breakeven',0)/n*100:>7.1f}%"
              f"{mix_a.get('stop_loss',0)/n*100:>7.1f}%")
    print()


if __name__ == "__main__":
    asyncio.run(amain())
