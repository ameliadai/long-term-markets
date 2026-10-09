"""Do liquidity rewards change market quality and accuracy? Stacked event study on Kalshi.

Treated: markets whose first reward program is a liquidity reward (no volume program starting
at the same moment), starting between START and DATA_END - 7 days, at least MIN_HISTORY days
after the market was listed and at least 7 days before it closes. Day 0 = the first reward day.
Programs only exist from Sep 2025, so for markets listed earlier "first" means first observed.
Controls: markets in the same series with no reward program of any kind (clean controls) that
have candle rows at least 3 days before and 3 days after day 0.
For each treated market a "stack" holds its days in [-PRE, +POST) around day 0 and the same
calendar days of up to N_CTRL controls. Each market's last day is dropped (the price there
usually already shows the outcome).

Daily panel: every calendar day from the day a market was listed to the day before it closed.
Days without a candle row had no trade (trade days almost always have a row), so they count as
traded = 0 and volume 0; spread and two-sided quotes are unknown on those days.

For every outcome, with fixed effects for market within stack and for day within stack, and
standard errors clustered by series:
  event weeks  y = sum_w delta_w * 1[treated, week w] + FE      (week -1 is the reference)
  post         y = delta * 1[treated, day >= 0] + FE            (baseline: all days before 0)
  post_ex_w-1  as post, plus a dummy for the treated market's week -1, so the baseline is
               weeks -PRE/7 .. -2 only
Outcomes (all markets): spread (median bid-ask spread that day, cents; days with two-sided
quotes), two_sided (share of the day's hourly snapshots with quotes on both sides), traded (any
trade that day), log_volume. Settled yes/no markets only: brier ((price - outcome)^2), info_gain
(how much the day's price move closed the gap to the outcome).
Subsamples: all; markets with more than 180 days left at day 0; long-dated program only.

Options for the control group:
  --controls series   never-rewarded markets in the same series (default)
  --controls event    never-rewarded markets in the same event (same question, other strikes)
  --match volume      among eligible controls, the N_CTRL closest to the treated market in mean
                      log volume over days -PRE..-8 (instead of a random draw)
  --match price       ... closest in mean distance of the price from 50¢ over days -PRE..-8, so
                      treated and controls are about equally uncertain
  --match brier       ... closest in mean Brier score over days -PRE..-8 (settled markets only)
Other options:
  --price ffill       price = midpoint when quotes are two-sided, else the day's last trade, carried
                      forward over days without either; every day from the first price on is then
                      scored (default: midpoint, on two-sided days only)
  --pre DAYS          length of the pre-period (default 28)
  --placebo           fake treatment: never-rewarded markets get a made-up "first reward day" drawn
                      from the real ones in their series, and are compared with the other
                      never-rewarded markets; real effects should vanish
  --min-pre-brier X   keep only stacks whose treated market had mean Brier >= X over days -PRE..-8
                      (settled markets that started out uncertain). With --placebo this tests
                      whether uncertain markets' Brier falls relative to their controls anyway

Writes results/13_reward_event_study[_TAG].csv, ..._sample.json (sample sizes, settings, reward
dollars) and ..._stacks.csv (which markets form each stack, with the treated market's liquidity
reward dollars from programs starting in its first POST days).
usage: python a13_reward_event_study.py [--controls series|event] [--match none|volume|price|brier]
                                        [--price mid|ffill] [--pre DAYS] [--placebo] [--min-pre-brier X]
                                        [--limit N] [--tag TAG]
"""
import argparse
import json

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

from common import D, R, keep

PRE, POST, MIN_HISTORY = 28, 56, 14
N_CTRL = 10
START, DATA_END = pd.Timestamp("2025-10-01", tz="UTC"), pd.Timestamp("2026-09-21", tz="UTC")
REF = -1
OUTCOMES = ["spread", "two_sided", "traded", "log_volume", "brier", "info_gain"]


def log(*a):
    print(*a, flush=True)


