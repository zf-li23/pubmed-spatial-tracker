"""006 — Spatial Tracker: 3 Methods Comparison

Compares three approaches on the Spatial Tracker dataset (9,148 articles,
6 single-label categories):

  1. TF-IDF + SVM          — Classical text classification baseline
  2. BioBERT + LR          — Frozen BioBERT embeddings + logistic regression
  3. BioBERT+MLP fine-tune — End-to-end fine-tuning (requires GPU)

Usage:
    # Method 1 & 2 (CPU, fast)
    python st_benchmark.py --methods tfidf_svm,biobert_lr

    # Method 3 (GPU, slow)
    python st_benchmark.py --methods biobert_mlp

    # All three
    python st_benchmark.py
"""
from pathlib import Path
import sys, time, argparse
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))

import numpy as np
from tqdm import tqdm
from _common import load_dataset, save_results, get_cached_features

OUT = HERE / "results"

CV = 5


def run_tfidf_svm(ds, cv=CV):
    """TF-IDF features + SVM (RBF kernel)."""
    from sklearn.model_selection import StratifiedKFold
    from sklearn.svm import SVC
    from sklearn.metrics import f1_score, accuracy_score

    X = get_cached_features(ds, "tfidf", {"max_samples": None})[0]
    if hasattr(X, "toarray"):
        X = X.toarray()
    y = ds.labels().argmax(axis=1)

    splits = list(StratifiedKFold(cv, shuffle=True, random_state=42).split(X, y))
    t0 = time.time()
    scores = []
    for tr, te in tqdm(splits, desc="  TF-IDF+SVM", unit="fold", leave=False):
        clf = SVC(kernel="rbf", random_state=42)
        clf.fit(X[tr], y[tr])
        y_pred = clf.predict(X[te])
        scores.append({
            "f1_macro": f1_score(y[te], y_pred, average="macro", zero_division=0),
            "accuracy": accuracy_score(y[te], y_pred),
        })
    elapsed = time.time() - t0
    res = {"dataset": ds.name, "method": "TF-IDF+SVM",
           "n_samples": len(ds), "n_labels": ds.n_labels,
           "train_time_s": round(elapsed, 2)}
    for m in scores[0]:
        vals = [s[m] for s in scores]
        res[m] = round(np.mean(vals), 4)
        res[f"{m}_std"] = round(np.std(vals), 4)
    return res


def run_biobert_lr(ds, cv=CV):
    """Frozen BioBERT embeddings + Logistic Regression."""
    from sklearn.model_selection import StratifiedKFold
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import f1_score, accuracy_score

    X = get_cached_features(ds, "biobert", {"max_samples": None})[0]
    y = ds.labels().argmax(axis=1)

    splits = list(StratifiedKFold(cv, shuffle=True, random_state=42).split(X, y))
    t0 = time.time()
    scores = []
    for tr, te in tqdm(splits, desc="  BioBERT+LR", unit="fold", leave=False):
        clf = LogisticRegression(max_iter=1000, random_state=42)
        clf.fit(X[tr], y[tr])
        y_pred = clf.predict(X[te])
        scores.append({
            "f1_macro": f1_score(y[te], y_pred, average="macro", zero_division=0),
            "accuracy": accuracy_score(y[te], y_pred),
        })
    elapsed = time.time() - t0
    res = {"dataset": ds.name, "method": "BioBERT+LR",
           "n_samples": len(ds), "n_labels": ds.n_labels,
           "train_time_s": round(elapsed, 2)}
    for m in scores[0]:
        vals = [s[m] for s in scores]
        res[m] = round(np.mean(vals), 4)
        res[f"{m}_std"] = round(np.std(vals), 4)
    return res


def run_biobert_mlp(ds, cv=3):
    """End-to-end BioBERT fine-tuning with MLP head (requires GPU)."""
    from src.models.deep import BioBERTFineTuner
    from sklearn.model_selection import StratifiedKFold
    from sklearn.metrics import f1_score, accuracy_score

    texts = ds.texts()
    y = ds.labels().argmax(axis=1)
    n_classes = ds.n_labels

    splits = list(StratifiedKFold(cv, shuffle=True, random_state=42).split(texts, y))
    t0 = time.time()
    scores = []
    for fold_i, (tr, te) in enumerate(
        tqdm(splits, desc="  BioBERT+MLP", unit="fold", leave=False), 1
    ):
        texts_tr = [texts[i] for i in tr]
        texts_te = [texts[i] for i in te]
        y_tr = y[tr]
        y_te = y[te]

        tuner = BioBERTFineTuner(n_labels=n_classes, epochs=3, batch_size=16,
                                 multilabel=False)
        tuner.fit(texts_tr, y_tr)
        y_pred = tuner.predict(texts_te)
        scores.append({
            "f1_macro": f1_score(y_te, y_pred, average="macro", zero_division=0),
            "accuracy": accuracy_score(y_te, y_pred),
        })

    elapsed = time.time() - t0
    res = {"dataset": ds.name, "method": "BioBERT+MLP",
           "n_samples": len(ds), "n_labels": ds.n_labels,
           "train_time_s": round(elapsed, 2)}
    for m in scores[0]:
        vals = [s[m] for s in scores]
        res[m] = round(np.mean(vals), 4)
        res[f"{m}_std"] = round(np.std(vals), 4)
    return res


METHODS = {
    "tfidf_svm": run_tfidf_svm,
    "biobert_lr": run_biobert_lr,
    "biobert_mlp": run_biobert_mlp,
}

if __name__ == "__main__":
    p = argparse.ArgumentParser(description="006 — Spatial Tracker Benchmark")
    p.add_argument("--methods", type=str, default="tfidf_svm,biobert_lr,biobert_mlp",
                   help="Comma-separated methods")
    args = p.parse_args()

    method_list = args.methods.split(",")
    for m in method_list:
        if m not in METHODS:
            raise ValueError(f"Unknown method: {m}. Options: {list(METHODS)}")

    print(f"006 — Spatial Tracker Benchmark")
    print(f"  methods: {method_list}")
    print()

    ds = load_dataset("st")
    print(f"Dataset: {ds.name} — {len(ds)} docs, {ds.n_labels} labels")
    print(f"  Label distribution:")
    labels = ds.labels().argmax(axis=1)
    for i, name in enumerate(ds.label_names):
        print(f"    {name}: {(labels == i).sum()}")

    rows = []
    for method in method_list:
        print(f"\n{'='*50}")
        print(f"  Method: {method}")
        print(f"{'='*50}")
        try:
            r = METHODS[method](ds)
            rows.append(r)
            print(f"  f1_macro={r['f1_macro']:.4f}  accuracy={r['accuracy']:.4f}  "
                  f"time={r['train_time_s']:.1f}s")
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback; traceback.print_exc()

    OUT.mkdir(parents=True, exist_ok=True)
    save_results(rows, OUT / "st_benchmark.csv")
    print(f"\n✅ 006 done — {len(rows)} results")
