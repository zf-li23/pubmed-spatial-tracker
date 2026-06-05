#!/bin/bash
#SBATCH --job-name=pmt-001
#SBATCH --output=slurm_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=48:00:00

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate pubmed-tracker
cd $HOME/zf-li23/pubmed-tracker/experiments/001_classical_matrix

# 用法：sbatch run_exp.slurm                                          (全量 84 组)
#       sbatch run_exp.slurm --datasets pml --features tfidf --models lr  (子集)
DATASETS="${1:-all}"
FEATURES="${2:-all}"
MODELS="${3:-all}"
SUFFIX="${4:-slurm}"
python -u classical_matrix.py \
  ${DATASETS:+--datasets "$DATASETS"} \
  ${FEATURES:+--features "$FEATURES"} \
  ${MODELS:+--models "$MODELS"} \
  --out-suffix "$SUFFIX"
