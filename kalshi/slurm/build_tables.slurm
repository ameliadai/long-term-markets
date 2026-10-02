#!/bin/bash
#SBATCH --job-name=kalshi_build
#SBATCH --partition=general
#SBATCH --cpus-per-task=2
#SBATCH --mem=96G
#SBATCH --time=2:00:00
#SBATCH --output=slurm/logs/%x_%j.out
#SBATCH --error=slurm/logs/%x_%j.err

# Combine the extracted parts into data/markets.parquet, data/mve_summary.parquet,
# data/candles_daily.parquet and data/trades_daily.parquet.
# Submit after the three extract arrays succeed:
#   sbatch --dependency=afterok:<markets>:<candles>:<trades> slurm/build_tables.slurm

set -euo pipefail
source "${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}"
conda activate "${CONDA_ENV:-long-term-markets}"
cd "$SLURM_SUBMIT_DIR/scripts"     # submitted from kalshi/
time python3 -u build_tables.py
