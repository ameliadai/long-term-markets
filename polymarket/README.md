# Polymarket pipeline

Polymarket counterpart of the Kalshi data: every market, daily prices and full trade
history for resolved markets, then the contract-day Brier-on-volume regressions.

```bash
bash slurm/submit_all.sh             # from this folder: 01 -> (02, 03) -> 04, with dependencies
bash slurm/submit_all.sh --from-02   # market list already built
squeue -u $USER                      # progress; logs in slurm/logs/
```

The job files activate the conda environment named in `CONDA_ENV` (default `long-term-markets`).

| Step | Script | Source | Output (`data/`) |
|---|---|---|---|
| 01 markets | `pm_events.py`, `pm_combine_select.py` | Gamma `/events/keyset` (events with their markets and tags), split by event start date into 48 chains walked in parallel | `pm_markets.parquet` (all markets), `pm_selected.parquet` (resolved binary, volume > 0, open ≥ `MIN_DURATION_HOURS`, default 24) |
| 02 prices | `pm_prices.py` (6 shards) | CLOB `/prices-history?interval=max&fidelity=1440` | `prices/` daily price of the first outcome |
| 03 trades | `pm_trades.py` (4 shards) | Data API `/trades`, paged backwards with `end=<ts>` (the offset cap is 10,000) | `trades_daily/` per market-day totals; `trades_raw/` every trade for markets open ≥ 30 days |
| 04 panel | `pm_panel_regress.py` | the three above | `pm_panel.parquet`, `results/pm_brier_volume_regressions.csv`, `results/pm_category_mix.csv`, `results/pm_by_category.csv` |
| site tables | `pm_kshape.py` | the three above | `kshape/` Kalshi-shaped tables for the Kalshi analysis scripts (results in `results/`) |

Every step saves progress as it goes. If a job hits the 12-hour limit or fails, submit
the same `.slurm` file again (`sbatch slurm/02_prices.slurm` from this folder); finished parts are skipped. Run 04 once 02 and 03 are complete.
Requests that keep failing are retried for about 12 minutes; a Gamma page that keeps failing
is retried with smaller page sizes; a market that keeps failing in 02/03 is skipped, tried again
at the end, and otherwise left for the next submission (the log says how many).

Rate limits (Polymarket docs): Gamma 400 req/s, CLOB prices 100 req/s, Data API trades
20 req/s (enforced with 429s, shared by all cluster nodes). The jobs use up to 30, 84 and 18 req/s.
02 and 03 fetch the longest-lived markets first. With ~1.4M selected markets, 02 takes ~5 hours
and 03 about a day, so `submit_all.sh` queues 2 runs of 02 and 3 runs of 03 back to back.

Checks done on test markets: summed trade `size` matches Gamma's `volumeNum` (ratio 1.000
over 24 markets); daily prices cover each market's full life.

Not available from the APIs: order-book history, historical reward settings, and trades before
30 Sep 2023 (including the 2020–2022 AMM era, which would need on-chain data). The analyses use only
markets that started on or after that date (`TRADES_FROM` in `scripts/pm_common.py`).
