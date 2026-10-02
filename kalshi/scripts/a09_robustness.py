"""Three robustness checks suggested for the advisor review.

1. Calibration by horizon: reliability curves (10 price bins) at 1/7/30/90/180
   days before close, expected calibration error (ECE, 95% CI over events), and
   the Murphy decomposition Brier = reliability - resolution + uncertainty.
2. Favourite returns: thresholds p >= 0.70 / 0.80 / 0.90, and three price
   definitions (midpoint only, last trade only, midpoint-else-trade as before).
3. Reward days and moves toward the outcome using only fresh prices (no
   forward fill), including trade-only and midpoint-only versions.
"""
import os

import numpy as np
import pandas as pd

from a04_twfe import twfe
from common import R, markets

rng = np.random.default_rng(0)
KS = [1, 7, 30, 90, 180]
mk = markets()[["ticker", "event_ticker", "status", "result"]]

# ------------------------------------------------------------------ 1. calibration
P = pd.read_parquet(f"{R}/03_prices_at_k.parquet", columns=["ticker", "k", "p", "y", "bid_close", "ask_close", "price_close"])
P = P.merge(mk[["ticker", "event_ticker"]], on="ticker", how="left")
EDGES = np.linspace(0, 1, 11)


def decompose(d):
    d = d.assign(bin=pd.cut(d.p, EDGES, include_lowest=True, labels=False))
    g = d.groupby("bin").agg(n=("y", "size"), pred=("p", "mean"), obs=("y", "mean"))
    N, ybar = len(d), d.y.mean()
    rel = (g.n * (g.pred - g.obs) ** 2).sum() / N
    res = (g.n * (g.obs - ybar) ** 2).sum() / N
    ece = (g.n * (g.pred - g.obs).abs()).sum() / N
    return {"brier": ((d.p - d.y) ** 2).mean(), "reliability": rel, "resolution": res,
            "uncertainty": ybar * (1 - ybar), "ece": ece}, g


def ece_ci(d, reps=500):
    ev = d.event_ticker.values
    uniq = pd.unique(ev)
    groups = {e: i for i, e in enumerate(uniq)}
    idx_by = pd.Series(np.arange(len(d))).groupby(pd.Series(ev).map(groups)).apply(np.array).values
    out = []
    for _ in range(reps):
        pick = rng.integers(0, len(uniq), len(uniq))
        rows = np.concatenate([idx_by[i] for i in pick])
        out.append(decompose(d.iloc[rows])[0]["ece"])
    return np.percentile(out, [2.5, 97.5])


cal_rows, curve_rows = [], []
for sample, sel in [("all markets priced at k", None), ("same 476 markets (open 180+ days)", "fixed")]:
    if sel == "fixed":
        ids = set.intersection(*[set(P[P.k == k].ticker) for k in KS])
    for k in KS:
        d = P[P.k == k]
        if sel == "fixed":
            d = d[d.ticker.isin(ids)]
        stats, g = decompose(d)
        lo, hi = ece_ci(d)
        cal_rows.append({"sample": sample, "k": k, "markets": len(d), "events": d.event_ticker.nunique(),
                         **stats, "ece_lo": lo, "ece_hi": hi})
        if sel is None:
            for b, r in g.iterrows():
                curve_rows.append({"k": k, "bin": int(b), "n": int(r.n), "mean_pred": r.pred, "mean_obs": r.obs})
CAL = pd.DataFrame(cal_rows)
CAL.to_csv(f"{R}/09_calibration_by_horizon.csv", index=False)
pd.DataFrame(curve_rows).to_csv(f"{R}/09_calibration_curves.csv", index=False)
pd.set_option("display.width", 220)
print(CAL.round(4).to_string())

# ------------------------------------------------------------------ 2. favourite returns
two = (P.bid_close > 0) & (P.ask_close < 1) & (P.ask_close > P.bid_close)
P["p_mid"] = np.where(two, (P.bid_close + P.ask_close) / 2, np.nan)
P["p_trade"] = P.price_close
PRICES = {"midpoint else last trade (baseline)": "p", "midpoint only": "p_mid", "last trade only": "p_trade"}


