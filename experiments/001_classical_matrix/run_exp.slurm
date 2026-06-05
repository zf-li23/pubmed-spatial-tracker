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
#       sbatch run_exp.slurm pml tfidf lr                              (子集)
SUFFIX="${4:-slurm}"
DATASETS="${1:-}"
FEATURES="${2:-}"
MODELS="${3:-}"
CMD="python -u classical_matrix.py"
[ -n "$DATASETS" ] && CMD="$CMD --datasets $DATASETS"
[ -n "$FEATURES" ] && CMD="$CMD --features $FEATURES"
[ -n "$MODELS" ]   && CMD="$CMD --models $MODELS"
CMD="$CMD --out-suffix $SUFFIX"
eval $CMD
