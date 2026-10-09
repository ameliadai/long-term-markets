# Kalshi data

## Sources

- `gs://prophet-kalshi-archive`: public archive of Kalshi's API (SQL dumps as of 21 Sep 2026),
  streamed part by part, never downloaded in full.
- Kalshi public API (`api.elections.kalshi.com/trade-api/v2`): open markets, order books, and
  reward programs (`/incentive_programs`; `period_reward` is in centi-cents, divide by 10,000 for USD).
- Optional: `scripts/bq.py` queries a BigQuery copy of the archive with a hard cap on bytes billed.

## Files in `data/` (not in git)

| File | What | Made by |
|---|---|---|
| `events.parquet`, `series.parquet` | all events and series | `scripts/extract_events_series.py` |
| `markets/*.parquet` → `markets.parquet` | every non-combo market with its listing horizon; combo (KXMVE*) markets summarized in `mve_summary.parquet` | `scripts/extract_markets.py`, `scripts/build_tables.py` |
| `candles_daily/*.parquet` → `candles_daily.parquet` | per market per day: volume, last price, bid/ask, median spread, open interest | `scripts/extract_candles.py`, `scripts/build_tables.py` |
| `trades_daily/*.parquet` → `trades_daily.parquet` | per market per day from the trade tape (15 Jul – 21 Sep 2026) | `scripts/extract_trades.py`, `scripts/build_tables.py` |
| `incentive_programs.parquet` | all reward programs, Sep 2025 – Sep 2026 | public API `/incentive_programs` |
| `open_markets_snapshot.parquet`, `open_markets_enriched.parquet` | open non-combo markets on 23 Sep 2026 | `scripts/snapshot_open_markets.py` |
| `orderbooks_snapshot.parquet`, `orderbooks_enriched.parquet` | order-book depth for a sample of open markets | `scripts/snapshot_orderbooks.py` |

## Jobs

Submit from this folder. Extraction tasks skip files whose output already exists, so
re-submitting only redoes failed ones (logs in `slurm/logs/`). The job files activate the conda
environment named in `CONDA_ENV` (default `long-term-markets`).

```bash
KIND=markets sbatch --array=1-6  --export=ALL slurm/extract.slurm
KIND=candles sbatch --array=1-47 --export=ALL slurm/extract.slurm
KIND=trades  sbatch --array=1-14 --export=ALL slurm/extract.slurm
sbatch slurm/build_tables.slurm   # after all three succeed
```

Analysis scripts that need more memory than a login node (e.g. `a13_reward_event_study.py`) run
through `slurm/analysis.slurm`; arguments for the script go in `ARGS`:

```bash
SCRIPT=a13_reward_event_study.py ARGS="--match price --price ffill --tag price_ffill" sbatch --export=ALL slurm/analysis.slurm
```

The website reads these a13 versions (tag: arguments):

| Tag | Arguments | What changes from the main version |
|---|---|---|
| `price_ffill` | `--match price --price ffill` | main version |
| `random` | `--match none --price ffill` | controls drawn at random |
| `series_matched` | `--match volume --price ffill` | controls matched on trading volume |
| `brier_matched` | `--match brier --price ffill` | controls matched on starting Brier score |
| `event_price` | `--controls event --match price --price ffill` | controls from the same event only |
| `event_matched` | `--controls event --match volume --price ffill` | same event, matched on volume |
| `mid` | `--match price --price mid` | Brier only on days with two-sided quotes |
| `pre56` | `--match price --price ffill --pre 56` | 8-week before-period |
| `uncertain` | `--match price --price ffill --min-pre-brier 0.05` | only markets that start out uncertain |
| `placebo_uncertain` | `... --placebo --min-pre-brier 0.05` | fake reward dates, uncertain markets |
| `placebo` | `--match price --price ffill --placebo` | fake reward dates |

Run `a13_example.py` after the main version.
