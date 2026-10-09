"""One worked example for the reward event study (a13): a rewarded market and its controls.

Reads the stacks of the main version (results/13_reward_event_study_price_ffill_stacks.csv) and
builds the same daily panel as a13 (same prices, same window of days -PRE..POST-1).
Candidates: rewarded markets that settled yes/no, with at least 3 settled controls, and spreads on
at least half of the days before and after the reward (for the rewarded market and its controls).
For each, the change from the days before the reward to the days after (rewarded market minus the
average of its controls) is computed for spread and Brier score. Eligible candidates also have
controls that start out alike (mean distance of the price from 50¢ within 15¢ of the rewarded
market's) and a steady spread before the reward (no week more than 3 times another). The example
is the eligible candidate whose two changes are closest to the eligible candidates' medians
(distance in standard deviations), so it is typical rather than the most striking. The Brier
changes are skewed (a few markets that started far from the outcome fall a lot), so the median
is the typical case and the mean is reported next to it.

Writes results/13_example.json: the markets, weekly means, and before/after means.
"""
import json

import numpy as np
import pandas as pd

from a13_reward_event_study import daily_panel
from common import D, R

meta = json.load(open(f"{R}/13_reward_event_study_price_ffill_sample.json"))
PRE, POST = meta["pre"], meta["post"]
st = pd.read_csv(f"{R}/13_reward_event_study_price_ffill_stacks.csv", parse_dates=["t0"])
m = pd.read_parquet(f"{D}/markets.parquet", columns=["ticker", "title", "yes_sub_title", "event_title", "series_title",
                                                     "category", "status", "result", "open_time", "close_time"])
m["y"] = m.result.map({"yes": 1.0, "no": 0.0})
m["settled"] = (m.status == "finalized") & m.y.notna()
st = st.merge(m[["ticker", "settled"]], on="ticker")
tr = st[st.treated == 1]
st = st[st.sid.isin(tr.loc[tr.settled, "sid"])]
n_settled_ctrl = st[(st.treated == 0) & st.settled].groupby("sid").size()
st = st[st.sid.isin(n_settled_ctrl[n_settled_ctrl >= 3].index) & st.settled]

c = daily_panel(m, set(st.ticker), price=meta["price"])
p = st.merge(c, on="ticker")
p["k"] = (p.day - p.t0).dt.days
p = p[(p.k >= -PRE) & (p.k < POST)].copy()
p["after"] = p.k >= 0
p["week"] = np.floor_divide(p.k, 7)

# spreads on at least half the days on each side, for the rewarded market and for the controls
days = p[p.spread.notna()].groupby(["sid", "treated", "after"]).day.nunique()
full = None
for (treated, after), n in {(1.0, False): PRE, (1.0, True): POST, (0.0, False): PRE, (0.0, True): POST}.items():
    ok = set(days.xs((treated, after), level=["treated", "after"]).loc[lambda s: s >= 0.5 * n].index)
    full = ok if full is None else full & ok
p = p[p.sid.isin(full)]


def means(y):
    """Per stack and side: the rewarded market's mean, and the mean over controls of each control's mean."""
    g = p.groupby(["sid", "treated", "after", "ticker"])[y].mean().groupby(["sid", "treated", "after"]).mean()
    return g.unstack(["treated", "after"])


out = {}
for y in ["spread", "brier"]:
    g = means(y)
    out[y] = (g[(1.0, True)] - g[(1.0, False)]) - (g[(0.0, True)] - g[(0.0, False)])
d = pd.DataFrame(out).dropna()
pre = p[~p.after].groupby(["sid", "treated", "ticker"]).p_dist.mean().groupby(["sid", "treated"]).mean().unstack("treated")
wk = p[(p.treated == 1) & ~p.after].groupby(["sid", "week"]).spread.mean().unstack()
alike = ((pre[1.0] - pre[0.0]).abs() <= 0.15).reindex(d.index, fill_value=False)
steady = (wk.max(axis=1) <= 3 * wk.min(axis=1)).reindex(d.index, fill_value=False)
e_ok = d[alike & steady]
z = ((e_ok - e_ok.median()) / e_ok.std()).abs().sum(axis=1)
sid = z.idxmin()
print(f"{len(d):,} candidates, {len(e_ok):,} eligible; eligible median change: spread {e_ok.spread.median():+.2f}¢, "
      f"brier {e_ok.brier.median():+.4f} (mean {e_ok.brier.mean():+.4f}); example sid {sid}: spread {d.loc[sid, 'spread']:+.2f}¢, brier {d.loc[sid, 'brier']:+.4f}")

e = p[p.sid == sid]
mi = m.set_index("ticker")
row = lambda tk: {"ticker": tk, "title": mi.at[tk, "title"], "sub": mi.at[tk, "yes_sub_title"],
                  "event": mi.at[tk, "event_title"], "open": mi.at[tk, "open_time"].strftime("%Y-%m-%d"),
                  "close": mi.at[tk, "close_time"].strftime("%Y-%m-%d"), "result": mi.at[tk, "result"]}
s = st[(st.sid == sid) & (st.treated == 1)].iloc[0]
ex = {"treated": {**row(s.ticker), "series": mi.at[s.ticker, "series_title"], "category": mi.at[s.ticker, "category"],
                  "t0": s.t0.strftime("%Y-%m-%d"), "reward_usd": float(s.reward_usd)},
      "controls": [row(tk) for tk in sorted(e.loc[e.treated == 0, "ticker"].unique())],
      "candidates": int(len(d)), "eligible": int(len(e_ok)), "median_change": {k: float(v) for k, v in e_ok.median().items()},
      "mean_change": {k: float(v) for k, v in e_ok.mean().items()},
      "change": {k: float(v) for k, v in d.loc[sid].items()}, "pre": PRE, "post": POST}
for y in ["spread", "brier"]:
    w = e.groupby(["treated", "week", "ticker"])[y].mean().groupby(["treated", "week"]).mean().unstack("treated")
    ex[y] = {"weeks": [int(i) for i in w.index], "rewarded": [None if np.isnan(v) else float(v) for v in w[1.0]],
             "controls": [None if np.isnan(v) else float(v) for v in w[0.0]]}
    g = means(y).loc[sid]
    ex[y]["before_after"] = {"rewarded": [float(g[(1.0, False)]), float(g[(1.0, True)])],
                             "controls": [float(g[(0.0, False)]), float(g[(0.0, True)])]}
json.dump(ex, open(f"{R}/13_example.json", "w"), indent=1, default=str)
