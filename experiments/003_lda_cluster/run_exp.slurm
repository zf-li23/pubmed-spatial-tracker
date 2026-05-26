#!/bin/bash
#SBATCH --job-name=pmt-003
#SBATCH --output=slurm_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=01:00:00

source $HOME/miniconda3/etc/profile.d/conda.sh
conda activate zf-li23
cd $HOME/zf-li23/pubmed-tracker/experiments/003_lda_cluster
python -u lda_cluster.py
