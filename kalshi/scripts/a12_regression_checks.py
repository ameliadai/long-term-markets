"""Robustness checks for the Brier-on-volume regressions (a10). Exploratory.

Panel: as in a10 (settled yes/no markets, one row per market-day with a price), with each
market's last day dropped. Every check is run for specs (1) month FE and (3) month + contract
FE, on all markets and on markets open > 180 days; SEs clustered by event.

  base         a10 as is: Brier ~ LogVol + DaysToExpiry
  hz_bins      DaysToExpiry replaced by fixed effects for days-to-expiry bins
  two_sided    only days with a two-sided quote (price = bid/ask midpoint, never a stale trade)
  two_sided+hz both of the above
  single_mkt   only events with a single market (no multi-outcome events)
  w_event      each event weighted equally
  w_market     each market weighted equally
  vol7         LogVol replaced by log(1 + volume over the previous 7 days)
  oi           LogVol replaced by log(1 + open interest at the previous day's close)
  all_fixes    two-sided days, days-to-expiry bins, each event weighted equally
Reward programs (liquidity rewards, the subsidy Kalshi pays market makers):
  rw_reduced   Brier ~ RewardActive + DaysToExpiry   (reward active at some point that day)
  rw_first     LogVol ~ LogCumRewardUSD + DaysToExpiry   (first stage)
  rw_iv        Brier ~ LogVol + DaysToExpiry, LogVol instrumented by LogCumRewardUSD
               (reward dollars posted for the market before day d)
  rw_reduced_cum[_hz]  Brier ~ LogCumRewardUSD (+ DaysToExpiry, or days-to-expiry bins)
  rw_iv_hz     rw_iv with days-to-expiry bins instead of the linear term
  rw_placebo_hz  Brier ~ log(1 + reward dollars posted after day d) with days-to-expiry bins;
               future rewards cannot cause today's accuracy, so a non-zero coefficient means the
               reward instrument also picks up which markets / periods get rewarded
Writes results/12_regression_checks.csv.
"""
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from common import D, R

# ---------------------------------------------------------------- panel (as in a10)
m = pd.read_parquet(f"{D}/markets.parquet", columns=[
    "ticker", "event_ticker", "status", "result", "close_time", "horizon_days", "category"])
m = m[(m.status == "finalized") & m.result.isin(["yes", "no"])].copy()
m["y"] = (m.result == "yes").astype(np.float64)
m["event_markets"] = m.groupby("event_ticker").ticker.transform("size")

t = pq.read_table(f"{D}/candles_daily.parquet", columns=["ticker", "day", "volume", "price_close", "bid_close", "ask_close", "oi_close"])
t = t.filter(pc.is_in(t.column("ticker"), value_set=pa.array(m.ticker.tolist()))).to_pandas()
t = t.sort_values(["ticker", "day"]).reset_index(drop=True)
t["cum_prior_vol"] = t.groupby("ticker").volume.cumsum() - t.volume
t["vol7"] = (t.set_index("day").groupby("ticker").volume.rolling("7D", closed="left").sum()
             .reset_index(drop=True).fillna(0).to_numpy())
t["oi_prev"] = t.groupby("ticker").oi_close.shift(1).fillna(0)
t["two_sided"] = (t.bid_close > 0) & (t.ask_close < 1) & (t.ask_close > t.bid_close)
t["price"] = np.where(t.two_sided, (t.bid_close + t.ask_close) / 2, t.price_close)
t = t.dropna(subset=["price"])
t = t.merge(m[["ticker", "event_ticker", "y", "close_time", "horizon_days", "category", "event_markets"]], on="ticker")
t["days_to_exp"] = (t.close_time - t.day).dt.total_seconds() / 86400
t = t[t.days_to_exp >= 0]
t["last_day"] = ~t.ticker.duplicated(keep="last")
t = t[~t.last_day].copy()
t["brier"] = (t.price - t.y) ** 2
t["log_cum_vol"] = np.log1p(t.cum_prior_vol.clip(lower=0))
t["log_vol7"] = np.log1p(t.vol7.clip(lower=0))
t["log_oi"] = np.log1p(t.oi_prev.clip(lower=0))
t["month"] = t.day.dt.strftime("%Y-%m")
EDGES = [0, 1, 2, 3, 4, 5, 6, 7, 14, 21, 28, 42, 56, 90, 120, 150, 180, 240, 300, 365, np.inf]
t["hz_bin"] = pd.cut(t.days_to_exp, EDGES, right=False, labels=False)
t["w_event"] = 1 / t.groupby("event_ticker").ticker.transform("size")
t["w_market"] = 1 / t.groupby("ticker").ticker.transform("size")

