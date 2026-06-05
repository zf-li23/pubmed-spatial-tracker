#!/usr/bin/env bash
# 005_graph_models — 本地复现（PGB 子集，1 模型）
# 完整复现请改用 sbatch run_exp.slurm
set -e
cd "$(dirname "$0")"
mkdir -p results
echo "=== 005 本地快速测试 (Node2Vec+LR, 2-fold) ==="
python3 -c "
import sys; sys.path.insert(0, '.'); sys.path.insert(0, '..')
from _common import load_dataset, get_cached_features, get_model
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import f1_score, accuracy_score
import numpy as np, time

ds = load_dataset('pgb', build_graph=True, max_samples=500)
X = get_cached_features(ds, 'node2vec', {'build_graph': True, 'max_samples': 500})[0]
y = ds.labels().argmax(axis=1)
clf = get_model('lr')()
splits = StratifiedKFold(2, shuffle=True, random_state=42).split(X, y)
for tr, te in splits:
    clf.fit(X[tr], y[tr]); p = clf.predict(X[te])
    print(f'  LR F1={f1_score(y[te], p, average=\"macro\"):.4f}')
"
echo "Done."
