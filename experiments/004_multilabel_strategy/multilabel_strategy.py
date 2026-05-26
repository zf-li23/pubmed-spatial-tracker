"""004 — Multi-label Strategy: BR / CC / LP

Compares Binary Relevance, Classifier Chain, and Label Powerset
on multi-label biomedical datasets.  PGB is excluded because it is
treated as 3-class single-label (argmax) in our pipeline.

Grid:
    OHSUMED (10K, ~1.6K labels) × [BR, CC, LP] × TF-IDF × LR
    PML     (10K, 16 labels)    × [BR, CC, LP] × TF-IDF × LR
    = 6 runs

Uses feature cache (shares TF-IDF with 001).
"""
from pathlib import Path
import sys, time
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))

import numpy as np
from tqdm import tqdm
from _common import load_dataset, get_model, save_results, get_cached_features

OUT = HERE / "results"

DATASETS = {
    "ohsumed": {"min_df": 10, "max_samples": 10000},
    "pml":     {},
}

FEATURE = "tfidf"
MODEL = "lr"
CV = 5
STRATEGIES = ["br", "cc", "lp"]


def run_strategy(ds, ds_kwargs, strategy, cv=CV):
    """Run one multi-label strategy using cached TF-IDF features."""
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.multioutput import ClassifierChain
    from sklearn.model_selection import KFold
    from sklearn.metrics import f1_score
    from joblib import Parallel, delayed
    import copy

    X, y = get_cached_features(ds, FEATURE, ds_kwargs)
    if hasattr(y, "toarray"):
        y = y.toarray()

    base = get_model(MODEL)()
    t0 = time.time()
    splits = list(KFold(cv, shuffle=True, random_state=42).split(X))

    def _fold(tr_idx, te_idx):
        if strategy == "cc":
            clf = ClassifierChain(copy.deepcopy(base), order="random",
                                  random_state=42)
        elif strategy == "lp":
            clf = OneVsRestClassifier(copy.deepcopy(base), n_jobs=-1)
        else:  # br
            clf = OneVsRestClassifier(copy.deepcopy(base), n_jobs=-1)

        clf.fit(X[tr_idx], y[tr_idx])
        y_pred = clf.predict(X[te_idx])
        return {
            "f1_macro": f1_score(y[te_idx], y_pred, average="macro", zero_division=0),
            "f1_micro": f1_score(y[te_idx], y_pred, average="micro", zero_division=0),
            "f1_samples": f1_score(y[te_idx], y_pred, average="samples", zero_division=0),
        }

    fold_results = Parallel(n_jobs=-1)(
        delayed(_fold)(tr, te)
        for tr, te in tqdm(splits, desc=f"  {strategy}", unit="fold", leave=False)
    )

    elapsed = time.time() - t0
    res = {
        "dataset": ds.name, "feature": FEATURE, "model": MODEL,
        "strategy": strategy,
        "n_samples": len(ds), "n_labels": ds.n_labels,
        "train_time_s": round(elapsed, 2),
    }
    for metric in ("f1_macro", "f1_micro", "f1_samples"):
        vals = [fr[metric] for fr in fold_results]
        res[metric] = round(np.mean(vals), 4)
        res[f"{metric}_std"] = round(np.std(vals), 4)
    return res


if __name__ == "__main__":
    rows = []
    total = len(DATASETS) * len(STRATEGIES)
    pbar = tqdm(total=total, desc="004", unit="run")

    for ds_name, ds_kw in DATASETS.items():
        ds = load_dataset(ds_name, **ds_kw)
        print(f"\n{'='*50}")
        print(f"  {ds_name}: {len(ds)} docs, {ds.n_labels} labels")
        print(f"{'='*50}")

        for strat in STRATEGIES:
            pbar.set_description(f"004 {ds_name}/{strat}")
            try:
                r = run_strategy(ds, ds_kw, strat)
                rows.append(r)
                print(f"  {strat:4s}  f1_macro={r['f1_macro']:.4f}  "
                      f"f1_micro={r['f1_micro']:.4f}  time={r['train_time_s']:.1f}s")
            except Exception as e:
                print(f"  {strat:4s}  ERROR: {e}")
                import traceback; traceback.print_exc()
            pbar.update(1)

    pbar.close()
    save_results(rows, OUT / "multilabel_strategy.csv")
    print(f"\n✅ 004 done — {len(rows)} results")
