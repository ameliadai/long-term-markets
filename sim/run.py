"""Run the simulation experiments and write sim/results/*.csv.

  calibration.csv  baseline vs Kalshi (Brier, share of days with a trade, spread) by days to close
  policies.csv     each policy at several strengths: cost per market and Brier gain vs baseline
                   (paired: same markets and outcomes), averaged over the market's life and at
                   180 / 90 / 30 days to close, with standard errors
  budget.csv       Brier gain at equal cost per market (interpolated along each policy's strengths)
  sensitivity.csv  each policy at its third strength when the market maker also learns from slots
                   without a trade
  paths.csv        by days to close: Brier, spread and share of days with a trade for the baseline,
                   each policy at its middle strength, two information-flow settings and the effort
                   extension
Costs are in dollars per market, where every trade is one $1 contract.
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model import Params, simulate  # noqa: E402

N, SEED = 2000, 7
OUT = Path(__file__).resolve().parent / "results"
BASE = Params()
FC_DAY = BASE.T - 183                       # forecast contract settles about six months before close
# Kalshi targets. Brier: kalshi/results/03_accuracy_h365.csv (markets open a year or more).
# Traded, spread: kalshi/results/04_panel.parquet (Rewards panel, a04_incentives.py), mean share
# traded and median spread over the days between each horizon and the next shorter one (e.g.
# 181-365 days before close for 365).
KALSHI = {"days_to_close": [365, 180, 90, 30, 7],
          "brier": [0.20, 0.13, 0.09, 0.06, 0.04], "traded": [0.22, 0.20, 0.19, 0.26, 0.36],
          "spread": [0.05, 0.05, 0.05, 0.04, 0.025]}
POLICIES = {   # name -> (label, parameter values for each strength)
    "interest": ("Interest subsidy", [dict(interest_subsidy=v) for v in (0.03, 0.06, 0.10, 0.15)]),
    "mm": ("Market-making subsidy", [dict(mm_subsidy=v) for v in (0.005, 0.01, 0.02, 0.04)]),
    "noise": ("We become noise traders", [dict(extra_noise_rate=v) for v in (0.005, 0.01, 0.02, 0.04)]),
    "panel": ("Paid panel of informed traders", [dict(panel_rate=v) for v in (0.005, 0.01, 0.02, 0.04)]),
    "forecast": ("Forecaster contract", [dict(forecast_day=FC_DAY, forecast_info=v, forecast_cost=5 * v) for v in (0.05, 0.1, 0.2, 0.4)]),
}
EXTRA = {"info_even": dict(info_shape=0.0), "info_late": dict(info_shape=3.0),
         "effort": dict(effort_cost=0.0001, effort_info=0.002)}


def run(kw):
    return simulate(BASE.with_(**kw), n=N, seed=SEED)


def main():
    OUT.mkdir(exist_ok=True)
    jobs = {("base", 0): {}}
    for name, (_, grid) in POLICIES.items():
        for i, kw in enumerate(grid):
            jobs[(name, i)] = kw
    for name, kw in EXTRA.items():
        jobs[(name, 0)] = kw
    jobs[("sens_base", 0)] = dict(learn_from_no_trade=True)
    for name, (_, grid) in POLICIES.items():
        jobs[("sens_" + name, 0)] = dict(grid[2], learn_from_no_trade=True)
    workers = int(os.environ.get("SLURM_CPUS_PER_TASK", 2))
    with ProcessPoolExecutor(workers) as ex:
        res = dict(zip(jobs, ex.map(run, jobs.values())))
    base = res[("base", 0)]
    d2c = base["days_to_close"]

    cal = pd.DataFrame(KALSHI)
    for col in ["brier", "traded", "spread"]:
        cal[f"model_{col}"] = [base[col][BASE.T - d] for d in cal.days_to_close]
    cal.to_csv(OUT / "calibration.csv", index=False)

    rows = []
    for name, (label, grid) in POLICIES.items():
        for i, kw in enumerate(grid):
            r = res[(name, i)]
            row = {"policy": name, "label": label, "strength": i + 1, "setting": ", ".join(f"{k}={v}" for k, v in kw.items()),
                   "cost": r["cost"], "spread_far": r["spread"][: BASE.T - 180].mean(), "traded_far": r["traded"][: BASE.T - 180].mean()}
            for h in ["life", 180, 90, 30]:
                d = base["market_brier"][h] - r["market_brier"][h]          # paired: same markets
                row[f"gain_{h}"], row[f"se_{h}"] = d.mean(), d.std(ddof=1) / np.sqrt(len(d))
            rows.append(row)
    pol = pd.DataFrame(rows)
    pol.to_csv(OUT / "policies.csv", index=False)

    brows = []
    for budget in (0.25, 0.5, 1.0, 2.0):
        for name, (label, _) in POLICIES.items():
            g = pol[pol.policy == name].sort_values("cost")
            c = np.r_[0.0, g.cost.to_numpy()]
            row = {"budget": budget, "policy": name, "label": label}
            for h in ["life", 180, 90]:
                v = np.r_[0.0, g[f"gain_{h}"].to_numpy()]
                row[f"gain_{h}"] = float(np.interp(budget, c, v)) if budget <= c.max() else np.nan
            brows.append(row)
    pd.DataFrame(brows).to_csv(OUT / "budget.csv", index=False)

    sb, srows = res[("sens_base", 0)], []
    for name, (label, grid) in POLICIES.items():
        r = res[("sens_" + name, 0)]
        d = sb["market_brier"]["life"] - r["market_brier"]["life"]
        main = pol[(pol.policy == name) & (pol.strength == 3)].iloc[0]
        srows.append({"policy": name, "label": label, "cost": r["cost"], "gain_life": d.mean(), "se_life": d.std(ddof=1) / np.sqrt(len(d)),
                      "main_gain_life": main.gain_life, "main_se_life": main.se_life})
    pd.DataFrame(srows).to_csv(OUT / "sensitivity.csv", index=False)

    paths = {"base": base, **{name: res[(name, 1)] for name in POLICIES}, **{name: res[(name, 0)] for name in EXTRA}}
    pd.concat([pd.DataFrame({"scenario": k, "days_to_close": d2c, "brier": v["brier"], "spread": v["spread"], "traded": v["traded"]})
               for k, v in paths.items()]).to_csv(OUT / "paths.csv", index=False)
    print(cal.round(3).to_string(index=False))
    print(pol[["label", "strength", "cost", "gain_life", "se_life", "gain_180", "gain_90"]].round(4).to_string(index=False))


if __name__ == "__main__":
    main()
