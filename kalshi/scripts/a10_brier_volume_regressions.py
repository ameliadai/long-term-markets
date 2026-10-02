"""Brier score on cumulative prior volume, contract-day panel.

Unit: one settled yes/no market ("contract") on one day. Price that day = the bid/ask
midpoint at the day's last hourly bar; days without a two-sided quote are dropped (a last
trade can be days old and would tie low volume to stale prices).
    Brier[m,d]   = (price[m,d] - outcome[m])^2
    log_cum_vol  = log(1 + contracts traded in market m before day d)
    days_to_exp  = days from d to the market's close

Specifications (SEs clustered by event):
  (1) Brier ~ log_cum_vol + days_to_exp | month-year FE
  (2) Brier ~ log_cum_vol + days_to_exp + duration_days | month-year FE + category FE
  (3) Brier ~ log_cum_vol + days_to_exp | month-year FE + contract FE
  (4) Brier ~ log_cum_vol | month-year FE + contract FE + days-to-expiry bin FE
      (20 bins, in days, lower end included: 0-1, 1-2, ..., 6-7, 7-14, 14-21, 21-28, 28-42, 42-56,
       56-90, 90-120, 120-150, 150-180, 180-240, 240-300, 300-365, 365+)
Samples: all; initial duration > 180 days; expired in 2026; expired in 2025.
Variants: "all days", and "drop last day" (the market's last day with any price, quote or trade,
is removed; on that day the price usually already reflects the outcome).
Also writes the category mix (markets, market-days) of the first two samples, and specs (1), (3), (4)
run separately for each category in those samples (categories with fewer than MIN_EVENTS events are
marked "too few events").
"""
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from common import D, R

m = pd.read_parquet(f"{D}/markets.parquet", columns=[
    "ticker", "event_ticker", "status", "result", "open_time", "close_time", "horizon_days", "category"])
m = m[(m.status == "finalized") & m.result.isin(["yes", "no"])].copy()
m["y"] = (m.result == "yes").astype(np.float64)

t = pq.read_table(f"{D}/candles_daily.parquet", columns=["ticker", "day", "volume", "price_close", "bid_close", "ask_close"])
t = t.filter(pc.is_in(t.column("ticker"), value_set=pa.array(m.ticker.tolist()))).to_pandas()
t = t.sort_values(["ticker", "day"])
t["cum_prior_vol"] = t.groupby("ticker").volume.cumsum() - t.volume
two = (t.bid_close > 0) & (t.ask_close < 1) & (t.ask_close > t.bid_close)
t = t[two | t.price_close.notna()].assign(two_sided=two)
t = t.merge(m[["ticker", "event_ticker", "y", "close_time", "horizon_days", "category"]], on="ticker")
t["days_to_exp"] = (t.close_time - t.day).dt.total_seconds() / 86400
t = t[t.days_to_exp >= 0]
# the market's last day with any price (quote or trade); flagged before stale-price days are dropped
t["last_day"] = ~t.ticker.duplicated(keep="last")      # t is sorted by ticker, day
t = t[t.two_sided].copy()
t["price"] = (t.bid_close + t.ask_close) / 2
t["brier"] = (t.price - t.y) ** 2
t["log_cum_vol"] = np.log1p(t.cum_prior_vol.clip(lower=0))
t["month"] = t.day.dt.strftime("%Y-%m")
HZ_EDGES = [0, 1, 2, 3, 4, 5, 6, 7, 14, 21, 28, 42, 56, 90, 120, 150, 180, 240, 300, 365, np.inf]
t["hz_bin"] = pd.cut(t.days_to_exp, HZ_EDGES, right=False, labels=False)
t["exp_year"] = t.close_time.dt.year
t["category"] = t.category.fillna("Unknown")
print(f"panel: {len(t):,} contract-days, {t.ticker.nunique():,} contracts, {t.event_ticker.nunique():,} events")


def codes(s):
    return pd.factorize(s)[0]


