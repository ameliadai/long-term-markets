"""Are more liquid markets more accurate?

For settled yes/no markets priced k days before close (from a03), measure
liquidity over the 30 days up to that date and relate it to the Brier score:
  volume      contracts traded in those 30 days
  spread      median bid-ask spread (days with quotes on both sides)
  days traded share of those days with at least one trade
  open int.   contracts held at the scoring date
  reward      any liquidity reward active in those 30 days
Order-book depth is not available historically, so it is not included.

Outputs: 08_quintiles.csv (Brier by quintile of each measure, 95% CIs
bootstrapped over events), 08_reward.csv, 08_regression.csv (Brier on all
measures together, controlling for how uncertain the price was and market group).
"""
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from common import D, R

KS = [30, 7, 90]
WINDOW = pd.Timedelta(days=30)
rng = np.random.default_rng(0)

P = pd.read_parquet(f"{R}/03_prices_at_k.parquet", columns=["ticker", "day", "k", "p", "y", "group"])
P = P[P.k.isin(KS)].rename(columns={"day": "d0"})
mk = pd.read_parquet(f"{D}/markets.parquet", columns=["ticker", "event_ticker"])
P = P.merge(mk, on="ticker", how="left")
tickers = pa.array(sorted(set(P.ticker)))
t = pq.read_table(f"{D}/candles_daily.parquet",
                  columns=["ticker", "day", "volume", "spread_med", "oi_close"])
c = t.filter(pc.is_in(t.column("ticker"), value_set=tickers)).to_pandas()

ip = pd.read_parquet(f"{D}/incentive_programs.parquet",
                     columns=["market_ticker", "incentive_type", "start_date", "end_date"])
ip = ip[(ip.incentive_type == "liquidity") & ip.market_ticker.isin(set(P.ticker))]
for col in ["start_date", "end_date"]:
    ip[col] = pd.to_datetime(ip[col], format="ISO8601", utc=True)

rows = []
for k in KS:
    s = P[P.k == k]
    w = c.merge(s[["ticker", "d0"]], on="ticker")
    w = w[(w.day <= w.d0) & (w.day > w.d0 - WINDOW)]
    g = w.groupby("ticker")
    f = pd.DataFrame({"volume": g.volume.sum(), "spread": g.spread_med.median(),
                      "days_traded": g.volume.apply(lambda v: (v > 0).mean()),
                      "open_interest": w[w.day == w.d0].set_index("ticker").oi_close})
    r = ip.merge(s[["ticker", "d0"]], left_on="market_ticker", right_on="ticker")
    r = r[(r.start_date <= r.d0 + pd.Timedelta(days=1)) & (r.end_date >= r.d0 - WINDOW)]
    f["reward"] = f.index.isin(set(r.ticker))
    rows.append(s.join(f, on="ticker"))
X = pd.concat(rows, ignore_index=True)
X["brier"] = (X.p - X.y) ** 2
X["uncertainty"] = X.p * (1 - X.p)
X.to_parquet(f"{R}/08_market_features.parquet", index=False)


def boot_ci(df, reps=300):
    ev = df.groupby("event_ticker").brier.agg(["sum", "size"])
    idx = rng.integers(0, len(ev), size=(reps, len(ev)))
    s, n = ev["sum"].values, ev["size"].values
    means = s[idx].sum(1) / n[idx].sum(1)
    return np.percentile(means, [2.5, 97.5])