def fav_return(d, col, reps=1000):
    r = d.y / d[col] - 1
    ev = r.groupby(d.event_ticker).mean()
    boot = [ev.values[rng.integers(0, len(ev), len(ev))].mean() for _ in range(reps)]
    return ev.mean(), np.percentile(boot, 2.5), np.percentile(boot, 97.5), len(d), len(ev)


fav = []
for label, col in PRICES.items():
    for thr in [0.7, 0.8, 0.9]:
        for k in KS:
            d = P[(P.k == k) & (P[col] >= thr) & (P[col] < 1)]
            if len(d) < 20:
                continue
            ret, lo, hi, n, ne = fav_return(d, col)
            fav.append({"price": label, "threshold": thr, "k": k, "markets": n, "events": ne,
                        "mean_price": d[col].mean(), "came_true": d.y.mean(),
                        "return": ret, "ci_lo": lo, "ci_hi": hi})
FAV = pd.DataFrame(fav)
FAV.to_csv(f"{R}/09_favourite_robustness.csv", index=False)
print(FAV.pivot_table(index=["price", "threshold"], columns="k", values="return").round(3).to_string())
print(FAV.pivot_table(index=["price", "threshold"], columns="k", values="events").to_string())

# ------------------------------------------------------------------ 3. reward days, fresh prices only
if os.path.exists(f"{R}/04_panel.parquet"):   # the reward panel exists only for Kalshi
    p = pd.read_parquet(f"{R}/04_panel.parquet")
    p = p.merge(mk[["ticker", "status", "result"]], on="ticker")
    p = p[(p.status == "finalized") & p.result.isin(["yes", "no"])].copy()
    p["y"] = (p.result == "yes").astype(float)
    two = (p.bid_close > 0) & (p.ask_close < 1) & (p.ask_close > p.bid_close)
    p["mid"] = np.where(two, (p.bid_close + p.ask_close) / 2, np.nan)
    p["trade"] = p.price_close
    p["fresh"] = p.mid.fillna(p.trade)
    p = p.sort_values(["ticker", "day"])
    p["prev_day"] = p.groupby("ticker").day.shift()
    consecutive = (p.day - p.prev_day).dt.days == 1
    dtc_d = pd.get_dummies(p.dtc_bin, prefix="dtc", drop_first=True, dtype=float)
    p = pd.concat([p, dtc_d], axis=1)
    xs = ["rw_long_dated", "rw_liquidity"] + list(dtc_d.columns)

    variants = {}
    ff = p.groupby("ticker").fresh.ffill()
    variants["forward-filled prices (baseline)"] = (ff, p.assign(_f=ff).groupby("ticker")._f.shift(), pd.Series(True, index=p.index))
    for name, col in [("fresh price both days (midpoint or trade)", "fresh"), ("trade price both days", "trade"), ("midpoint both days", "mid")]:
        variants[name] = (p[col], p.groupby("ticker")[col].shift(), consecutive)

    rows = []
    for name, (cur, prev, ok) in variants.items():
        d = p.assign(cur=cur, prev=prev)
        d = d[ok & d.cur.notna() & d.prev.notna()].copy()
        d["info_gain"] = (d.prev - d.y) ** 2 - (d.cur - d.y) ** 2
        r = twfe(d, "info_gain", xs).loc[["rw_long_dated", "rw_liquidity"]]
        r["variant"] = name
        r["markets"] = d.ticker.nunique()
        rows.append(r.reset_index().rename(columns={"index": "reward"}))
    FR = pd.concat(rows, ignore_index=True)
    FR.to_csv(f"{R}/09_reward_info_fresh.csv", index=False)
    print(FR[["variant", "reward", "coef", "se", "t", "n", "markets", "mean_y"]].round(5).to_string())

# reference for the favourite plot: buying YES in near-50/50 markets (40-60¢), where the
# waiting cost should not push the price either way
ref = []
for k in KS:
    d = P[(P.k == k) & (P.p >= 0.4) & (P.p <= 0.6)]
    ret, lo, hi, n, ne = fav_return(d, "p")
    ref.append({"k": k, "markets": n, "events": ne, "return": ret, "ci_lo": lo, "ci_hi": hi})
pd.DataFrame(ref).to_csv(f"{R}/09_fav_reference_4060.csv", index=False)
print(pd.DataFrame(ref).round(3).to_string())
