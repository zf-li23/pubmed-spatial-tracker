#!/usr/bin/env bash
# 006_st_benchmark — 本地复现（仅 TF-IDF+SVM）
# 完整复现请：sbatch run_exp.slurm --methods tfidf_svm,biobert_lr  (CPU)
#              sbatch run_exp.slurm --methods biobert_mlp           (GPU)
set -e
cd "$(dirname "$0")"
mkdir -p results
echo "=== 006 本地快速测试 (仅 TF-IDF+SVM, 2-fold) ==="
python3 st_benchmark.py --methods tfidf_svm --out-suffix local
echo "Done. 结果见 results/"
