#!/bin/bash
#SBATCH --job-name=pmt-007-cpu
#SBATCH --output=slurm_cpu_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=48:00:00
#SBATCH --partition=Yangxrlab

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate pubmed-tracker
cd $HOME/zf-li23/pubmed-tracker/experiments/007_transfer_learning

echo "=== CPU experiments ==="
echo "  A1 A2 A3 A4 A5 B1 B3 C3 C4 D1 D2 D3 D4"

python -u transfer_learning.py \
  --exps A1,A2,A3,A4,A5,B1,B3,C3,C4,D1,D2,D3,D4 \
  --out-suffix cpu
