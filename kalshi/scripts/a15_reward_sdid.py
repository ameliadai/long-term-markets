"""Synthetic difference-in-differences (Arkhangelsky et al. 2021) for the reward event study (a13).

Same pool of treated markets, daily panel and prices as a13 (--price ffill; every calendar day, last
day dropped), on weekly means over weeks -PRE/7 .. 7. Each treated market is its own comparison (as
in a13's stacks), with these donors: every never-rewarded market in its series with candle rows at
least 3 days before and after day 0 (no cap, no matching). The treated market and each donor need a
value in every week, so only treated markets observed through week 7 (at least 8 weeks left, and a
quote in every week for spreads) are used: a subset of a13's. For each treated market:
  unit weights   w (>= 0, sum 1) and w0 minimise
                 sum over pre weeks t of (w0 + sum_i w_i Y_i,t - Y_T,t)^2 + zeta^2 * T_pre * |w|^2,
                 zeta = T_post^(1/4) * sigma, sigma = sd of the donors' week-to-week changes before day 0
                 (the intercept means the donors match the treated path up to a constant)
  time weights   l (>= 0, sum 1) and l0 minimise
                 sum over donors i of (l0 + sum_t l_t Y_i,t - mean of Y_i after day 0)^2 + tiny ridge;
                 equal weights when they are not identified (one donor, or donors whose pre-period
                 paths differ only by a constant, up to 0.1% of the treated market's range)
  effect in week w = (Y_T,w - sum_t l_t Y_T,t) - sum_i w_i (Y_i,w - sum_t l_t Y_i,t)
  effect after = the mean of the post weeks' effects
Effects are averaged over treated markets (also reported: their median, and plain DiD with equal
weights on the same markets); standard errors from a bootstrap over series. The pre-week "effects"
are fit residuals, not a pre-trend test. Weights are found with Frank-Wolfe on the simplex, as in
the synthdid R package (differences: sigma uses ddof 0; no sparsify step).

Options: --pre DAYS (default 28), --placebo (fake reward dates, as in a13), --min-pre-brier X
(treated markets whose mean Brier over days -PRE..-8 is at least X), --limit N, --boot B, --tag TAG.
Writes results/15_reward_sdid[_TAG].csv (outcome, term: post, post_median, did_same_sample, w-4..w7;
coef, se, t, stacks, series, donors and eff_donors = mean 1 / sum w_i^2 per treated market) and
results/15_reward_sdid[_TAG]_markets.csv (one row per treated market and outcome).
"""
import argparse
import warnings

import numpy as np
import pandas as pd

from a13_reward_event_study import POST, PRE, design, log
from common import R

OUTCOMES = ["spread", "traded", "brier"]
N_POST = POST // 7


def simplex_ls(A, b, eta, tol, iters=10000):
    """min |A w - b|^2 + eta |w|^2 over w >= 0, sum(w) = 1 (Frank-Wolfe with exact line search).

    Stops when a step lowers the objective by less than tol."""
    n = A.shape[1]
    w = np.full(n, 1.0 / n)
    r = A @ w - b
    for _ in range(iters):
        g = A.T @ r + eta * w
        i = int(np.argmin(g))
        d = -w
        d[i] += 1.0
        Ad = A[:, i] - A @ w
        quad = Ad @ Ad + eta * (d @ d)
        if quad <= 0:
            break
        lin = r @ Ad + eta * (w @ d)
        step = min(max(-lin / quad, 0.0), 1.0)
        if -(2 * step * lin + step ** 2 * quad) < tol:
            break
        w = w + step * d
        r = r + step * Ad
    return w


def sdid_one(yt, yd, n_pre):
    """yt: treated weekly series (T,); yd: donors (N, T). Returns the weekly effects and unit weights."""
    pre, post = slice(0, n_pre), slice(n_pre, None)
    diffs = np.diff(yd[:, pre], axis=1)
    sigma = diffs.std() if diffs.size > 1 else 0.0
    zeta = N_POST ** 0.25 * sigma
    tol = max((1e-5 * sigma) ** 2, 1e-20)
    # unit weights: match the treated pre-period path up to a constant (centre over weeks)
    A = (yd[:, pre] - yd[:, pre].mean(axis=1, keepdims=True)).T          # weeks x donors
    b = yt[pre] - yt[pre].mean()
    w = simplex_ls(A, b, zeta ** 2 * n_pre, tol) if len(yd) > 1 else np.ones(1)
    # time weights: pre weeks that best predict the donors' post-period mean (centre over donors)
    A = yd[:, pre] - yd[:, pre].mean(axis=0, keepdims=True)              # donors x weeks
    b = yd[:, post].mean(axis=1) - yd[:, post].mean()
    # not identified when the donors' pre-period paths are (almost) flat apart from their level
    flat = np.abs(A - A.mean(axis=1, keepdims=True)).max() < 1e-3 * max(np.ptp(yt), 1e-12)
    lam = np.full(n_pre, 1 / n_pre) if len(yd) == 1 or flat else simplex_ls(A, b, (1e-6 * sigma) ** 2 * len(yd), tol)
    base_t, base_d = yt[pre] @ lam, yd[:, pre] @ lam
    eff = (yt - base_t) - w @ (yd - base_d[:, None])
    did = (yt[post].mean() - yt[pre].mean()) - (yd[:, post].mean(axis=1) - yd[:, pre].mean(axis=1)).mean()
    return eff, w, did


