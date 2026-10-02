"""How informative are prices at different distances from resolution?

For settled yes/no markets, take the market's probability k days before close
(mid of bid/ask when two-sided, otherwise last traded price) and score it
against the outcome: Brier score, AUC, and calibration.
"""
import numpy as np, pandas as pd
from sklearn.metrics import roc_auc_score
from common import markets, candles_for, R

KS = [1, 7, 30, 90, 180, 365]
m = markets(min_horizon=30)
m = m[(m.status == "finalized") & m.result.isin(["yes", "no"]) & (m.volume > 0)]
m["y"] = (m.result == "yes").astype(int)
c = candles_for(m.ticker)
two = (c.bid_close > 0) & (c.ask_close < 1) & (c.ask_close > c.bid_close)
c["p"] = np.where(two, (c.bid_close + c.ask_close) / 2, c.price_close)
c = c.dropna(subset=["p"]).sort_values(["ticker", "day"])
c = c.merge(m[["ticker", "close_time", "horizon_days", "y", "group", "volume"]], on="ticker")
c["dtc"] = (c.close_time - c.day).dt.total_seconds() / 86400

rows = []
for k in KS:
    # last observation at least k days before close
    s = c[c.dtc >= k].groupby("ticker").tail(1)
    s = s[s.dtc < k + max(3, 0.1 * k)]  # require a fresh quote near the target date
    s["k"] = k
    rows.append(s)
P = pd.concat(rows)
P.to_parquet(f"{R}/03_prices_at_k.parquet", index=False)

def score(df):
    out = {"markets": len(df), "yes_rate": df.y.mean(), "mean_p": df.p.mean(),
           "brier": ((df.p - df.y) ** 2).mean()}
    out["brier_base_rate"] = ((df.y.mean() - df.y) ** 2).mean()
    out["skill_vs_base"] = 1 - out["brier"] / out["brier_base_rate"] if out["brier_base_rate"] > 0 else np.nan
    out["auc"] = roc_auc_score(df.y, df.p) if df.y.nunique() == 2 else np.nan
    return pd.Series(out)

# Same markets at every k: markets that lived >= 180 days (k up to 180)
for H, ks in [(90, [1, 7, 30, 90]), (180, [1, 7, 30, 90, 180]), (365, [1, 7, 30, 90, 180, 365])]:
    ids = set(m[m.horizon_days >= H].ticker)
    sub = P[P.ticker.isin(ids) & P.k.isin(ks)]
    common = set.intersection(*[set(sub[sub.k == k].ticker) for k in ks])
    sub = sub[sub.ticker.isin(common)]
    t = sub.groupby("k").apply(score)
    print(f"\n== markets that lived >= {H} days, scored at each k (same {len(common)} markets) ==")
    print(t.round(3).to_string())
    t.to_csv(f"{R}/03_accuracy_h{H}.csv")

# by group, fixed sample H>=90
ids = set(m[m.horizon_days >= 90].ticker)
sub = P[P.ticker.isin(ids) & P.k.isin([1, 7, 30, 90])]
common = set.intersection(*[set(sub[sub.k == k].ticker) for k in [1, 7, 30, 90]])
sub = sub[sub.ticker.isin(common)]
g = sub.groupby(["group", "k"]).apply(score).reset_index()
print(g.pivot(index="k", columns="group", values="auc").round(3).to_string())
print(g.pivot(index="k", columns="group", values="skill_vs_base").round(3).to_string())
print(g.pivot(index="k", columns="group", values="markets").to_string())
g.to_csv(f"{R}/03_accuracy_by_group.csv", index=False)

# calibration at k = 90 and 30 (markets with horizon >= k)
for k in [30, 90, 180]:
    s = P[P.k == k].copy()
    s["pbin"] = pd.cut(s.p, [0, .05, .15, .3, .5, .7, .85, .95, 1], include_lowest=True)
    cal = s.groupby("pbin", observed=True).agg(n=("y", "size"), mean_p=("p", "mean"), yes_rate=("y", "mean"))
    print(f"\ncalibration k={k}"); print(cal.round(3).to_string())
    cal.to_csv(f"{R}/03_calibration_k{k}.csv")
