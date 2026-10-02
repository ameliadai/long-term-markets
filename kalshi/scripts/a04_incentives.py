"""Incentive programs: who gets them (by horizon) and what they change.

1. Coverage and dollars by listing horizon (markets closing in 2026 or later).
2. Market-day panel for long-lived markets (Mar 15 - Aug 31 2026): does a
   market's quoting/trading change on days a liquidity reward is active?
   Two-way fixed effects (market, calendar day), SEs clustered by series.
"""
import numpy as np
import pandas as pd

from common import D, R, candles_for, markets

ip = pd.read_parquet(f"{D}/incentive_programs.parquet")
for c in ["start_date", "end_date"]:
    ip[c] = pd.to_datetime(ip[c], format="ISO8601", utc=True)
ip["usd"] = ip.period_reward / 1e4
ip["kind"] = np.where(ip.incentive_type == "volume", "rw_volume",
                      np.where(ip.incentive_description == "long_dated", "rw_long_dated",
                               "rw_liquidity"))

# ---------------------------------------------------------------- coverage
m = markets()
m = m[m.close_time >= "2026-01-01"]
per = ip.groupby(["market_ticker", "kind"]).usd.sum().unstack(fill_value=0)
m = m.join(per, on="ticker")
kinds = ["rw_liquidity", "rw_long_dated", "rw_volume"]
m[kinds] = m[kinds].fillna(0)
m["rw_usd"] = m[kinds].sum(axis=1)
m["any_liq"] = (m.rw_liquidity + m.rw_long_dated) > 0

g = m.groupby("hz", observed=True)
cov = pd.DataFrame({
    "markets": g.size(),
    "share_liquidity_reward": g.any_liq.mean(),
    "share_long_dated": g.rw_long_dated.apply(lambda x: (x > 0).mean()),
    "share_volume_reward": g.rw_volume.apply(lambda x: (x > 0).mean()),
    "reward_usd": g.rw_usd.sum(),
    "volume_contracts": g.volume.sum(),
})
cov["reward_usd_per_1k_contracts"] = 1000 * cov.reward_usd / cov.volume_contracts
cov["reward_usd_per_rewarded_market"] = g.apply(lambda d: d.rw_usd[d.rw_usd > 0].mean())
print("== reward coverage by listing horizon (markets closing 2026+) ==")
print(cov.round(3).to_string())
cov.to_csv(f"{R}/04_reward_coverage_by_horizon.csv")

gc = m[m.hz.isin(["6-12m", "1-2y", ">2y"])].groupby("group")
covg = pd.DataFrame({"markets": gc.size(), "share_liquidity_reward": gc.any_liq.mean(),
                     "reward_usd": gc.rw_usd.sum(), "volume_contracts": gc.volume.sum()})
covg["reward_usd_per_1k_contracts"] = 1000 * covg.reward_usd / covg.volume_contracts
print("\n== markets listed 6+ months ahead, by group ==")
print(covg.round(3).to_string())
covg.to_csv(f"{R}/04_reward_coverage_long_by_group.csv")

# ---------------------------------------------------------------- panel
START, END = pd.Timestamp("2026-03-15", tz="UTC"), pd.Timestamp("2026-08-31", tz="UTC")
pm = m[(m.horizon_days >= 60) & (m.open_time < END) & (m.close_time > START + pd.Timedelta(days=30))
       & (m.volume > 0)]
c = candles_for(pm.ticker)
c = c[(c.day >= START) & (c.day <= END)]
c = c.merge(pm[["ticker", "series_ticker", "close_time", "group"]], on="ticker")
c = c[c.day < c.close_time.dt.floor("D") - pd.Timedelta(days=1)]  # drop final days