def weekly(arr, first, t0, pre):
    """Weekly means of a market's daily outcome over days -pre..POST-1 around t0 (NaN where no data)."""
    i0 = (t0 - first).days - pre
    out = np.full(pre + POST, np.nan)
    lo, hi = max(i0, 0), min(i0 + pre + POST, len(arr))
    if hi > lo:
        out[lo - i0:hi - i0] = arr[lo:hi]
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        return np.nanmean(out.reshape(-1, 7), axis=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pre", type=int, default=PRE)
    ap.add_argument("--placebo", action="store_true")
    ap.add_argument("--min-pre-brier", type=float, default=None)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--boot", type=int, default=1000)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    pre, n_pre = a.pre, a.pre // 7
    rng = np.random.default_rng(0)
    m, ip, t, c, by_key, key = design("series", "ffill", a.placebo, a.limit, rng)
    first = c.groupby("ticker").day.first()
    arrs = {y: {tk: d[y].to_numpy(float) for tk, d in c.groupby("ticker")} for y in OUTCOMES}
    week_terms = [f"w{k}" for k in range(-n_pre, N_POST)]

    rows, per_market = [], []
    for y in OUTCOMES:
        res = []
        for r in t.itertuples(index=False):
            cand = by_key.get(getattr(r, key))
            if cand is None or r.ticker not in first.index:
                continue
            if a.min_pre_brier is not None:
                i0 = (r.t0 - first[r.ticker]).days
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", RuntimeWarning)
                    pb = np.nanmean(arrs["brier"][r.ticker][max(i0 - pre, 0):i0 - 7]) if i0 - 7 > 0 else np.nan
                if not pb >= a.min_pre_brier:
                    continue
            ok = cand[(cand["min"] <= r.t0 - pd.Timedelta(days=3)) & (cand["max"] >= r.t0 + pd.Timedelta(days=3))]
            donors = [tk for tk in ok.ticker if tk != r.ticker and tk in first.index]
            yt = weekly(arrs[y][r.ticker], first[r.ticker], r.t0, pre)
            if np.isnan(yt).any() or not donors:
                continue
            yd = np.array([weekly(arrs[y][tk], first[tk], r.t0, pre) for tk in donors])
            yd = yd[~np.isnan(yd).any(axis=1)]
            if len(yd) == 0:
                continue
            eff, w, did = sdid_one(yt, yd, n_pre)
            res.append({"outcome": y, "ticker": r.ticker, "series": r.series_ticker, "t0": r.t0.date(), "donors": len(yd),
                        "eff_donors": 1 / (w @ w), **dict(zip(week_terms, eff)), "post": eff[n_pre:].mean(), "did_same_sample": did})
        d = pd.DataFrame(res)
        per_market.append(d)
        if len(d) < 30:
            rows.append({"outcome": y, "term": "post", "stacks": len(d), "note": "too few treated markets"})
            continue
        # bootstrap over series: draw series with replacement, average the effects of their treated markets
        terms = ["post", "did_same_sample"] + week_terms
        g = d.groupby("series")
        sums, counts = g[terms].sum().to_numpy(), g.size().to_numpy()
        draws = rng.multinomial(len(counts), np.full(len(counts), 1 / len(counts)), size=a.boot)
        boot = (draws @ sums) / (draws @ counts)[:, None]
        base = {"outcome": y, "stacks": len(d), "series": len(counts), "donors": d.donors.mean(), "eff_donors": d.eff_donors.mean()}
        for j, term in enumerate(terms):
            coef, se = d[term].mean(), boot[:, j].std(ddof=1)
            rows.append({**base, "term": term, "coef": coef, "se": se, "t": coef / se if se > 0 else np.nan})
        rows.append({**base, "term": "post_median", "coef": d.post.median()})
        log(f"{y:<8} treated markets={len(d):>5,} in {len(counts):,} series  donors/market={d.donors.mean():.1f} "
            f"(effective {d.eff_donors.mean():.1f})  post: {d.post.mean():+.5f} (t={rows[-len(terms) - 1]['t']:+.1f}), "
            f"median {d.post.median():+.5f}, plain DiD {d.did_same_sample.mean():+.5f}  weeks: "
            + " ".join(f"{d[w].mean():+.4f}" for w in week_terms))
    suffix = f"_{a.tag}" if a.tag else ""
    pd.DataFrame(rows).to_csv(f"{R}/15_reward_sdid{suffix}.csv", index=False)
    pd.concat(per_market, ignore_index=True).to_csv(f"{R}/15_reward_sdid{suffix}_markets.csv", index=False)
    log("done")


if __name__ == "__main__":
    main()
