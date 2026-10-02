#!/bin/bash
#SBATCH --partition=general
#SBATCH --output=slurm/logs/%x_%A_%a.out
#SBATCH --error=slurm/logs/%x_%A_%a.err
#SBATCH --job-name=pm04_panel
#SBATCH --cpus-per-task=2
#SBATCH --mem=192G
#SBATCH --time=6:00:00

# Contract-day panel + Brier-on-volume regressions -> results/pm_brier_volume_regressions.csv,
# plus the category mix and per-category regressions (pm_category_mix.csv, pm_by_category.csv)
set -euo pipefail
source "${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}"
conda activate "${CONDA_ENV:-long-term-markets}"
cd "$SLURM_SUBMIT_DIR/scripts"     # submitted from polymarket/
python -u pm_panel_regress.py
