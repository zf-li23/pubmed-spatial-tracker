#!/bin/bash
# 006 — Spatial Tracker: BioBERT+MLP fine-tune (GPU)
#SBATCH --job-name=pmt-006-gpu
#SBATCH --output=slurm_gpu_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --time=48:00:00

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate biobert_env
cd $HOME/zf-li23/pubmed-tracker/experiments/006_st_benchmark
python -u st_benchmark.py --methods biobert_mlp
