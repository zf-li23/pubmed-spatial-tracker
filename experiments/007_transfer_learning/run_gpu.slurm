#!/bin/bash
#SBATCH --job-name=pmt-007-gpu
#SBATCH --output=slurm_gpu_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --time=48:00:00
#SBATCH --partition=Yangxrlab

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate biobert_env
cd $HOME/zf-li23/pubmed-tracker/experiments/007_transfer_learning

echo "=== GPU experiments ==="
echo "  B2 C1 C2"

python -u transfer_learning.py \
  --exps B2,C1,C2 \
  --out-suffix gpu
