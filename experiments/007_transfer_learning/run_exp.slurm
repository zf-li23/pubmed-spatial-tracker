#!/bin/bash
#SBATCH --job-name=pmt-007
#SBATCH --output=slurm_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=48:00:00

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate pubmed-tracker
cd $HOME/zf-li23/pubmed-tracker/experiments/007_transfer_learning

# 用法：sbatch run_exp.slurm                                          (CPU: A1,A2,A4,A5,B1,B3,D1,D2)
#       sbatch --gres=gpu:1 run_exp.slurm --exps B2,C1,C2 --out-suffix gpu  (GPU)
EXPS="${1:-A1,A2,A4,A5,B1,B3,D1,D2}"
SUFFIX="${2:-slurm}"
python -u transfer_learning.py --exps "$EXPS" --out-suffix "$SUFFIX"
