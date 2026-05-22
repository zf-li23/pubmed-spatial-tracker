#!/bin/bash
#SBATCH --job-name=pmt-002
#SBATCH --output=slurm_%j.log
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=01:00:00

PY=$HOME/miniconda3/envs/pubmed-tracker/bin/python
cd $HOME/zf-li23/pubmed-tracker/experiments/002_feature_compare
$PY -u feature_compare.py