def fe_ols(df, y, xs, fes, cluster, tol=1e-8, max_iter=500):
    """OLS of y on xs absorbing the fixed effects in fes; SEs clustered by `cluster`."""
    Z = df[[y] + xs].to_numpy(np.float64).copy()
    groups = [pd.factorize(df[f])[0] for f in fes]
    counts = [np.bincount(g) for g in groups]
    for _ in range(max_iter):
        prev = Z.copy()
        for g, n in zip(groups, counts):
            for j in range(Z.shape[1]):
                Z[:, j] -= (np.bincount(g, weights=Z[:, j]) / n)[g]
        if np.abs(Z - prev).max() < tol:
            break
    else:
        log(f"  warning: demeaning for {y} did not converge in {max_iter} iterations")
    Y, X = Z[:, 0], Z[:, 1:]
    A = np.linalg.pinv(X.T @ X)
    b = A @ X.T @ Y
    u = Y - X @ b
    cl = pd.factorize(df[cluster])[0]
    S = np.column_stack([np.bincount(cl, weights=X[:, j] * u) for j in range(X.shape[1])])
    G = S.shape[0]
    V = A @ (S.T @ S) @ A * G / (G - 1)
    return b, np.sqrt(np.diag(V)), G


def daily_panel(m, tickers, price="mid"):
    """One row per market per calendar day from listing to the day before close (see docstring).

    m: markets with ticker, open_time, close_time, y, settled. Returns ticker, day, has_row (a
    candle row exists), price p, p_dist and the outcomes.
    """
    c = pq.read_table(f"{D}/candles_daily.parquet", columns=[
        "ticker", "day", "volume", "price_close", "bid_close", "ask_close", "spread_med", "two_sided_share"])
    c = c.filter(pc.is_in(c.column("ticker"), value_set=pa.array(sorted(tickers)))).to_pandas()
    mm = m[m.ticker.isin(c.ticker.unique())].copy()
    mm["first"] = mm.open_time.dt.floor("D").clip(lower=c.day.min())
    mm["last"] = (mm.close_time.dt.floor("D") - pd.Timedelta(days=1)).clip(upper=DATA_END)
    mm = mm[mm["last"] >= mm["first"]]
    n = ((mm["last"] - mm["first"]).dt.days + 1).to_numpy()
    cal = pd.DataFrame({"ticker": np.repeat(mm.ticker.to_numpy(), n)})
    cal["day"] = pd.DatetimeIndex(mm["first"]).repeat(n) + pd.to_timedelta(np.concatenate([np.arange(k) for k in n]), unit="D")
    c = cal.merge(c, on=["ticker", "day"], how="left", indicator=True)
    c["has_row"] = c.pop("_merge") == "both"
    c = c.merge(mm[["ticker", "y", "settled"]], on="ticker").sort_values(["ticker", "day"], ignore_index=True)
    c["volume"] = c.volume.fillna(0)
    two = (c.bid_close > 0) & (c.ask_close < 1) & (c.ask_close > c.bid_close)
    c["p"] = np.where(two, (c.bid_close + c.ask_close) / 2, np.nan)
    if price == "ffill":
        c["p"] = c.p.fillna(c.price_close)
        c["p"] = c.groupby("ticker").p.ffill()
    c["spread"] = np.where(c.two_sided_share > 0, c.spread_med * 100, np.nan)
    c["two_sided"] = c.two_sided_share
    c["traded"] = (c.volume > 0).astype(float)
    c["log_volume"] = np.log1p(c.volume)
    c["brier"] = np.where(c.settled, (c.p - c.y) ** 2, np.nan)
    prev_p = c.groupby("ticker").p.shift()
    c["info_gain"] = np.where(c.settled, (prev_p - c.y) ** 2 - (c.p - c.y) ** 2, np.nan)
    c["p_dist"] = (c.p - 0.5).abs()
    return c[["ticker", "day", "has_row", "p", "p_dist"] + OUTCOMES]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--controls", choices=["series", "event"], default="series")
    ap.add_argument("--match", choices=["none", "volume", "price", "brier"], default="none")
    ap.add_argument("--tag", default="")
    ap.add_argument("--price", choices=["mid", "ffill"], default="mid")
    ap.add_argument("--pre", type=int, default=PRE)
    ap.add_argument("--placebo", action="store_true")
    ap.add_argument("--min-pre-brier", type=float, default=None)
    a = ap.parse_args()
    pre = a.pre
    weeks = list(range(-pre // 7, POST // 7))          # -4 .. 7 by default
    rng = np.random.default_rng(0)

    m = keep(pd.read_parquet(f"{D}/markets.parquet", columns=[
        "ticker", "series_ticker", "event_ticker", "category", "status", "result", "open_time", "close_time"]))
    m = m[m.series_ticker.notna() & m.open_time.notna() & m.close_time.notna()]
    m["y"] = np.where(m.result == "yes", 1.0, np.where(m.result == "no", 0.0, np.nan))
    m["settled"] = (m.status == "finalized") & m.y.notna()

    ip = pd.read_parquet(f"{D}/incentive_programs.parquet",
                         columns=["market_ticker", "incentive_type", "incentive_description", "start_date", "period_reward"])
    ip["start"] = pd.to_datetime(ip.start_date, format="ISO8601", utc=True)
    rewarded = set(ip.market_ticker)
    # each market's earliest program start; treated only if every program starting then is a liquidity reward
    ip["t_first"] = ip.groupby("market_ticker").start.transform("min")
    at_first = ip[ip.start == ip.t_first].groupby("market_ticker").agg(
        all_liq=("incentive_type", lambda s: (s == "liquidity").all()),
        long_dated=("incentive_description", lambda s: (s == "long_dated").any()), start=("start", "first"))
    t = at_first[at_first.all_liq].rename_axis("ticker").reset_index()
    t["t0"] = t.start.dt.floor("D")
    t["kind"] = np.where(t.long_dated, "long_dated", "other")
    t = t.merge(m, on="ticker")
    t = t[(t.t0 >= START) & (t.t0 <= DATA_END - pd.Timedelta(days=7))
          & (t.t0 - t.open_time >= pd.Timedelta(days=MIN_HISTORY))
          & (t.close_time - t.t0 >= pd.Timedelta(days=7))]
    ctrl = m[~m.ticker.isin(rewarded)]
    t = t[t.series_ticker.isin(set(ctrl.series_ticker))]
    if a.placebo:
        fake = []
        t0s = t.groupby("series_ticker").t0.apply(list)
        for s_, cands in ctrl[ctrl.series_ticker.isin(t0s.index)].groupby("series_ticker"):
            cands = cands.assign(t0=rng.choice(t0s[s_], len(cands)))
            ok = (cands.t0 - cands.open_time >= pd.Timedelta(days=MIN_HISTORY)) & (cands.close_time - cands.t0 >= pd.Timedelta(days=7))
            fake.append(cands[ok])
        t = pd.concat(fake, ignore_index=True).assign(kind="placebo")
        t = t.sample(min(len(t), 2000), random_state=0)
    if a.limit:
        t = t.sample(min(a.limit, len(t)), random_state=0)
    t = t.sort_values(["t0", "ticker"], ignore_index=True)
    log(f"treated candidates: {len(t):,} markets in {t.series_ticker.nunique():,} series; "
        f"never-rewarded markets in those series: {ctrl.series_ticker.isin(set(t.series_ticker)).sum():,}")

    ctrl = ctrl[ctrl.series_ticker.isin(set(t.series_ticker))]
    c = daily_panel(m, set(t.ticker) | set(ctrl.ticker), a.price)
    log(f"panel days: {len(c):,} market-days for {c.ticker.nunique():,} markets ({c.has_row.mean():.0%} with a candle row)")

    # controls need candle rows on both sides of day 0: first and last row day per control
    span = c[c.has_row].groupby("ticker").day.agg(["min", "max"])
    ctrl = ctrl.join(span, on="ticker", how="inner").sort_values("ticker")
    key = "series_ticker" if a.controls == "series" else "event_ticker"
    by_key = {s: d for s, d in ctrl.groupby(key)}
    if a.match != "none":
        col = {"volume": "log_volume", "price": "p_dist", "brier": "brier"}[a.match]
        series_of = {tk: d.set_index("day")[col] for tk, d in c.groupby("ticker")}

        def pre_mean(tk, t0):
            s = series_of[tk]
            return s[(s.index >= t0 - pd.Timedelta(days=pre)) & (s.index <= t0 - pd.Timedelta(days=8))].mean()
    stacks = []
    for sid, r in enumerate(t.itertuples(index=False)):
        cand = by_key.get(getattr(r, key))
        if cand is None:
            continue
        ok = cand[(cand["min"] <= r.t0 - pd.Timedelta(days=3)) & (cand["max"] >= r.t0 + pd.Timedelta(days=3))]
        pick = ok.ticker.to_numpy()
        pick = pick[pick != r.ticker]
        if len(pick) == 0:
            continue
        if a.match != "none":
            if r.ticker not in series_of:
                continue
            target = pre_mean(r.ticker, r.t0)
            if np.isnan(target):
                continue
            gap = np.array([abs(pre_mean(tk, r.t0) - target) for tk in pick])
            keep_idx = np.where(~np.isnan(gap))[0]
            pick = pick[keep_idx[np.argsort(gap[keep_idx], kind="stable")][:N_CTRL]]
            if len(pick) == 0:
                continue
        elif len(pick) > N_CTRL:
            pick = rng.choice(pick, N_CTRL, replace=False)
        stacks.append(pd.DataFrame({"sid": sid, "ticker": np.concatenate([[r.ticker], pick]),
                                    "treated": [1.0] + [0.0] * len(pick), "t0": r.t0, "series": r.series_ticker,
                                    "kind": r.kind, "days_left": (r.close_time - r.t0).days}))
    st = pd.concat(stacks, ignore_index=True)
    # liquidity reward dollars from programs that start in the treated market's first POST days
    tr0 = st.loc[st.treated == 1, ["ticker", "t0"]].drop_duplicates("ticker")
    lq = ip[ip.incentive_type == "liquidity"].merge(tr0, left_on="market_ticker", right_on="ticker")
    lq = lq[(lq.start >= lq.t0) & (lq.start < lq.t0 + pd.Timedelta(days=POST))]
    usd = (lq.groupby("ticker").period_reward.sum() / 1e4).reindex(tr0.ticker).fillna(0)
    log(f"stacks: {st.sid.nunique():,} treated markets, {int((st.treated == 0).sum()):,} control slots "
        f"({st.loc[st.treated == 0, 'ticker'].nunique():,} distinct control markets)")
    suffix = f"_{a.tag}" if a.tag else ""
    st.assign(reward_usd=st.ticker.map(usd).where(st.treated == 1)).to_csv(f"{R}/13_reward_event_study{suffix}_stacks.csv", index=False)

    p = st.merge(c, on="ticker")
    p["k"] = (p.day - p.t0).dt.days
    p = p[(p.k >= -pre) & (p.k < POST)].copy()
    p["week"] = np.floor_divide(p.k, 7)
    p["post"] = p.treated * (p.k >= 0)
    for w in weeks:
        if w != REF:
            p[f"w{w}"] = p.treated * (p.week == w)
    p["ref_week"] = p.treated * (p.week == REF)
    p["stack_mkt"] = p.sid.astype(str) + "|" + p.ticker
    p["stack_day"] = p.sid.astype(str) + "|" + p.day.dt.strftime("%Y-%m-%d")
    if a.min_pre_brier is not None:
        pb = p[(p.treated == 1) & (p.k <= -8)].groupby("sid").brier.mean()
        p = p[p.sid.isin(pb[pb >= a.min_pre_brier].index)]
        log(f"kept {p.sid.nunique():,} stacks whose treated market had mean Brier >= {a.min_pre_brier} over days -{pre}..-8")
    log(f"stacked panel: {len(p):,} rows")

    samples = {"all": p, "> 180 days left": p[p.days_left > 180], "long-dated program": p[p.kind == "long_dated"]}
    rows, meta = [], {}
    wcols = [f"w{w}" for w in weeks if w != REF]
    n_pre = sum(1 for w in weeks if w < REF)
    for sname, d0 in samples.items():
        for y in OUTCOMES:
            d = d0.dropna(subset=[y])
            # keep stacks that still have the treated market on both sides of day 0 and a control
            tr = d[d.treated == 1]
            good = set(tr.loc[tr.k < 0, "sid"]) & set(tr.loc[tr.k >= 0, "sid"]) & set(d.loc[d.treated == 0, "sid"])
            d = d[d.sid.isin(good)]
            if d.sid.nunique() < 30:
                rows.append({"sample": sname, "outcome": y, "term": "post", "note": "too few stacks", "stacks": d.sid.nunique()})
                continue
            base = {"sample": sname, "outcome": y, "n": len(d), "stacks": d.sid.nunique(),
                    "control_markets": d.loc[d.treated == 0, "ticker"].nunique(), "series": d.series.nunique(),
                    "mean_treated_pre": d.loc[(d.treated == 1) & (d.k < 0), y].mean(),
                    "mean_control_pre": d.loc[(d.treated == 0) & (d.k < 0), y].mean()}
            b, se, G = fe_ols(d, y, ["post"], ["stack_mkt", "stack_day"], "series")
            rows.append({**base, "term": "post", "coef": b[0], "se": se[0], "t": b[0] / se[0], "clusters": G})
            b, se, G = fe_ols(d, y, ["post", "ref_week"], ["stack_mkt", "stack_day"], "series")
            rows.append({**base, "term": "post_ex_w-1", "coef": b[0], "se": se[0], "t": b[0] / se[0], "clusters": G})
            b, se, G = fe_ols(d, y, wcols, ["stack_mkt", "stack_day"], "series")
            for wc, bb, ss in zip(wcols, b, se):
                rows.append({**base, "term": wc, "coef": bb, "se": ss, "t": bb / ss, "clusters": G})
            wk = rows[-len(wcols):]
            log(f"{sname:<20} {y:<11} stacks={base['stacks']:>6,} n={len(d):>10,}  post: {rows[-len(wcols) - 2]['coef']:+.5f} "
                f"(t={rows[-len(wcols) - 2]['t']:+.1f})  pre weeks: " + " ".join(f"{r['coef']:+.4f}" for r in wk[:n_pre])
                + "  post weeks: " + " ".join(f"{r['coef']:+.4f}" for r in wk[n_pre:]))
            if sname == "all" and y == "brier":
                u = usd.reindex(d.loc[d.treated == 1, "ticker"].unique())
                meta["reward_usd_settled"] = {"markets": int(len(u)), "mean": float(u.mean()), "median": float(u.median())}
        meta[sname] = {"stacks": int(d0.sid.nunique()), "rows": int(len(d0))}
    out = pd.DataFrame(rows)
    out.to_csv(f"{R}/13_reward_event_study{suffix}.csv", index=False)
    meta.update({"treated_candidates": int(len(t)), "reward_usd_mean": float(usd.mean()), "reward_usd_median": float(usd.median()),
                 "pre": pre, "post": POST, "min_history": MIN_HISTORY, "n_ctrl": N_CTRL, "limit": a.limit,
                 "controls": a.controls, "match": a.match, "price": a.price, "placebo": a.placebo,
                 "min_pre_brier": a.min_pre_brier})
    json.dump(meta, open(f"{R}/13_reward_event_study{suffix}_sample.json", "w"), indent=1)
    log("done")


if __name__ == "__main__":
    main()
