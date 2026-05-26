#!/bin/bash
#SBATCH --job-name=pmt-005
#SBATCH --output=slurm_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --time=12:00:00

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate pubmed-tracker
cd $HOME/zf-li23/pubmed-tracker/experiments/005_graph_models
python -u graph_models.py
