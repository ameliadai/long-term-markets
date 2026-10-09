#!/bin/bash
#SBATCH --job-name=kalshi_analysis
#SBATCH --partition=general
#SBATCH --cpus-per-task=2
#SBATCH --mem=128G
#SBATCH --time=8:00:00
#SBATCH --output=slurm/logs/%x_%j.out
#SBATCH --error=slurm/logs/%x_%j.err

# Run one analysis script from kalshi/scripts. Submit from kalshi/:
#   SCRIPT=a13_reward_event_study.py sbatch --export=ALL slurm/analysis.slurm
# Extra arguments for the script go in ARGS. Set PYTHON to a python executable to skip conda.

set -euo pipefail
if [ -z "${PYTHON:-}" ]; then
  source "${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}"
  conda activate "${CONDA_ENV:-long-term-markets}"
  PYTHON=python
fi
cd "$SLURM_SUBMIT_DIR/scripts"
time "$PYTHON" -u "$SCRIPT" ${ARGS:-}