# ---------------------------------------------------------------- reward exposure
ip = pd.read_parquet(f"{D}/incentive_programs.parquet", columns=["market_ticker", "start_date", "end_date", "incentive_type", "period_reward"])
ip = ip[(ip.incentive_type == "liquidity") & ip.market_ticker.isin(set(t.ticker))].copy()
for c in ["start_date", "end_date"]:
    ip[c] = pd.to_datetime(ip[c], format="ISO8601", utc=True)
ip["usd"] = ip.period_reward / 1e4
days = [pd.date_range(s.floor("D"), e.floor("D"), freq="D") for s, e in zip(ip.start_date, ip.end_date)]
active = pd.DataFrame({"ticker": np.repeat(ip.market_ticker.to_numpy(), [len(x) for x in days]),
                       "day": np.concatenate(days) if days else []}).drop_duplicates()
active["day"] = pd.to_datetime(active.day, utc=True).astype(t.day.dtype)
active["reward_active"] = 1.0
t = t.merge(active, on=["ticker", "day"], how="left")
t["reward_active"] = t.reward_active.fillna(0)
cum = ip.sort_values("start_date")[["market_ticker", "start_date", "usd"]].rename(columns={"market_ticker": "ticker"})
cum["cum_usd"] = cum.groupby("ticker").usd.cumsum()
cum["start_date"] = cum.start_date.astype(t.day.dtype)
t = pd.merge_asof(t.sort_values("day"), cum.sort_values("start_date")[["ticker", "start_date", "cum_usd"]],
                  left_on="day", right_on="start_date", by="ticker", direction="backward", allow_exact_matches=False)
t["log_cum_reward"] = np.log1p(t.cum_usd.fillna(0))
t["next_day"] = t.day + pd.Timedelta(days=1)
t = pd.merge_asof(t.sort_values("next_day"), cum.sort_values("start_date")[["ticker", "start_date", "cum_usd"]]
                  .rename(columns={"start_date": "start2", "cum_usd": "cum_usd_thru"}),
                  left_on="next_day", right_on="start2", by="ticker", direction="backward", allow_exact_matches=False)
t["future_usd"] = t.ticker.map(ip.groupby("market_ticker").usd.sum()).fillna(0) - t.cum_usd_thru.fillna(0)
t["log_future_reward"] = np.log1p(t.future_usd.clip(lower=0))
REWARD_START = ip.start_date.min().floor("D")
t["reward_era"] = t.day >= REWARD_START
t["single_mkt"] = t.event_markets == 1
print(f"panel: {len(t):,} market-days, {t.ticker.nunique():,} markets; reward active on {t.reward_active.mean():.1%} of days; "
      f"liquidity programs from {REWARD_START.date()}", flush=True)


# ---------------------------------------------------------------- estimation
def demean(Z, groups, w, tol=1e-8, max_iter=500):
    Z = Z.copy()
    counts = [np.bincount(g, weights=w) for g in groups]
    for _ in range(max_iter):
        prev = Z.copy()
        for g, n in zip(groups, counts):
            for j in range(Z.shape[1]):
                Z[:, j] -= (np.bincount(g, weights=w * Z[:, j]) / n)[g]
        if len(groups) == 1 or np.abs(Z - prev).max() < tol:
            break
    return Z