for kind, sub in ip[ip.market_ticker.isin(set(pm.ticker)) & (ip.incentive_type == "liquidity")].groupby("kind"):
    s = sub[["market_ticker", "start_date", "end_date"]].copy().reset_index(drop=True)
    s["d0"] = s.start_date.dt.floor("D")
    s["n"] = ((s.end_date.dt.floor("D") - s.d0).dt.days + 1).clip(lower=1)
    rep = s.loc[s.index.repeat(s.n)].copy()
    rep["day"] = rep.d0 + pd.to_timedelta(rep.groupby(level=0).cumcount(), unit="D")
    rep = rep[["market_ticker", "day"]].drop_duplicates().rename(columns={"market_ticker": "ticker"})
    rep[kind] = 1.0
    c = c.merge(rep, on=["ticker", "day"], how="left")
for k in ["rw_liquidity", "rw_long_dated"]:
    if k not in c:
        c[k] = 0.0
    c[k] = c[k].fillna(0.0)

c["traded"] = (c.volume > 0).astype(float)
c["log_volume"] = np.log1p(c.volume)
c["dtc"] = (c.close_time - c.day).dt.days
c["dtc_bin"] = pd.cut(c.dtc, [0, 7, 30, 90, 180, 365, 1e5]).astype(str)
print(f"\npanel: {c.ticker.nunique()} markets, {len(c)} market-days, "
      f"{int((c.rw_long_dated > 0).sum())} long-dated reward days, "
      f"{int((c.rw_liquidity > 0).sum())} other reward days")
pd.Series({"markets": c.ticker.nunique(), "market_days": len(c)}).to_json(f"{R}/04_sample.json")


def twfe(df, y, xs, fe=("ticker", "day"), cluster="series_ticker", iters=30):
    """OLS of y on xs after sweeping out two sets of fixed effects."""
    df = df.dropna(subset=[y]).reset_index(drop=True)
    Z = df[[y] + xs].astype(float)
    keys = [df[f].astype(str).values for f in fe]
    for _ in range(iters):
        for k in keys:
            Z = Z - Z.groupby(k).transform("mean")
    X, Y = Z[xs].values, Z[y].values
    beta = np.linalg.lstsq(X, Y, rcond=None)[0]
    u = Y - X @ beta
    XtX_inv = np.linalg.pinv(X.T @ X)
    Xu = pd.DataFrame(X * u[:, None]).groupby(df[cluster].values).sum().values
    G = len(Xu)
    V = XtX_inv @ (Xu.T @ Xu) @ XtX_inv * G / (G - 1)
    se = np.sqrt(np.diag(V))
    return pd.DataFrame({"coef": beta, "se": se, "t": beta / se}, index=xs).assign(
        outcome=y, n=len(df), mean_y=df[y].mean(), clusters=G)


dtc_d = pd.get_dummies(c.dtc_bin, prefix="dtc", drop_first=True, dtype=float)
c = pd.concat([c, dtc_d], axis=1)
xs = ["rw_long_dated", "rw_liquidity"] + list(dtc_d.columns)
res = []
for y in ["two_sided_share", "spread_med", "traded", "log_volume"]:
    r = twfe(c, y, xs)
    res.append(r.loc[["rw_long_dated", "rw_liquidity"]])
res = pd.concat(res).reset_index().rename(columns={"index": "reward"})
print("\n== within-market effect of an active liquidity reward (market + day FE) ==")
print(res.round(4).to_string())
res.to_csv(f"{R}/04_reward_effects_twfe.csv", index=False)

first = c[c.rw_long_dated > 0].groupby("ticker").day.min().rename("t0")
e = c.join(first, on="ticker", how="inner")
e["week"] = ((e.day - e.t0).dt.days // 7).clip(-6, 14)
es = e.groupby("week").agg(markets=("ticker", "nunique"), two_sided=("two_sided_share", "mean"),
                           spread=("spread_med", "median"), traded=("traded", "mean"),
                           ld_active=("rw_long_dated", "mean"), other_active=("rw_liquidity", "mean"))
print("\n== weeks relative to first long-dated reward day (treated markets) ==")
print(es.round(3).to_string())
es.to_csv(f"{R}/04_long_dated_event_study.csv")
c.drop(columns=list(dtc_d.columns)).to_parquet(f"{R}/04_panel.parquet", index=False)
