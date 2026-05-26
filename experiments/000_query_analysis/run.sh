#!/usr/bin/env bash
# 000_query_analysis — 一键复现
set -e
cd "$(dirname "$0")"
mkdir -p results
python3 query_analysis.py
echo "Done. 结果见 results/"
