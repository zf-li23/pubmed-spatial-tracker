#!/usr/bin/env bash
# 004_multilabel_strategy — 本地复现
set -e
cd "$(dirname "$0")"
mkdir -p results
echo "=== 004 多标签策略 (完整运行) ==="
python3 multilabel_strategy.py
echo "Done. 结果见 results/"
