#!/bin/bash
#SBATCH --partition=general
#SBATCH --output=slurm/logs/%x_%A_%a.out
#SBATCH --error=slurm/logs/%x_%A_%a.err
#SBATCH --job-name=pm03_trades
#SBATCH --cpus-per-task=2
#SBATCH --mem=48G
#SBATCH --time=12:00:00
#SBATCH --array=0-3

# Full trade history for every selected market (Data API /trades, time-cursor paging),
# saved as per-market daily totals, plus every trade for markets open >= 30 days.
# 4 shards x 4.5 req/s = 18 req/s (API limit 20/s, enforced with 429s), 4 threads each,
# longest-lived markets first. Resumable: resubmit to continue.
set -euo pipefail
source "${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}"
conda activate "${CONDA_ENV:-long-term-markets}"
cd "$SLURM_SUBMIT_DIR/scripts"     # submitted from polymarket/
export PM_RATE=4.5
export PM_WORKERS=4
python -u pm_trades.py $SLURM_ARRAY_TASK_ID 4
