#!/usr/bin/env bash
# 007_transfer_learning — 本地复现（仅 B1 基线）
# 完整复现请：sbatch run_exp.slurm --exps A1,A2,A4,A5,B1,B3,D1,D2  (CPU)
#              sbatch run_exp.slurm --exps B2,C1,C2                 (GPU)
set -e
cd "$(dirname "$0")"
mkdir -p results
echo "=== 007 本地快速测试 (仅 B1: ST→ST LR) ==="
python3 transfer_learning.py --exps B1 --out-suffix local
echo "Done. 结果见 results/"
