#!/bin/bash
#SBATCH --job-name=pmt-002
#SBATCH --output=slurm_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=02:00:00

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate zf-li23
cd $HOME/pubmed-spatial-tracker/experiments/002_feature_compare
python -u feature_compare.py
