#!/bin/bash
#SBATCH --job-name=pmt-002
#SBATCH --output=slurm_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --time=48:00:00

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate pubmed-tracker
cd $HOME/zf-li23/pubmed-tracker/experiments/002_biobert_mlp
# Force CPU until PyTorch CUDA compat is fixed
CUDA_VISIBLE_DEVICES="" python -u biobert_mlp.py
