#!/bin/bash
#SBATCH --partition=general
#SBATCH --output=slurm/logs/%x_%A_%a.out
#SBATCH --error=slurm/logs/%x_%A_%a.err
#SBATCH --job-name=pm02_prices
#SBATCH --cpus-per-task=2
#SBATCH --mem=8G
#SBATCH --time=12:00:00
#SBATCH --array=0-5

# Daily price history for every selected market (CLOB /prices-history).
# 6 shards x 14 req/s = 84 req/s (API limit 100/s), 8 threads each, longest-lived markets first.
# Resumable: resubmit to continue.
set -euo pipefail
source "${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}"
conda activate "${CONDA_ENV:-long-term-markets}"
cd "$SLURM_SUBMIT_DIR/scripts"     # submitted from polymarket/
export PM_RATE=14
export PM_WORKERS=8
python -u pm_prices.py $SLURM_ARRAY_TASK_ID 6
