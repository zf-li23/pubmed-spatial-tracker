#!/bin/bash
# 006 — Spatial Tracker: TF-IDF+SVM + BioBERT+LR (CPU)
#SBATCH --job-name=pmt-006-cpu
#SBATCH --output=slurm_cpu_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=12:00:00

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate pubmed-tracker
cd $HOME/zf-li23/pubmed-tracker/experiments/006_st_benchmark
python -u st_benchmark.py --methods tfidf_svm,biobert_lr
