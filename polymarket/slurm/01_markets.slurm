#!/bin/bash
#SBATCH --partition=general
#SBATCH --output=slurm/logs/%x_%A_%a.out
#SBATCH --error=slurm/logs/%x_%A_%a.err
#SBATCH --job-name=pm01_markets
#SBATCH --cpus-per-task=2
#SBATCH --mem=64G
#SBATCH --time=12:00:00

# Snapshot every Polymarket event + market (Gamma keyset API, 48 chains in parallel), then build
# data/pm_markets.parquet and data/pm_selected.parquet (resolved binary markets,
# volume > 0, open >= MIN_DURATION_HOURS, default 24).
# Resumable: if it hits the time limit, submit it again and it continues.
set -euo pipefail
source "${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}"
conda activate "${CONDA_ENV:-long-term-markets}"
cd "$SLURM_SUBMIT_DIR/scripts"     # submitted from polymarket/
python -u pm_events.py --workers 32
python -u pm_combine_select.py
