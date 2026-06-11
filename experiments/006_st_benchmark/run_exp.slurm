#!/bin/bash
#SBATCH --job-name=pmt-006
#SBATCH --output=slurm_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=48:00:00

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate pubmed-tracker
cd $HOME/zf-li23/pubmed-tracker/experiments/006_st_benchmark

# 用法：sbatch run_exp.slurm                          (CPU: TF-IDF+SVM + BioBERT+LR)
#       sbatch --time=4:00:00 run_exp.slurm biobert_mlp  (BioBERT+MLP, 5-fold CPU ~30min)
METHODS="${1:-tfidf_svm,biobert_lr}"
SUFFIX="${2:-slurm}"
# Force CPU to avoid CUDA driver incompatibility (gpu01 driver too old for PyTorch 2.12)
CUDA_VISIBLE_DEVICES="" python -u st_benchmark.py --methods "$METHODS" --out-suffix "$SUFFIX"
