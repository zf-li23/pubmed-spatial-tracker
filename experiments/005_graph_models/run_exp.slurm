#!/bin/bash
#SBATCH --job-name=pmt-005
#SBATCH --output=slurm_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --gres=gpu:1
#SBATCH --time=04:00:00

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate zf-li23
cd $HOME/pubmed-spatial-tracker/experiments/005_graph_models
python -u graph_models.py
