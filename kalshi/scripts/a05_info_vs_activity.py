"""Do reward days bring information, or just activity?

For markets in the reward panel that have since settled yes/no, measure how
much each day's price move closed the gap to the eventual outcome:
    info_gain_t = (p_{t-1} - y)^2 - (p_t - y)^2
Positive = the price moved toward the truth that day. Compare reward-active
days with other days in the same market (market + day FE), next to the
activity outcomes from a04.

Also: realized return from buying favourites/longshots k days out, a rough
check on whether long-dated prices carry a capital-lockup discount.
"""
import numpy as np, pandas as pd
from common import D, R, markets
from a04_twfe import twfe

p = pd.read_parquet(f"{R}/04_panel.parquet")
m = markets()
res_ = m.set_index("ticker").loc[:, ["status", "result"]]
p = p.join(res_, on="ticker")
p = p[(p.status == "finalized") & p.result.isin(["yes", "no"])].copy()
p["y"] = (p.result == "yes").astype(float)
two = (p.bid_close > 0) & (p.ask_close < 1) & (p.ask_close > p.bid_close)
p["prob"] = np.where(two, (p.bid_close + p.ask_close) / 2, p.price_close)
p = p.sort_values(["ticker", "day"])
p["prob"] = p.groupby("ticker").prob.ffill()
p["prev"] = p.groupby("ticker").prob.shift()
p = p.dropna(subset=["prob", "prev"])
p["info_gain"] = (p.prev - p.y) ** 2 - (p.prob - p.y) ** 2
p["abs_move"] = (p.prob - p.prev).abs()
p["moved"] = (p.abs_move > 0.005).astype(float)
dtc_d = pd.get_dummies(p.dtc_bin, prefix="dtc", drop_first=True, dtype=float)
p = pd.concat([p, dtc_d], axis=1)
xs = ["rw_long_dated", "rw_liquidity"] + list(dtc_d.columns)
print(f"settled panel: {p.ticker.nunique()} markets, {len(p)} market-days")
pd.Series({"markets": p.ticker.nunique(), "market_days": len(p)}).to_json(f"{R}/05_sample.json")
out = []
for y in ["traded", "log_volume", "abs_move", "moved", "info_gain"]:
    out.append(twfe(p, y, xs).loc[["rw_long_dated", "rw_liquidity"]])
out = pd.concat(out).reset_index().rename(columns={"index": "reward"})
out["pct_of_mean"] = out.coef / out.mean_y
print(out.round(5).to_string())
out.to_csv(f"{R}/05_info_vs_activity_twfe.csv", index=False)

# ---- favourite / longshot returns by distance to resolution
P = pd.read_parquet(f"{R}/03_prices_at_k.parquet")
P["event"] = P.ticker.map(m.set_index("ticker").event_ticker)
rows = []
for k, s in P.groupby("k"):
    for name, sel in [("favourite p>=0.80", s.p >= 0.8), ("longshot p<=0.20", s.p <= 0.2),
                      ("middle", (s.p > 0.2) & (s.p < 0.8))]:
        d = s[sel]
        if len(d) < 30:
            continue
        # buy YES on favourites, buy NO on longshots: return per dollar held to resolution
        if name.startswith("favourite"):
            ret = d.y / d.p - 1
        elif name.startswith("longshot"):
            ret = (1 - d.y) / (1 - d.p) - 1
        else:
            ret = pd.Series(np.nan, index=d.index)
        ev = ret.groupby(d.event).mean()  # events weigh equally
        boot = [ev.sample(len(ev), replace=True, random_state=i).mean() for i in range(500)]
        rows.append({"k": k, "bucket": name, "markets": len(d), "events": len(ev),
                     "mean_price": d.p.mean(), "yes_rate": d.y.mean(),
                     "return_to_resolution": ev.mean(),
                     "ci_lo": np.percentile(boot, 2.5), "ci_hi": np.percentile(boot, 97.5),
                     "annualized": (1 + ev.mean()) ** (365 / max(k, 1)) - 1})
fl = pd.DataFrame(rows)
print(fl.round(3).to_string())
fl.to_csv(f"{R}/05_favourite_longshot_returns.csv", index=False)
