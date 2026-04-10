#!/bin/bash
set -e

echo "⚠️  注意: 推荐使用 'make run' 命令来替代本脚本！"
echo "=> 正在转发至 'make run'..."
make run -C "$(dirname "$0")"
