# long-term-markets

What makes long-horizon prediction markets informative? This repo collects data from
**Kalshi** and **Polymarket**, measures how accurate prices are at different distances from
resolution, how trading and liquidity relate to accuracy, and what platform subsidies
(Kalshi's reward programs) change. Results are shown on a static website (`website/`).

## Layout

```
kalshi/
  scripts/     extraction (archive dumps, public API) and analyses a01–a12
  slurm/       batch jobs for the extraction
  data/        local data (not in git; rebuilt by the scripts)
  results/     analysis outputs (CSV)
polymarket/
  scripts/     API pipeline (markets, daily prices, trades), regressions, Kalshi-shaped tables
  slurm/       batch jobs for the pipeline
  data/, kshape/   local data (not in git)
  results/     analysis outputs (CSV)
website/       static site: index.html, site.js, charts.js, style.css, data/site.json
environment.yml
```

## Setup

```bash
conda env create -f environment.yml
conda activate long-term-markets
```

## Kalshi

Data come from a public archive of Kalshi's API (`gs://prophet-kalshi-archive`, SQL dumps as of
21 Sep 2026, streamed rather than downloaded) and from Kalshi's public API (open markets, order
books, reward programs). See [`kalshi/README.md`](kalshi/README.md) for the data files and jobs.

```bash
cd kalshi/scripts
python a01_landscape.py        # then a02, a03, a04, a05, a06, a08, a09, a10, a11, a12, a13 (+ a13_example), a14
```

| Script | What it does |
|---|---|
| `a01_landscape.py` | markets and volume by listing horizon and category |
| `a02_volume_to_close.py` | how much long markets trade at each distance from resolution |
| `a03_accuracy.py` | Brier score, AUC and calibration 1–365 days before close |
| `a04_incentives.py`, `a04_twfe.py` | reward-program coverage, and market outcomes on reward days |
| `a05_info_vs_activity.py` | do reward days move prices toward the outcome; favourite/long-shot returns |
| `a06_trades.py` | trade counts and sizes by horizon |
| `a08_accuracy_vs_liquidity.py` | accuracy by liquidity (spread, open interest, volume, trading days) |
| `a09_robustness.py` | calibration by horizon, favourite-return robustness |
| `a10_brier_volume_regressions.py` | daily Brier score on cumulative past volume, five specifications |
| `a11_resolution_timing.py` | late resolution, and markets whose last days already show the answer |
| `a12_regression_checks.py` | robustness checks for a10 (time bins, stale prices, weights, reward instrument) |
| `a13_reward_event_study.py` | before/after a market's first liquidity reward vs never-rewarded markets in the same series (stacked event study; options for controls, matching, placebo) |
| `a13_example.py` | one worked example for a13: a typical rewarded market, its controls, and their before/after numbers |
| `a14_reward_programs.py` | the five kinds of reward program (size, timing), and reward coverage by category |

## Polymarket

Built from Polymarket's public APIs (Gamma markets, CLOB price history, Data API trades). See
[`polymarket/README.md`](polymarket/README.md). The same Kalshi analyses run on Polymarket through
Kalshi-shaped tables:

```bash
python polymarket/scripts/pm_kshape.py
for s in a01_landscape a02_volume_to_close a03_accuracy a06_trades a08_accuracy_vs_liquidity a09_robustness a11_resolution_timing; do
  KL_DATA=polymarket/kshape KL_RESULTS=polymarket/results python kalshi/scripts/$s.py
done
```

## Website

```bash
python website/build_site.py           # results -> website/data/site.json
cd website && python3 -m http.server 8767
```

The site is static and reads only `website/data/site.json`, so any static host can serve the
`website/` folder (`netlify.toml` points Netlify there).

## Caveats

- Sports and crypto markets are left out of every analysis: they are mostly very short games and
  price brackets. Set `KL_ALL_CATEGORIES=1` to keep them (see `EXCLUDE` in
  `kalshi/scripts/common.py` and `polymarket/scripts/pm_common.py`).

- Kalshi's archive covers markets still open on 14 Jul 2026 or later (plus about 4,000 that closed
  earlier in 2026); individual trades only for 15 Jul – 21 Sep 2026. No order-book history.
- Polymarket's trade records start on 30 Sep 2023, so only markets that started on or after that
  date are analysed. Daily prices are taken at 00:00 UTC and have no bid/ask.
- All results are associations, not causal effects.
