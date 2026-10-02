"""Build the Polymarket contract-day panel and run the Brier-on-volume regressions.

Panel (data/pm_panel.parquet), one row per resolved market per day with a price:
  brier        = (price - outcome)^2, price = CLOB daily price of the first outcome
  cum_prior_sh = shares traded in the market before that day (from trades_daily)
  days_to_exp  = days from that day to the market's close; duration_days, category, month

Regressions (results/pm_brier_volume_regressions.csv), SEs clustered by event:
  (1) Brier ~ log(1 + cum volume) + days_to_exp | month FE
  (2) Brier ~ log(1 + cum volume) + days_to_exp + duration_days | month FE + category FE
  (3) Brier ~ log(1 + cum volume) + days_to_exp | month FE + contract FE
  (4) Brier ~ log(1 + cum volume) | month FE + contract FE + days-to-expiry bin FE
      (same bins as the Kalshi a10 script)
The CLOB price series has no bid/ask, so Kalshi's "two-sided quotes only" rule cannot be applied.
Also writes the category mix (results/pm_category_mix.csv) and specs (1), (3), (4) run separately
for each category (results/pm_by_category.csv), for all markets and markets open > 180 days.
Samples: all; duration > 180 days; expired in 2023, 2024, 2025, 2026.
Only markets that started on or after TRADES_FROM (the first day the Data API has trades) are used.
Variants: "all days", and "drop last day" (each market's last day with a price is removed;
on that day the price usually already reflects the outcome).
"""
import glob
import os

import numpy as np
import pandas as pd

from pm_common import DATA, ROOT, TRADES_FROM

RES = os.environ.get("PM_RESULTS", os.path.join(ROOT, "results"))


def read_parts(sub):
    fs = [f for f in glob.glob(os.path.join(DATA, sub, "*_part*.parquet"))]
    return pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True) if fs else pd.DataFrame()


def fe_ols(df, y, xs, fes, cluster="event_id", tol=1e-8, max_iter=1000):
    Z = df[[y] + xs].to_numpy(np.float64).copy()
    groups = [pd.factorize(df[f])[0] for f in fes]
    counts = [np.bincount(g) for g in groups]
    for _ in range(max_iter):
        prev = Z.copy()
        for g, n in zip(groups, counts):
            for j in range(Z.shape[1]):
                Z[:, j] -= (np.bincount(g, weights=Z[:, j]) / n)[g]
        if len(groups) == 1 or np.abs(Z - prev).max() < tol:
            break
    Y, X = Z[:, 0], Z[:, 1:]
    inv = np.linalg.pinv(X.T @ X)
    beta = inv @ X.T @ Y
    u = Y - X @ beta
    cl = pd.factorize(df[cluster])[0]
    S = np.column_stack([np.bincount(cl, weights=X[:, j] * u) for j in range(X.shape[1])])
    G = S.shape[0]
    V = inv @ (S.T @ S) @ inv * G / (G - 1)
    return beta, np.sqrt(np.diag(V)), G, 1 - (u @ u) / (Y @ Y)


