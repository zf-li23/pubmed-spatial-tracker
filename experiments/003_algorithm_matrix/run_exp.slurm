#!/bin/bash
#SBATCH --job-name=pmt-003
#SBATCH --output=slurm_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=04:00:00

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate zf-li23
cd $HOME/pubmed-spatial-tracker/experiments/003_algorithm_matrix
python -u algorithm_matrix.py
