#!/usr/bin/env bash
# 001_classical_matrix — 本地复现（小规模子集，不计成本）
# 完整复现请改用 sbatch run_exp.slurm
set -e
cd "$(dirname "$0")"
mkdir -p results
echo "=== 001 本地快速测试 (1 数据集 × 1 特征 × 1 模型 × 2-fold CV) ==="
python3 classical_matrix.py \
  --datasets pml --features tfidf --models lr --cv 2 --out-suffix local
echo "Done. 结果见 results/"
