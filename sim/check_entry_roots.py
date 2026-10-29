"""How often is more than one entry rate consistent with the quotes? For each scenario of run_entry.py
at entry elasticities 1, 2 and 4 (no policy, 300 markets), every time the entry rate is solved it is also
solved starting from no entry and from the whole pool, in the same state; writes the share of
market-slots where either finds a different rate to results/entry_roots.csv. Run after run_entry.py.
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import model  # noqa: E402
from run import BASE, SEED  # noqa: E402
from run_entry import SCEN  # noqa: E402

OUT = Path(__file__).resolve().parent / "results"


def roots(arg):
    scen, eps, kw = arg
    gaps = []
    solve = model.Market.equilibrium

    def checked(self, *a):
        out = solve(self, *a)
        p, alpha, iters = self.p, self.alpha.copy(), list(self.iters)
        other = []
        for start in ("zero", "pool"):
            self.p = replace(p, entry_start=start)
            solve(self, *a)
            other.append(np.abs(self.alpha - alpha))
        self.p, self.alpha, self.iters = p, alpha, iters
        gaps.append(np.maximum(*other))
        return out

    model.Market.equilibrium = checked
    model.simulate(BASE.with_(**kw), n=300, seed=SEED)
    g = np.concatenate(gaps)
    return {"scenario": scen, "eps": eps, "market_slots": g.size, "share_other_rate": float((g > 1e-4).mean()),
            "largest_difference": float(g.max())}


def main():
    cal = pd.read_csv(OUT / "entry_calibration.csv")
    args = [(r.scenario, r.eps, {**SCEN[r.scenario], "entry_elasticity": r.eps, "entry_pool": r.entry_pool, "entry_cost": r.entry_cost})
            for r in cal.itertuples() if r.eps in (1.0, 2.0, 4.0)]
    with ProcessPoolExecutor(int(os.environ.get("SLURM_CPUS_PER_TASK", 2))) as ex:
        out = pd.DataFrame(list(ex.map(roots, args)))
    out.to_csv(OUT / "entry_roots.csv", index=False)
    print(out.to_string(index=False))


if __name__ == "__main__":
    main()