def main():
    os.makedirs(RES, exist_ok=True)
    sel = pd.read_parquet(os.path.join(DATA, "pm_selected.parquet"))
    pr = read_parts("prices")
    pr["day"] = pd.to_datetime(pr.t, unit="s", utc=True).dt.floor("D").astype("datetime64[ns, UTC]")
    pr = pr.sort_values(["market_id", "t"]).drop_duplicates(["market_id", "day"], keep="last")
    td = read_parts("trades_daily")
    sel = sel[sel.start >= pd.Timestamp(TRADES_FROM, tz="UTC")]      # cumulative volume is complete only for these
    panel = pr.merge(sel, on="market_id", how="inner")
    if len(td):
        td["day"] = pd.to_datetime(td.day, utc=True).astype("datetime64[ns, UTC]")
        td = td.sort_values(["market_id", "day"])
        td["cum_through"] = td.groupby("market_id").shares.cumsum()      # shares up to and including that day
        td = td.rename(columns={"day": "tday"})[["market_id", "tday", "shares", "cum_through"]]
        # latest trade day at or before each price day
        panel = pd.merge_asof(panel.sort_values("day"), td.sort_values("tday"), left_on="day", right_on="tday",
                              by="market_id", direction="backward")
        same_day = panel.tday == panel.day
        panel["cum_prior_sh"] = np.where(same_day, panel.cum_through - panel.shares, panel.cum_through)
        panel["cum_prior_sh"] = panel.cum_prior_sh.fillna(0)
        panel = panel.drop(columns=["tday", "shares", "cum_through"])
    else:
        panel["cum_prior_sh"] = 0.0
    panel["days_to_exp"] = (panel.end - panel.day).dt.total_seconds() / 86400
    panel = panel[(panel.days_to_exp >= 0) & panel.p.between(0, 1)]
    panel["brier"] = (panel.p - panel.y) ** 2
    panel["log_cum_vol"] = np.log1p(panel.cum_prior_sh.clip(lower=0))
    panel["month"] = panel.day.dt.strftime("%Y-%m")
    hz_edges = [0, 1, 2, 3, 4, 5, 6, 7, 14, 21, 28, 42, 56, 90, 120, 150, 180, 240, 300, 365, np.inf]
    panel["hz_bin"] = pd.cut(panel.days_to_exp, hz_edges, right=False, labels=False)
    panel["exp_year"] = panel.end.dt.year
    panel = panel.sort_values(["market_id", "day"])
    panel["last_day"] = ~panel.market_id.duplicated(keep="last")
    panel.to_parquet(os.path.join(DATA, "pm_panel.parquet"), index=False)
    print(f"panel: {len(panel):,} market-days, {panel.market_id.nunique():,} markets, {panel.event_id.nunique():,} events")

    specs = {
        "(1) month FE": (["log_cum_vol", "days_to_exp"], ["month"]),
        "(2) + category FE + duration": (["log_cum_vol", "days_to_exp", "duration_days"], ["month", "category_coarse"]),
        "(3) month FE + contract FE": (["log_cum_vol", "days_to_exp"], ["month", "market_id"]),
        "(4) + days-to-expiry bins": (["log_cum_vol"], ["month", "market_id", "hz_bin"]),
    }
    rows = []
    for vname, pv in {"all days": panel, "drop last day": panel[~panel.last_day]}.items():
        samples = {"all": pv, "duration > 180 days": pv[pv.duration_days > 180]}
        for yr in (2023, 2024, 2025, 2026):
            samples[f"expired in {yr}"] = pv[pv.exp_year == yr]
        for sname, d in samples.items():
            for spec, (xs, fes) in specs.items():
                base = {"variant": vname, "sample": sname, "spec": spec, "n": len(d), "markets": d.market_id.nunique(),
                        "events": d.event_id.nunique(), "mean_brier": d.brier.mean() if len(d) else np.nan}
                if d.event_id.nunique() < 20:
                    rows.append({**base, "note": "too few events"})
                    continue
                b, se, G, r2 = fe_ols(d, "brier", xs, fes)
                for x, bb, ss in zip(xs, b, se):
                    rows.append({**base, "term": x, "coef": bb, "se": ss, "t": bb / ss, "clusters": G, "r2_within": r2})
                print(f"{vname} | {sname} | {spec} | n={len(d):,} | "
                      + ", ".join(f"{x}: {bb:.5f} ({ss:.5f})" for x, bb, ss in zip(xs, b, se)), flush=True)
    pd.DataFrame(rows).to_csv(os.path.join(RES, "pm_brier_volume_regressions.csv"), index=False)

    mix, cat_rows = [], []
    for vname, pv in {"all days": panel, "drop last day": panel[~panel.last_day]}.items():
        for sname, d0 in {"all": pv, "duration > 180 days": pv[pv.duration_days > 180]}.items():
            mix.append(d0.groupby("category_coarse").agg(markets=("market_id", "nunique"), market_days=("market_id", "size"))
                       .reset_index().rename(columns={"category_coarse": "category"}).assign(sample=sname, variant=vname))
            for cat, d in d0.groupby("category_coarse"):
                for spec in ("(1) month FE", "(3) month FE + contract FE", "(4) + days-to-expiry bins"):
                    xs, fes = specs[spec]
                    base = {"variant": vname, "sample": sname, "category": cat, "spec": spec, "n": len(d),
                            "markets": d.market_id.nunique(), "events": d.event_id.nunique(), "mean_brier": d.brier.mean()}
                    if base["events"] < 20:
                        cat_rows.append({**base, "note": "too few events"})
                        continue
                    b, se, G, r2 = fe_ols(d, "brier", xs, fes)
                    for x, bb, ss in zip(xs, b, se):
                        cat_rows.append({**base, "term": x, "coef": bb, "se": ss, "t": bb / ss, "clusters": G})
            print(f"by category done: {vname} | {sname}", flush=True)
    pd.concat(mix).to_csv(os.path.join(RES, "pm_category_mix.csv"), index=False)
    pd.DataFrame(cat_rows).to_csv(os.path.join(RES, "pm_by_category.csv"), index=False)


if __name__ == "__main__":
    main()
