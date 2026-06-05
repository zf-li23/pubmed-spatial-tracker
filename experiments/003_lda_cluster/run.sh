#!/usr/bin/env bash
# 003_lda_cluster — 本地复现（完整运行也很快）
set -e
cd "$(dirname "$0")"
mkdir -p results
echo "=== 003 LDA+聚类 (完整运行) ==="
python3 lda_cluster.py
echo "Done. 结果见 results/"
