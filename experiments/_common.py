"""Shared experiment utilities."""
import csv, sys, time, os, json
from pathlib import Path
from datetime import datetime

import numpy as np

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
    """Write list-of-dicts to CSV."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        return
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"  -> saved {len(rows)} rows to {path}")


def run_cv(ds, feat_name, model_fn, cv=5):
    """Run one CV experiment. Returns metrics dict."""
    from sklearn.multiclass import OneVsRestClassifier
    from sklearn.model_selection import cross_validate

    feat_cls = get_feature(feat_name)
    X = feat_cls().fit_transform(ds.texts())
    y = ds.labels()

    # PGB: 3-class single-label
    if ds.name == "pgb":
        y = y.argmax(axis=1) if y.ndim > 1 and y.shape[1] > 1 else y

    is_ml = ds.task_type == "multilabel" and ds.name != "pgb"
    clf = OneVsRestClassifier(model_fn()) if is_ml else model_fn()

    scoring = ("f1_macro", "f1_weighted", "accuracy") if not is_ml else \
              ("f1_macro", "f1_samples", "f1_micro")
    t0 = time.time()
    scores = cross_validate(clf, X, y, cv=cv, scoring=scoring, n_jobs=1 if feat_name == "biobert" else -1,
                            return_train_score=False)
    train_time = time.time() - t0

    res = {
        "dataset": ds.name, "feature": feat_name,
        "n_samples": len(ds), "n_labels": ds.n_labels,
        "train_time_s": round(train_time, 2),
    }
    for metric in scoring:
        if isinstance(metric, str):
            res[metric] = round(scores[f"test_{metric}"].mean(), 4)
            res[f"{metric}_std"] = round(scores[f"test_{metric}"].std(), 4)
    return res
