#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
mkdir -p results
python3 multilabel_strategy.py
echo "Done. 结果见 results/"