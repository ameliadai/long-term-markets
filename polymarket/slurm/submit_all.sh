#!/bin/bash
# Submit the Polymarket pipeline with dependencies:
#   01 markets  ->  02 prices (2 runs) + 03 trades (3 runs), in parallel  ->  04 panel + regressions
# 02 and 03 pick up from saved progress, so each extra run continues where the previous one
# hit the 12-hour limit, or exits within a minute if nothing is left.
# usage: bash submit_all.sh             whole pipeline
#        bash submit_all.sh --from-02   market list already built; start at 02
set -euo pipefail
cd "$(dirname "$0")/.."      # jobs are submitted from polymarket/
J1="-"
DEP=""
if [ "${1:-}" != "--from-02" ]; then
  J1=$(sbatch --parsable slurm/01_markets.slurm)
  DEP="--dependency=afterok:$J1"
fi
J2a=$(sbatch --parsable $DEP slurm/02_prices.slurm)
J2b=$(sbatch --parsable --dependency=afterany:$J2a slurm/02_prices.slurm)
J3a=$(sbatch --parsable $DEP slurm/03_trades.slurm)
J3b=$(sbatch --parsable --dependency=afterany:$J3a slurm/03_trades.slurm)
J3c=$(sbatch --parsable --dependency=afterany:$J3b slurm/03_trades.slurm)
J4=$(sbatch --parsable --dependency=afterok:$J2b:$J3c slurm/04_panel_regress.slurm)
echo "01 markets=$J1  02 prices=$J2a,$J2b  03 trades=$J3a,$J3b,$J3c  04 panel=$J4" | tee -a slurm/submitted_jobs.txt
