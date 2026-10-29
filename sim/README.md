# Market simulation

Agent-based simulation of a Kalshi-style yes/no market, for comparing policies that might make
long-horizon prices more informative. `model.py` has the model (its docstring describes every
parameter); `run.py` runs the experiments and writes `results/`; `run_entry.py` runs the
endogenous-entry extension and writes `results/entry_*.csv`.

## Model in brief

- One contract pays $1 if the event happens; time runs in days to resolution (365 by default),
  with several trading slots per day.
- Information: public news each day, plus private signals that each informed trader receives.
  `info_total`, `public_share` and `info_shape` set how much information there is, how much is
  public, and whether it arrives evenly or mostly near resolution.
- Informed traders discount the payoff to resolution (`informed_discount`) and pay a fee; they
  trade only when the discounted expected payoff beats the price. Extension: they can pay for more
  private information each day (`effort_cost`, `effort_info`). The research decision uses the
  trader's public belief and the closed-form surplus (earlier versions used the market maker's belief
  and quadrature; research-path Brier changes by at most 1e-4).
- Noise traders buy or sell at random.
- Extension: informed entry can respond to expected profits (`entry_elasticity`, `entry_pool`,
  `entry_cost`): potential informed traders enter when the surplus they expect before seeing their
  signal beats a recurring attention cost (power distribution, so the entry elasticity is the same
  wherever the surplus is positive and below the highest cost), solved jointly with the quotes in every slot; their realized
  trading profit is recorded next to the profit they expect.
  `overlap` makes part of the private information common to all informed traders.
- A competitive market maker sets bid and ask at its expected value after a sell or a buy
  (Glosten–Milgrom), plus an add-on for the capital it locks up until resolution, and learns from
  public news and order flow.

Policies (switches in `Params`): interest subsidy, market-making subsidy, our own noise trades, a
paid panel of informed traders, and a contract that settles early at a forecasting panel's published
probability (YES pays the probability, NO pays one minus it; the panel does not trade).

## Calibration

The default parameters roughly match Kalshi: Brier score by days to close (markets open a year or
more), the share of days with a trade and the bid-ask spread (the Rewards panel, `kalshi/scripts/a04_incentives.py`)
(`results/calibration.csv`; sources in `run.py`). The model's spreads are wider than Kalshi's 180
days or more before close, its Brier score in the final week is higher (0.056 vs 0.04), and it does
not reproduce the rise in trading in the final week.

## Running

```bash
python sim/run.py        # 30 runs of 2,000 markets (a few minutes on 16 cores); uses SLURM_CPUS_PER_TASK workers
python sim/run_entry.py  # entry extension: calibration, then ~290 runs of 2,000 markets (about an hour on 32 cores)
python sim/check_entry_roots.py  # after run_entry.py: how often more than one entry rate is consistent
```

On the cluster: from `kalshi/`,
`SCRIPT=$PWD/../sim/run.py sbatch --export=ALL --cpus-per-task=12 slurm/analysis.slurm` (same with
`run_entry.py` and `--cpus-per-task=32`).

Costs are in dollars per market, where every trade is one $1 contract. The costs of the panel
(their fee and capital cost) follow from the model and are an upper bound (capital cost is charged
on $1, while a panelist puts up only the price); the cost of the forecaster contract
(`forecast_cost`, $5 per unit of information) is an assumption.
