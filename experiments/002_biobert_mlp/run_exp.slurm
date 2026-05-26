#!/bin/bash
#SBATCH --job-name=pmt-002
#SBATCH --output=slurm_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --gres=gpu:1
#SBATCH --time=08:00:00

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate zf-li23
cd $HOME/zf-li23/pubmed-tracker/experiments/002_biobert_mlp
python -u biobert_mlp.py