def fe_ols(df, y, xs, fes, cluster="event_ticker", tol=1e-8, max_iter=1000):
    """OLS of y on xs absorbing the fixed effects in `fes`; SEs clustered by `cluster`."""
    Z = df[[y] + xs].to_numpy(np.float64).copy()
    groups = [codes(df[f]) for f in fes]
    counts = [np.bincount(g) for g in groups]
    for _ in range(max_iter):
        prev = Z.copy()
        for g, n in zip(groups, counts):
            for j in range(Z.shape[1]):
                Z[:, j] -= (np.bincount(g, weights=Z[:, j]) / n)[g]
        if len(groups) == 1 or np.abs(Z - prev).max() < tol:
            break
    Y, X = Z[:, 0], Z[:, 1:]
    XtX_inv = np.linalg.pinv(X.T @ X)
    beta = XtX_inv @ X.T @ Y
    u = Y - X @ beta
    cl = codes(df[cluster])
    S = np.column_stack([np.bincount(cl, weights=X[:, j] * u) for j in range(X.shape[1])])
    G = S.shape[0]
    V = XtX_inv @ (S.T @ S) @ XtX_inv * G / (G - 1)
    se = np.sqrt(np.diag(V))
    r2_within = 1 - (u @ u) / (Y @ Y)
    return beta, se, G, r2_within


SPECS = {
    "(1) month FE": (["log_cum_vol", "days_to_exp"], ["month"]),
    "(2) + category FE + duration": (["log_cum_vol", "days_to_exp", "horizon_days"], ["month", "category"]),
    "(3) month FE + contract FE": (["log_cum_vol", "days_to_exp"], ["month", "ticker"]),
    "(4) + days-to-expiry bins": (["log_cum_vol"], ["month", "ticker", "hz_bin"]),
}
VARIANTS = {"all days": t, "drop last day": t[~t.last_day]}
rows, mix = [], []
for vname, tv in VARIANTS.items():
    samples = {
        "all": tv,
        "duration > 180 days": tv[tv.horizon_days > 180],
        "expired in 2026": tv[tv.exp_year == 2026],
        "expired in 2025": tv[tv.exp_year == 2025],
    }
    mix += [samples[s].groupby("category").agg(markets=("ticker", "nunique"), market_days=("ticker", "size"))
            .reset_index().assign(sample=s, variant=vname) for s in ("all", "duration > 180 days")]
    for sname, d in samples.items():
        for spec, (xs, fes) in SPECS.items():
            base = {"variant": vname, "sample": sname, "spec": spec, "n": len(d),
                    "contracts": d.ticker.nunique() if len(d) else 0, "events": d.event_ticker.nunique() if len(d) else 0,
                    "mean_brier": d.brier.mean() if len(d) else np.nan}
            if len(d) < 100:
                rows.append({**base, "note": "too few observations"})
                continue
            beta, se, G, r2 = fe_ols(d, "brier", xs, fes)
            for x, b, s in zip(xs, beta, se):
                rows.append({**base, "term": x, "coef": b, "se": s, "t": b / s, "clusters": G, "r2_within": r2})
            print(vname, "|", sname, "|", spec, "| n =", f"{len(d):,}", "|",
                  ", ".join(f"{x}: {b:.5f} ({s:.5f})" for x, b, s in zip(xs, beta, se)), flush=True)
pd.concat(mix).to_csv(f"{R}/10_category_mix.csv", index=False)

MIN_EVENTS = 20
cat_rows = []
for vname, tv in VARIANTS.items():
    for sname, d0 in {"all": tv, "duration > 180 days": tv[tv.horizon_days > 180]}.items():
        for cat, d in d0.groupby("category"):
            for spec in ("(1) month FE", "(3) month FE + contract FE", "(4) + days-to-expiry bins"):
                xs, fes = SPECS[spec]
                base = {"variant": vname, "sample": sname, "category": cat, "spec": spec, "n": len(d),
                        "contracts": d.ticker.nunique(), "events": d.event_ticker.nunique(), "mean_brier": d.brier.mean()}
                if base["events"] < MIN_EVENTS:
                    cat_rows.append({**base, "note": "too few events"})
                    continue
                beta, se, G, r2 = fe_ols(d, "brier", xs, fes)
                for x, b, s in zip(xs, beta, se):
                    cat_rows.append({**base, "term": x, "coef": b, "se": s, "t": b / s, "clusters": G})
pd.DataFrame(cat_rows).to_csv(f"{R}/10_by_category.csv", index=False)
out = pd.DataFrame(rows)
out.to_csv(f"{R}/10_brier_volume_regressions.csv", index=False)
