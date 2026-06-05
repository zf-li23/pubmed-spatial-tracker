#!/usr/bin/env bash
# 000_query_analysis — 本地或集群复现
set -e
cd "$(dirname "$0")"
mkdir -p results
echo "=== 000 PubMed 查询分析 ==="
python3 query_analysis.py
echo "Done. 结果见 results/"
