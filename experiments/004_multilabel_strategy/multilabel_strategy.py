"""E1.3: 多标签策略对比 — BR / CC / LP."""
from pathlib import Path
import sys, time
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))

from tqdm import tqdm
import numpy as np
from _common import load_dataset, get_model, get_feature, save_results

OUT = HERE / "results"
DATASETS = {"ohsumed": {"min_df": 10, "max_samples": 10000}, "pml": {}}
FEATURE = "tfidf"
MODEL = "lr"


def run_strategy(ds, strategy, cv=3):
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.model_selection import KFold
    from sklearn.metrics import f1_score
    import copy

    feat_cls = get_feature(FEATURE)
    X = feat_cls().fit_transform(ds.texts())
    y = ds.labels().toarray() if hasattr(ds.labels(), "toarray") else ds.labels()
    base = get_model(MODEL)()
    t0 = time.time()
    fold_scores = []
    for tr_idx, te_idx in tqdm(KFold(cv, shuffle=True, random_state=42).split(X),
                                desc=f"  {strategy}", unit="fold", leave=False, total=cv):
        if strategy == "br":
            clf = OneVsRestClassifier(copy.deepcopy(base), n_jobs=-1)
        elif strategy == "cc":
            from sklearn.multioutput import ClassifierChain
            clf = ClassifierChain(copy.deepcopy(base), order="random", random_state=42, cv=3)
        elif strategy == "lp":
            clf = OneVsRestClassifier(copy.deepcopy(base), n_jobs=-1)
        clf.fit(X[tr_idx], y[tr_idx])
        y_pred = clf.predict(X[te_idx])
        fold_scores.append(f1_score(y[te_idx], y_pred, average="macro", zero_division=0))
    return {"dataset": ds.name, "feature": FEATURE, "model": MODEL,
            "strategy": strategy, "f1_macro": round(np.mean(fold_scores), 4),
            "f1_macro_std": round(np.std(fold_scores), 4),
            "train_time_s": round(time.time() - t0, 2),
            "n_samples": len(ds), "n_labels": ds.n_labels}


if __name__ == "__main__":
    rows = []
    for ds_name, ds_kw in tqdm(DATASETS.items(), desc="E1.3 dataset", unit="ds"):
        ds = load_dataset(ds_name, **ds_kw)
        print(f"  {ds_name}: {len(ds)} docs, {ds.n_labels} labels")
        for strat in tqdm(["br", "cc", "lp"], desc=f"  {ds_name} strat", unit="s", leave=False):
            try:
                r = run_strategy(ds, strat)
                rows.append(r)
                print(f"    {strat} f1={r['f1_macro']:.4f}  {r['train_time_s']}s")
            except Exception as e:
                print(f"    {strat} ERROR: {e}")
    save_results(rows, OUT / "multilabel_strategy.csv")
