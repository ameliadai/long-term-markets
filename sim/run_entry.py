"""Endogenous informed entry: can subsidising noise trading attract enough informed participation to
improve accuracy? Writes sim/results/entry_*.csv.

Scenarios, each with entry elasticities 0, 0.5, 1, 2 and 4 (0 = fixed entry, the main model):
  main        fresh private information for each arriving trader; market maker learns from trades
  full        as main, but the market maker also learns from slots without a trade
  overlap50   half of the private information is shared by all informed traders
  overlap90   90% of it is shared
  effort      as main, plus the research extension (traders can buy more information of their own)
For each scenario and elasticity above 0, the pool of potential informed traders and the highest
attention cost are set so that, with no policy, informed traders arrive at 0.012 per slot on average
(the main model's rate) and the highest cost equals the 99th percentile of the positive surplus, so
the entry elasticity takes the scenario's value in 99% of market-slots with a positive surplus.
These primitives are then held fixed across policies. main and full run every policy at every strength; the others run the noise
subsidy.

  entry_calibration.csv  entry primitives per scenario and elasticity, and the no-policy market by
                         horizon next to the Kalshi targets
  entry_runs.csv         every run: sponsor cost; Brier gain vs the same scenario's no-policy run
                         (paired, with standard errors); activity per market (informed arrivals and
                         trades, noise trades, spread, share of days with a trade, informed traders'
                         expected and realized profit before participation costs, attention and
                         research spending)
                         and its change from the no-policy run
  entry_budget.csv       Brier gain at $1 per market, interpolated along each policy's strengths
  entry_paths.csv        by days to close, no-policy and noise-subsidy (strength 3) runs: Brier,
                         spread, share of days with a trade, informed entry rate
  entry_checks.csv       entry solution: other starting values (main and overlap90), a finer time
                         step, convergence
  entry_data.csv         the market-making subsidy that narrows spreads as much as Kalshi's rewards
                         did, and the change in days with a trade it implies, next to the rewards
                         event study
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from model import simulate  # noqa: E402
from run import BASE, KALSHI, POLICIES, SEED  # noqa: E402

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
N = int(os.environ.get("SIM_N", 2000))
CAL_N = int(os.environ.get("CAL_N", N))
EPS = [0.0, 0.5, 1.0, 2.0, 4.0]
SCEN = {"main": dict(), "full": dict(learn_from_no_trade=True), "overlap50": dict(overlap=0.5),
        "overlap90": dict(overlap=0.9), "effort": dict(effort_cost=0.0001, effort_info=0.002)}
ALL_POLICIES = ("main", "full")
TARGET = BASE.informed_rate
METRICS = ["informed_arrivals", "informed_trades", "noise_trades", "spread", "days_traded",
           "expected_profit", "realized_profit", "entry_spend", "research_spend"]
REWARDS = ROOT.parent / "kalshi" / "results" / "13_reward_event_study_price_ffill.csv"


def calibrate(arg):
    """Entry primitives for one scenario and elasticity (see the module docstring)."""
    scen, eps = arg
    base = BASE.with_(**SCEN[scen])
    if eps == 0:
        return {"scenario": scen, "eps": eps, "entry_pool": np.nan, "entry_cost": np.nan, "iterations": 0}
    cost, pool = simulate(base, n=CAL_N, seed=SEED)["checks"]["net_q99"], 2 * TARGET * 2 ** eps
    for it in range(12):
        c = simulate(base.with_(entry_elasticity=eps, entry_pool=pool, entry_cost=cost), n=CAL_N, seed=SEED)["checks"]
        if abs(c["alpha_mean"] / TARGET - 1) < 0.01 and abs(c["net_q99"] / cost - 1) < 0.02:
            break
        pool, cost = pool * TARGET / c["alpha_mean"], c["net_q99"]
    return {"scenario": scen, "eps": eps, "entry_pool": pool, "entry_cost": cost, "iterations": it + 1,
            "cal_alpha_mean": c["alpha_mean"], "cal_net_q99": c["net_q99"]}


def run(kw):
    o = simulate(BASE.with_(**kw), n=N, seed=SEED)
    return {k: o[k] for k in ["brier", "spread", "traded", "alpha", "cost", "market_brier", "market_stats", "checks"]}


def paired(a, b):
    d = a - b
    return d.mean(), d.std(ddof=1) / np.sqrt(len(d))


def main():
    OUT.mkdir(exist_ok=True)
    workers = int(os.environ.get("SLURM_CPUS_PER_TASK", 2))
    with ProcessPoolExecutor(workers) as ex:
        cal = pd.DataFrame(list(ex.map(calibrate, [(s, e) for s in SCEN for e in EPS])))
        prim = {(r.scenario, r.eps): ({} if r.eps == 0 else dict(entry_elasticity=r.eps, entry_pool=r.entry_pool, entry_cost=r.entry_cost))
                for r in cal.itertuples()}

        jobs = {}
        for s in SCEN:
            pols = POLICIES if s in ALL_POLICIES else {"noise": POLICIES["noise"]}
            for e in EPS:
                kw = {**SCEN[s], **prim[(s, e)]}
                jobs[(s, e, "base", 0)] = kw
                for name, (_, grid) in pols.items():
                    for i, g in enumerate(grid):
                        jobs[(s, e, name, i + 1)] = {**kw, **g}
        noise3 = POLICIES["noise"][1][2]
        e2, o4 = prim[("main", 2.0)], prim[("overlap90", 4.0)]
        for start in ("zero", "pool"):
            jobs[(f"check_{start}_overlap90", 4.0, "base", 0)] = {**SCEN["overlap90"], **o4, "entry_start": start}
            jobs[(f"check_{start}_overlap90", 4.0, "noise", 3)] = {**SCEN["overlap90"], **o4, **noise3, "entry_start": start}
        for i, extra in enumerate([{}, noise3]):
            jobs[("check_zero", 2.0, "base" if not extra else "noise", 3 * i)] = {**e2, **extra, "entry_start": "zero"}
            jobs[("check_pool", 2.0, "base" if not extra else "noise", 3 * i)] = {**e2, **extra, "entry_start": "pool"}
            for e in (0.0, 2.0):
                pr = prim[("main", e)]
                fine = dict(slots=8, noise_rate=BASE.noise_rate / 2, informed_rate=BASE.informed_rate / 2)
                if pr:
                    fine["entry_pool"] = pr["entry_pool"] / 2
                if extra:
                    fine["extra_noise_rate"] = extra["extra_noise_rate"] / 2
                jobs[("check_slots8", e, "base" if not extra else "noise", 3 * i)] = {**pr, **fine}
        res = dict(zip(jobs, ex.map(run, jobs.values())))

    # no-policy market by horizon, next to the Kalshi targets
    T = BASE.T
    for col in ["brier", "traded", "spread"]:
        for d in KALSHI["days_to_close"]:
            cal[f"{col}_{d}"] = [res[(r.scenario, r.eps, "base", 0)][col][T - d] for r in cal.itertuples()]
    cal["alpha_mean"] = [res[(r.scenario, r.eps, "base", 0)]["checks"]["alpha_mean"] for r in cal.itertuples()]
    for d in KALSHI["days_to_close"]:
        cal[f"alpha_{d}"] = [res[(r.scenario, r.eps, "base", 0)]["alpha"][T - d] for r in cal.itertuples()]
    cal.to_csv(OUT / "entry_calibration.csv", index=False)

    label = {k: v[0] for k, v in POLICIES.items()}
    rows, per_market = [], {}
    for (s, e, name, i), r in res.items():
        b = res.get((s if not s.startswith("check") else s, e, "base", 0))
        row = {"scenario": s, "eps": e, "policy": name, "label": label.get(name, "No policy"), "strength": i,
               "setting": ", ".join(f"{k}={v}" for k, v in jobs[(s, e, name, i)].items()), "cost": r["cost"],
               "alpha_mean": r["checks"]["alpha_mean"], "entry_iters": r["checks"]["entry_iters"],
               "entry_iters_max": r["checks"]["entry_iters_max"], "entry_gap_max": r["checks"]["entry_gap_max"],
               "arrival_prob_max": r["checks"]["arrival_prob_max"]}
        for h in ["life", 180, 90, 30]:
            row[f"gain_{h}"], row[f"se_{h}"] = paired(b["market_brier"][h], r["market_brier"][h])
        for k in METRICS:
            row[k] = r["market_stats"][k].mean()
            row[f"d_{k}"], row[f"se_d_{k}"] = paired(r["market_stats"][k], b["market_stats"][k])
        rows.append(row)
        per_market[(s, e, name, i)] = {h: b["market_brier"][h] - r["market_brier"][h] for h in ["life", 180, 90]}
    runs = pd.DataFrame(rows)
    runs.to_csv(OUT / "entry_runs.csv", index=False)

    # Brier gain at $1 per market: per-market gains interpolated between the two strengths around $1
    brows = []
    for s in SCEN:
        for e in EPS:
            for name in runs[(runs.scenario == s) & (runs.policy != "base")].policy.unique():
                g = runs[(runs.scenario == s) & (runs.eps == e) & (runs.policy == name)].sort_values("cost")
                c = np.r_[0.0, g.cost.to_numpy()]
                row = {"scenario": s, "eps": e, "policy": name, "label": label[name], "budget": 1.0}
                if c.max() < 1.0:
                    brows.append(row)
                    continue
                j = int(np.searchsorted(c, 1.0))
                w = (1.0 - c[j - 1]) / (c[j] - c[j - 1])
                for h in ["life", 180, 90]:
                    lo = 0.0 if j == 1 else per_market[(s, e, name, int(g.strength.iloc[j - 2]))][h]
                    hi = per_market[(s, e, name, int(g.strength.iloc[j - 1]))][h]
                    v = (1 - w) * lo + w * hi
                    row[f"gain_{h}"], row[f"se_{h}"] = v.mean(), v.std(ddof=1) / np.sqrt(len(v))
                brows.append(row)
    pd.DataFrame(brows).to_csv(OUT / "entry_budget.csv", index=False)

    d2c = T - np.arange(T)
    pd.concat([pd.DataFrame({"scenario": s, "eps": e, "policy": name, "days_to_close": d2c, "brier": r["brier"],
                             "spread": r["spread"], "traded": r["traded"], "alpha": r["alpha"]})
               for (s, e, name, i), r in res.items() if not s.startswith("check") and (name == "base" or (name == "noise" and i == 3))]
              ).to_csv(OUT / "entry_paths.csv", index=False)

    chk = runs[runs.scenario.str.startswith("check")].copy()
    chk["reference"] = ["overlap90" if r.scenario.endswith("overlap90") else "main" for r in chk.itertuples()]
    ref = runs.set_index(["scenario", "eps", "policy", "strength"])
    chk["main_gain_life"] = [ref.loc[(r.reference, r.eps, r.policy, r.strength), "gain_life"] if r.policy != "base" else np.nan for r in chk.itertuples()]
    chk["main_alpha_mean"] = [ref.loc[(r.reference, r.eps, r.policy, r.strength), "alpha_mean"] for r in chk.itertuples()]
    for k in ["life", 180, 90]:
        chk[f"brier_{k}"] = [res[(r.scenario, r.eps, r.policy, r.strength)]["market_brier"][k].mean() for r in chk.itertuples()]
        chk[f"main_brier_{k}"] = [res[(r.reference, r.eps, r.policy, r.strength)]["market_brier"][k].mean() for r in chk.itertuples()]
    conv = runs[~runs.scenario.str.startswith("check")].groupby("scenario")[["entry_iters", "entry_iters_max", "entry_gap_max", "arrival_prob_max"]].max().reset_index()
    pd.concat([chk, conv.assign(policy="all runs (max)")]).to_csv(OUT / "entry_checks.csv", index=False)

    # rewards event study vs the model's market-making subsidy
    ev = pd.read_csv(REWARDS)
    ev = ev[(ev["sample"] == "all") & (ev.term == "post")].set_index("outcome")
    target = ev.loc["spread", "coef"] / 100
    drows = []
    for s in ALL_POLICIES:
        for e in EPS:
            g = runs[(runs.scenario == s) & (runs.eps == e) & (runs.policy == "mm")].sort_values("strength")
            ds, dt = np.r_[0.0, g.d_spread.to_numpy()], np.r_[0.0, g.d_days_traded.to_numpy()]
            q = np.r_[0.0, [POLICIES["mm"][1][k - 1]["mm_subsidy"] for k in g.strength]]
            drows.append({"scenario": s, "eps": e, "kalshi_d_spread": target, "kalshi_d_spread_se": ev.loc["spread", "se"] / 100,
                          "kalshi_d_traded": ev.loc["traded", "coef"], "kalshi_d_traded_se": ev.loc["traded", "se"],
                          "mm_subsidy": float(np.interp(-target, -ds, q)), "model_d_traded": float(np.interp(-target, -ds, dt)),
                          "model_d_traded_at_max": dt[-1], "model_d_spread_at_max": ds[-1]})
    pd.DataFrame(drows).to_csv(OUT / "entry_data.csv", index=False)

    b = pd.DataFrame(brows)
    print(cal[["scenario", "eps", "entry_pool", "entry_cost", "iterations", "alpha_mean", "brier_180", "traded_180", "spread_180"]].round(4).to_string(index=False))
    print(b[b.policy == "noise"].pivot(index="eps", columns="scenario", values="gain_life").round(4).to_string())
    print(b.pivot_table(index=["scenario", "policy"], columns="eps", values="gain_life").round(4).to_string())
    print(pd.DataFrame(drows).round(4).to_string(index=False))


if __name__ == "__main__":
    main()
