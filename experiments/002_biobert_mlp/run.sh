#!/usr/bin/env bash
# 002_biobert_mlp — 本地复现（CPU，1 epoch，小规模）
# 完整复现请改用 sbatch run_exp.slurm（需要 GPU）
set -e
cd "$(dirname "$0")"
mkdir -p results
echo "=== 002 本地快速测试 (限定 PML, CPU, 1 epoch) ==="
# 临时修改代码中的 epochs 为 1，仅验证管线
CUDA_VISIBLE_DEVICES="" python3 -c "
import sys, os
os.environ['CUDA_VISIBLE_DEVICES'] = ''
sys.path.insert(0, '.')
sys.path.insert(0, '..')
from biobert_mlp import run_biobert_mlp
from _common import load_dataset
ds = load_dataset('pml')
# 只跑 1 fold 快速验证
r = run_biobert_mlp(ds, cv=1)
print(f'F1={r[\"f1_macro\"]:.4f}  Acc={r[\"accuracy\"]:.4f}')
"
echo "Done."