def fe_ols(df, y, xs, fes, weight=None, iv=None, cluster="event_ticker"):
    """Weighted OLS absorbing `fes`; if iv=(endog, instrument), 2SLS with that one instrument.
    Returns coef, se for xs, plus the first-stage t on the instrument."""
    w = df[weight].to_numpy(np.float64) if weight else np.ones(len(df))
    cols = [y] + xs + ([iv[1]] if iv else [])
    Z = demean(df[cols].to_numpy(np.float64), [pd.factorize(df[f])[0] for f in fes], w)
    Y, X = Z[:, 0], Z[:, 1:1 + len(xs)]
    cl = pd.factorize(df[cluster])[0]
    first_t = np.nan
    if iv:
        j = xs.index(iv[0])
        W = np.column_stack([Z[:, -1]] + [X[:, k] for k in range(len(xs)) if k != j])   # instruments
        g1 = np.linalg.solve(W.T @ (W * w[:, None]), W.T @ (X[:, j] * w))
        e1 = X[:, j] - W @ g1
        A1 = np.linalg.pinv(W.T @ (W * w[:, None]))
        S1 = np.column_stack([np.bincount(cl, weights=w * W[:, k] * e1) for k in range(W.shape[1])])
        first_t = g1[0] / np.sqrt((A1 @ S1.T @ S1 @ A1)[0, 0])
        Xh = X.copy()
        Xh[:, j] = W @ g1
    else:
        Xh = X
    A = np.linalg.pinv(Xh.T @ (X * w[:, None]))
    beta = A @ Xh.T @ (Y * w)
    u = Y - X @ beta
    S = np.column_stack([np.bincount(cl, weights=w * Xh[:, k] * u) for k in range(X.shape[1])])
    G = S.shape[0]
    V = A @ (S.T @ S) @ A.T * G / (G - 1)
    return beta, np.sqrt(np.diag(V)), first_t


CHECKS = {   # name: (subset, x variables, extra fixed effects, weight, iv)
    "base": (None, ["log_cum_vol", "days_to_exp"], [], None, None),
    "hz_bins": (None, ["log_cum_vol"], ["hz_bin"], None, None),
    "two_sided": ("two_sided", ["log_cum_vol", "days_to_exp"], [], None, None),
    "two_sided+hz": ("two_sided", ["log_cum_vol"], ["hz_bin"], None, None),
    "single_mkt": ("single_mkt", ["log_cum_vol", "days_to_exp"], [], None, None),
    "w_event": (None, ["log_cum_vol", "days_to_exp"], [], "w_event", None),
    "w_market": (None, ["log_cum_vol", "days_to_exp"], [], "w_market", None),
    "vol7": (None, ["log_vol7", "days_to_exp"], [], None, None),
    "oi": (None, ["log_oi", "days_to_exp"], [], None, None),
    "all_fixes": ("two_sided", ["log_cum_vol"], ["hz_bin"], "w_event", None),
    "rw_reduced": ("reward_era", ["reward_active", "days_to_exp"], [], None, None),
    "rw_first": ("reward_era", ["log_cum_reward", "days_to_exp"], [], None, None),
    "rw_iv": ("reward_era", ["log_cum_vol", "days_to_exp"], [], None, ("log_cum_vol", "log_cum_reward")),
    "rw_reduced_cum": ("reward_era", ["log_cum_reward", "days_to_exp"], [], None, None),
    "rw_reduced_cum_hz": ("reward_era", ["log_cum_reward"], ["hz_bin"], None, None),
    "rw_iv_hz": ("reward_era", ["log_cum_vol"], ["hz_bin"], None, ("log_cum_vol", "log_cum_reward")),
    "rw_placebo_hz": ("reward_era", ["log_future_reward"], ["hz_bin"], None, None),
}
SPECS = {"(1) month FE": ["month"], "(3) month + contract FE": ["month", "ticker"]}
rows = []
for sname, d0 in {"all": t, "duration > 180 days": t[t.horizon_days > 180]}.items():
    for check, (sub, xs, extra, weight, iv) in CHECKS.items():
        d = d0[d0[sub]] if sub else d0
        for spec, fes in SPECS.items():
            base = {"sample": sname, "check": check, "spec": spec, "n": len(d), "markets": d.ticker.nunique(),
                    "events": d.event_ticker.nunique()}
            if base["events"] < 20:
                rows.append({**base, "note": "too few events"})
                continue
            b, se, ft = fe_ols(d, "brier" if check != "rw_first" else "log_cum_vol",
                               xs, fes + extra, weight, iv)
            rows.append({**base, "term": xs[0], "coef": b[0], "se": se[0], "t": b[0] / se[0], "first_stage_t": ft})
            print(f"{sname:<20} {check:<13} {spec:<24} n={len(d):>9,}  {xs[0]}: {b[0]:+.5f} ({se[0]:.5f}) t={b[0] / se[0]:+.1f}"
                  + (f"  first-stage t={ft:.1f}" if iv else ""), flush=True)
pd.DataFrame(rows).to_csv(f"{R}/12_regression_checks.csv", index=False)
