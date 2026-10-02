#!/bin/bash
#SBATCH --job-name=kalshi_extract
#SBATCH --partition=general
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --time=4:00:00
#SBATCH --output=slurm/logs/%x_%A_%a.out
#SBATCH --error=slurm/logs/%x_%A_%a.err

# Stream one archived dump file from gs://prophet-kalshi-archive (public, no
# credentials) and write its parquet aggregate. One array task per file listed
# in slurm/tasks/$KIND.txt; tasks whose output already exists are skipped.
#
# Submit:
#   KIND=markets sbatch --array=1-6  --export=ALL slurm/extract.slurm
#   KIND=candles sbatch --array=1-47 --export=ALL slurm/extract.slurm
#   KIND=trades  sbatch --array=1-14 --export=ALL slurm/extract.slurm

set -euo pipefail
source "${CONDA_SH:-$HOME/miniconda3/etc/profile.d/conda.sh}"
conda activate "${CONDA_ENV:-long-term-markets}"

ROOT=$SLURM_SUBMIT_DIR     # submitted from kalshi/
cd "$ROOT/scripts"

FILE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "$ROOT/slurm/tasks/${KIND}.txt")
STEM=${FILE/.sql.gz./_}
case "$KIND" in
    markets) OUT_DIR=$ROOT/data/markets;       DONE=$OUT_DIR/${STEM}_mve.parquet; SCRIPT=extract_markets.py ;;
    candles) OUT_DIR=$ROOT/data/candles_daily; DONE=$OUT_DIR/${STEM}.parquet;     SCRIPT=extract_candles.py ;;
    trades)  OUT_DIR=$ROOT/data/trades_daily;  DONE=$OUT_DIR/${STEM}.parquet;     SCRIPT=extract_trades.py ;;
    *) echo "unknown KIND=$KIND"; exit 1 ;;
esac

if [ -e "$DONE" ]; then
    echo "skip $FILE (output exists)"; exit 0
fi
echo "== $KIND task $SLURM_ARRAY_TASK_ID: $FILE on $(hostname) at $(date -u) =="
time python3 -u "$SCRIPT" "$FILE" "$OUT_DIR"