# Q1 = least liquid ... Q5 = most liquid (spread is reversed: tightest = most liquid);
# measures with no data in this dataset (e.g. spread and open interest for Polymarket) are skipped
MEASURES = {"volume": 1, "days_traded": 1, "open_interest": 1, "spread": -1}
MEASURES = {k: v for k, v in MEASURES.items() if X[k].notna().any()}
out = []
for k in KS:
    Xk = X[X.k == k]
    for meas, sign in MEASURES.items():
        d = Xk.dropna(subset=[meas]).copy()
        d["q"] = pd.qcut((sign * d[meas]).rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
        for q, dq in d.groupby("q"):
            lo, hi = boot_ci(dq)
            out.append({"k": k, "measure": meas, "quintile": q, "markets": len(dq),
                        "events": dq.event_ticker.nunique(), "brier": dq.brier.mean(),
                        "ci_lo": lo, "ci_hi": hi, "uncertainty": dq.uncertainty.mean(),
                        "min": dq[meas].min(), "max": dq[meas].max()})
Q = pd.DataFrame(out)
Q.to_csv(f"{R}/08_quintiles.csv", index=False)
pd.set_option("display.width", 200)
print(Q[Q.k == 30].round(4).to_string())

rw = []
for k in KS:
    for flag, d in X[X.k == k].groupby("reward"):
        lo, hi = boot_ci(d)
        rw.append({"k": k, "reward": bool(flag), "markets": len(d), "brier": d.brier.mean(),
                   "ci_lo": lo, "ci_hi": hi, "uncertainty": d.uncertainty.mean()})
RW = pd.DataFrame(rw)
RW.to_csv(f"{R}/08_reward.csv", index=False)
print(RW.round(4).to_string())


def ols_cluster(y, Xm, cl):
    Xm = np.column_stack([np.ones(len(y)), Xm])
    beta = np.linalg.lstsq(Xm, y, rcond=None)[0]
    u = y - Xm @ beta
    inv = np.linalg.pinv(Xm.T @ Xm)
    Xu = pd.DataFrame(Xm * u[:, None]).groupby(cl).sum().values
    G = len(Xu)
    V = inv @ (Xu.T @ Xu) @ inv * G / (G - 1)
    return beta[1:], np.sqrt(np.diag(V))[1:]


reg = []
for k in KS:
    d = X[X.k == k].dropna(subset=["open_interest"] if "open_interest" in MEASURES else []).copy()
    d["log_volume"] = np.log1p(d.volume)
    z = ["log_volume", "days_traded"]
    if "open_interest" in MEASURES:
        d["log_open_interest"] = np.log1p(d.open_interest.clip(lower=0))
        z.append("log_open_interest")
    if "spread" in MEASURES:
        d["no_quotes"] = d.spread.isna().astype(float)
        d["spread"] = d.spread.fillna(d.spread.median())
        z.insert(1, "spread")
    for col in z:  # per 1 standard deviation
        d[col] = (d[col] - d[col].mean()) / d[col].std()
    groups = pd.get_dummies(d.group, drop_first=True, dtype=float)
    cols = z + (["reward"] if d.reward.any() else []) + (["no_quotes"] if "spread" in MEASURES else []) + ["uncertainty"]
    Xm = pd.concat([d[cols].astype(float), groups], axis=1).values
    b, se = ols_cluster(d.brier.values, Xm, d.event_ticker.values)
    for name, bb, ss in zip(cols, b, se):
        reg.append({"k": k, "term": name, "coef": bb, "se": ss, "t": bb / ss,
                    "markets": len(d), "mean_brier": d.brier.mean()})
REG = pd.DataFrame(reg)
REG.to_csv(f"{R}/08_regression.csv", index=False)
print(REG.round(4).to_string())

# ---- equally sure markets: within bands of how far the price was from 50¢,
# compare the more liquid half with the less liquid half (k = 30)
BANDS = [(0, .1, "40–60¢"), (.1, .3, "20–40¢ or 60–80¢"), (.3, .45, "5–20¢ or 80–95¢"), (.45, .51, "0–5¢ or 95–100¢")]
d = X[X.k == 30].copy()
d["dist"] = (d.p - 0.5).abs()
eq = []
for lo_d, hi_d, band in BANDS:
    b = d[(d.dist >= lo_d) & (d.dist < hi_d)]
    for meas, sign in MEASURES.items():
        bb = b.dropna(subset=[meas])
        liquid = (sign * bb[meas]) > (sign * bb[meas]).median()
        for half, part in [("less liquid half", bb[~liquid]), ("more liquid half", bb[liquid])]:
            lo, hi = boot_ci(part)
            eq.append({"band": band, "measure": meas, "half": half, "markets": len(part),
                       "brier": part.brier.mean(), "ci_lo": lo, "ci_hi": hi})
EQ = pd.DataFrame(eq)
EQ.to_csv(f"{R}/08_equal_sure.csv", index=False)
print(EQ.pivot_table(index=["measure", "band"], columns="half", values="brier").round(4).to_string())

# significance of (less liquid - more liquid) Brier within each band: bootstrap over events
sig = []
for lo_d, hi_d, band in BANDS:
    b = d[(d.dist >= lo_d) & (d.dist < hi_d)]
    for meas, sign in MEASURES.items():
        bb = b.dropna(subset=[meas]).copy()
        bb["liquid"] = (sign * bb[meas]) > (sign * bb[meas]).median()
        ev = bb.groupby(["event_ticker", "liquid"]).brier.agg(["sum", "size"]).unstack(fill_value=0)
        s_i, n_i = ev[("sum", False)].values, ev[("size", False)].values
        s_l, n_l = ev[("sum", True)].values, ev[("size", True)].values
        idx = rng.integers(0, len(ev), size=(2000, len(ev)))
        diff = s_i[idx].sum(1) / n_i[idx].sum(1) - s_l[idx].sum(1) / n_l[idx].sum(1)
        point = s_i.sum() / n_i.sum() - s_l.sum() / n_l.sum()
        p = min(1.0, 2 * min((diff <= 0).mean(), (diff >= 0).mean()))
        sig.append({"band": band, "measure": meas, "diff_less_minus_more": point,
                    "ci_lo": np.percentile(diff, 2.5), "ci_hi": np.percentile(diff, 97.5), "p": p})
SIG = pd.DataFrame(sig)
SIG.to_csv(f"{R}/08_equal_sure_sig.csv", index=False)
print(SIG.round(4).to_string())

# how sure prices were in each liquidity group (k = 30): share priced 0–5¢ or 95–100¢
near = []
for meas, sign in MEASURES.items():
    dd = d.dropna(subset=[meas]).copy()
    dd["q"] = pd.qcut((sign * dd[meas]).rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    for q, dq in dd.groupby("q"):
        near.append({"measure": meas, "quintile": q, "markets": len(dq),
                     "share_0_5_or_95_100": ((dq.p <= .05) | (dq.p >= .95)).mean(),
                     "share_0_20_or_80_100": ((dq.p <= .2) | (dq.p >= .8)).mean()})
pd.DataFrame(near).to_csv(f"{R}/08_near_certain.csv", index=False)

# ---- one view: Brier by price bin for the more vs less liquid half (global median split), k = 30
EDGES = np.linspace(0, 1, 11)
pb = []
for meas, sign in MEASURES.items():
    dd = d.dropna(subset=[meas]).copy()
    dd["liquid"] = (sign * dd[meas]) > (sign * dd[meas]).median()
    dd["bin"] = pd.cut(dd.p, EDGES, include_lowest=True, labels=False)
    for b, db in dd.groupby("bin"):
        ev = db.groupby(["event_ticker", "liquid"]).brier.agg(["sum", "size"]).unstack(fill_value=0)
        row = {"measure": meas, "bin": int(b), "lo": EDGES[b], "hi": EDGES[b + 1]}
        for flag, name in [(False, "less"), (True, "more")]:
            part = db[db.liquid == flag]
            row[f"n_{name}"] = len(part)
            row[f"share_{name}"] = len(part) / (dd.liquid == flag).sum()
            row[f"brier_{name}"] = part.brier.mean() if len(part) else np.nan
        if ("size", False) in ev and ("size", True) in ev and row["n_less"] and row["n_more"]:
            s_i, n_i = ev[("sum", False)].values, ev[("size", False)].values
            s_l, n_l = ev[("sum", True)].values, ev[("size", True)].values
            idx = rng.integers(0, len(ev), size=(2000, len(ev)))
            with np.errstate(invalid="ignore", divide="ignore"):
                diff = s_i[idx].sum(1) / n_i[idx].sum(1) - s_l[idx].sum(1) / n_l[idx].sum(1)
            diff = diff[np.isfinite(diff)]
            row["p"] = min(1.0, 2 * min((diff <= 0).mean(), (diff >= 0).mean()))
        else:
            row["p"] = np.nan
        pb.append(row)
PB = pd.DataFrame(pb)
PB.to_csv(f"{R}/08_price_bins.csv", index=False)
print(PB[PB.measure == "spread"].round(4).to_string())
