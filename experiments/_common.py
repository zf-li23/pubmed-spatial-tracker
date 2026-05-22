"""Shared experiment utilities."""
import csv, sys, time, os, json
from pathlib import Path
from datetime import datetime

import numpy as np

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# ── Path setup ──
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SRC = REPO / "src"
sys.path.insert(0, str(REPO))  # repo root


def load_dataset(name, **kwargs):
    """Load a dataset by short name. Kwargs passed to loader."""
    from src.datasets.ohsumed import OHSUMEDLoader
    from src.datasets.pubmed_multilabel import PMLLoader
    from src.datasets.pgb import PGBLoader
    from src.config import OHSUMED_PATH, PML_PATH, PGB_DIR

    registry = {
        "ohsumed":  lambda: OHSUMEDLoader(str(OHSUMED_PATH), **kwargs),
        "pml":      lambda: PMLLoader(str(PML_PATH), **kwargs),
        "pgb":      lambda: PGBLoader(str(PGB_DIR), **kwargs),
    }
    return registry[name]()


def get_model(name):
    """Return constructor for a model by short name."""
    from src.models.classical import MODELS as cls_models
    from src.models.ensemble import MODELS as ens_models

    all_models = {**cls_models, **ens_models}
    if name not in all_models:
        raise ValueError(f"Unknown model: {name}, options: {list(all_models.keys())}")
    return all_models[name]


def get_feature(name):
    """Return feature extractor class by short name."""
    from src.features.tfidf import TFIDFExtractor
    from src.features.biobert import BioBERTExtractor
    from src.features.lda_features import LDAExtractor
    registry = {
        "tfidf": TFIDFExtractor,
        "biobert": BioBERTExtractor,
        "lda": LDAExtractor,
    }
    if name not in registry:
        raise ValueError(f"Unknown feature: {name}")
    return registry[name]


def save_results(rows, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    all_keys = set()
    for r in rows:
        all_keys.update(r.keys())
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted(all_keys))
        w.writeheader()
        w.writerows(rows)
    print(f"  -> saved {len(rows)} rows to {path}")


def run_cv(ds, feat_name, model_fn, cv=5):
    feat_cls = get_feature(feat_name)
    X = feat_cls().fit_transform(ds.texts())
    y = ds.labels()
    if hasattr(y, "toarray"):
        y = y.toarray()

    if ds.name == "pgb":
        y = y.argmax(axis=1) if y.ndim > 1 and y.shape[1] > 1 else y

    is_ml = ds.task_type == "multilabel" and ds.name != "pgb"
    base = model_fn()
    n_jobs = 1 if feat_name == "biobert" else -1

    from sklearn.model_selection import KFold, StratifiedKFold
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.metrics import f1_score
    from sklearn.metrics import accuracy_score
    from joblib import Parallel, delayed
    from tqdm import tqdm
    import copy

    if is_ml or ds.name == "pgb":
        fold_idx = KFold(n_splits=cv, shuffle=True, random_state=42)
    else:
        strat = y.argmax(axis=1) if y.ndim > 1 else y
        fold_idx = StratifiedKFold(n_splits=cv, shuffle=True, random_state=42)

    splits = list(fold_idx.split(X, y))

    def _eval_fold(tr_idx, te_idx):
        X_tr, X_te = X[tr_idx], X[te_idx]
        y_tr, y_te = y[tr_idx], y[te_idx]
        clf = OneVsRestClassifier(copy.deepcopy(base)) if is_ml else copy.deepcopy(base)
        clf.fit(X_tr, y_tr)
        y_pred = clf.predict(X_te)
        return {
            "f1_macro": f1_score(y_te, y_pred, average="macro", zero_division=0),
            "f1_weighted": f1_score(y_te, y_pred, average="weighted", zero_division=0),
            "accuracy": accuracy_score(y_te, y_pred),
            "f1_samples": f1_score(y_te, y_pred, average="samples", zero_division=0)
            if is_ml else None,
        }

    t0 = time.time()
    fold_results = Parallel(n_jobs=n_jobs)(
        delayed(_eval_fold)(tr, te)
        for tr, te in tqdm(splits, desc="CV", unit="fold", leave=False)
    )
    train_time = time.time() - t0

    scoring_list = ("f1_macro", "f1_weighted", "accuracy") if not is_ml else \
                   ("f1_macro", "f1_samples", "f1_micro")
    res = {
        "dataset": ds.name, "feature": feat_name,
        "n_samples": len(ds), "n_labels": ds.n_labels,
        "train_time_s": round(train_time, 2),
    }
    for metric in scoring_list:
        vals = [fr[metric] for fr in fold_results if fr.get(metric) is not None]
        if vals:
            res[metric] = round(np.mean(vals), 4)
            res[f"{metric}_std"] = round(np.std(vals), 4)
    return res
    for metric in scoring:
        if isinstance(metric, str):
            res[metric] = round(scores[f"test_{metric}"].mean(), 4)
            res[f"{metric}_std"] = round(scores[f"test_{metric}"].std(), 4)
    return res
