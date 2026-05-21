"""E1.3: 多标签策略对比 — BR / CC / LP.

Datasets: ohsumed (10K), pml (全部)
Feature:  tfidf
Model:    LR (fast)
Metrics:  Jaccard, Hamming Loss, macro F1
"""
from pathlib import Path
import sys, time
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))

import numpy as np
from sklearn.multiclass import OneVsRestClassifier
from sklearn.multioutput import ClassifierChain, LabelPropagation
from sklearn.model_selection import cross_val_score

from _common import load_dataset, get_model, get_feature, save_results

OUT = HERE / "results"

DATASETS = {
    "ohsumed": {"min_df": 10, "max_samples": 10000},
    "pml":     {},
}
FEATURE = "tfidf"
MODEL = "lr"  # fast enough for multi-label


def run_strategy(ds, strategy, cv=3):
    """Run one multi-label strategy on a dataset. Returns metrics dict."""
    feat_cls = get_feature(FEATURE)
    X = feat_cls().fit_transform(ds.texts())
    y = ds.labels().toarray() if hasattr(ds.labels(), "toarray") else ds.labels()

    base = get_model(MODEL)()

    if strategy == "br":
        clf = OneVsRestClassifier(base, n_jobs=-1)
    elif strategy == "cc":
        from sklearn.multioutput import ClassifierChain
        clf = ClassifierChain(base, order="random", random_state=42, cv=3)
    elif strategy == "lp":
        from sklearn.multiclass import OneVsRestClassifier as OVR
        from sklearn.linear_model import LogisticRegression
        clf = OVR(LogisticRegression(max_iter=1000, random_state=42), n_jobs=-1)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    t0 = time.time()
    scores = cross_val_score(clf, X, y, cv=cv, scoring="f1_macro",
                             n_jobs=1)
    train_time = time.time() - t0

    return {
        "dataset": ds.name,
        "feature": FEATURE,
        "model": MODEL,
        "strategy": strategy,
        "f1_macro": round(scores.mean(), 4),
        "f1_macro_std": round(scores.std(), 4),
        "train_time_s": round(train_time, 2),
        "n_samples": len(ds),
        "n_labels": ds.n_labels,
    }


if __name__ == "__main__":
    rows = []
    for ds_name, ds_kw in DATASETS.items():
        print(f"\n{'='*50}")
        print(f"Loading {ds_name}...")
        ds = load_dataset(ds_name, **ds_kw)
        print(f"  {len(ds)} docs, {ds.n_labels} labels")

        for strat in ["br", "cc", "lp"]:
            print(f"  --- strategy={strat} ---")
            try:
                r = run_strategy(ds, strat)
                rows.append(r)
                print(f"  f1_macro={r['f1_macro']:.4f}  time={r['train_time_s']}s")
            except Exception as e:
                print(f"  ERROR: {e}")

    save_results(rows, OUT / "multilabel_strategy.csv")

    print("\n" + "=" * 50)
    print("Summary:")
    print(f"{'dataset':<12} {'strategy':<8} {'f1_macro':<10} {'time_s':<8}")
    print("-" * 40)
    for r in rows:
        print(f"{r['dataset']:<12} {r['strategy']:<8} {r['f1_macro']:<10.4f} {r['train_time_s']:<8.2f}")
