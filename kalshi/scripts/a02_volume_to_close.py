"""How much long markets trade at each distance from resolution, by how long they were open.

Sample: markets open at least 90 days that settled yes/no, traded at least once, and have price
history (the last row of the Horizons tab's long-market table).
They are split by duration (open 3-6 months, 6-12 months, over a year), since a market can only
trade in windows it was open for. For each group and window of days before close
(> 1 year, 6-12 months, ..., final day):
  markets          markets in the group
  markets_open     markets with at least one day in that window
  avg_volume       volume traded in that window per market, averaged over the group
                   (a market not yet open counts as 0, so the windows add up to the group's
                   average lifetime volume)
  share_of_volume  share of each market's lifetime volume traded in that window, averaged over
                   the group (adds up to 100% across windows)
  avg_volume_wc    the part of avg_volume from markets about the 2026 World Cup (title mentions
                   "World Cup"), which dominate trading among the longest markets
  wc_markets       World Cup markets in the group
Windows have different lengths, so these are totals per window, not per day.

Writes results/02_volume_to_close.csv.
"""
import numpy as np
import pandas as pd

from common import R, candles_for, markets

BINS = [0, 1, 7, 30, 90, 180, 365, np.inf]
LABELS = ["0-1d", "1-7d", "7-30d", "30-90d", "90-180d", "180-365d", ">365d"]
GROUPS = [(90, 180, "3-6m"), (180, 365, "6-12m"), (365, np.inf, ">1y")]

m = markets(min_horizon=90)
m = m[(m.status == "finalized") & (m.volume > 0)]
m["wc"] = m.title.str.contains("World Cup", case=False, na=False)
c = candles_for(m.ticker)[["ticker", "day", "volume"]].merge(m[["ticker", "close_time", "horizon_days", "wc"]], on="ticker")
c["dtc"] = (c.close_time - c.day).dt.total_seconds() / 86400
c = c[c.dtc >= 0]
c["dtc_bin"] = pd.cut(c.dtc, BINS, labels=LABELS, right=False)
life = c.groupby("ticker").volume.sum()
c = c[c.ticker.isin(life[life > 0].index)]

rows = []
for lo, hi, name in GROUPS:
    d = c[(c.horizon_days >= lo) & (c.horizon_days < hi)]
    n = d.ticker.nunique()
    per = d.groupby(["ticker", "dtc_bin"], observed=True).agg(volume=("volume", "sum"), wc=("wc", "first")).reset_index()
    per["share"] = per.volume / per.ticker.map(life)
    per["volume_wc"] = per.volume.where(per.wc, 0)
    g = per.groupby("dtc_bin", observed=True)
    out = pd.DataFrame({"markets_open": g.ticker.nunique(), "avg_volume": g.volume.sum() / n,
                        "avg_volume_wc": g.volume_wc.sum() / n,
                        "share_of_volume": g.share.sum() / n}).reindex(LABELS[::-1]).fillna(0)
    out["markets"] = n
    out["wc_markets"] = d.loc[d.wc, "ticker"].nunique()
    out["group"] = name
    rows.append(out.rename_axis("dtc_bin").reset_index())
out = pd.concat(rows, ignore_index=True)
print(out.round(4).to_string())
out.to_csv(f"{R}/02_volume_to_close.csv", index=False)
