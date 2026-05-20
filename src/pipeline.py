"""Experiment pipeline: run a single (dataset, feature, model) combination."""

import time
import numpy as np
from sklearn.multiclass import OneVsRestClassifier
from sklearn.model_selection import cross_val_score

from .datasets.base import BiomedDataset
from .features.tfidf import TFIDFExtractor
from .features.biobert import BioBERTExtractor
from .features.lda_features import LDAExtractor
from .evaluation.metrics import eval_multilabel
from .evaluation.report import ExpLogger


FEATURE_REGISTRY = {
    "tfidf": TFIDFExtractor,
    "biobert": BioBERTExtractor,
    "lda": LDAExtractor,
}

logger = ExpLogger()


def _get_features(ds: BiomedDataset, feat_name: str):
    """Extract features. Meta features are appended if available."""
    texts = ds.texts()
    if feat_name not in FEATURE_REGISTRY:
        raise ValueError(f"Unknown feature: {feat_name}")
    extractor = FEATURE_REGISTRY[feat_name]()
    X = extractor.fit_transform(texts)

    meta = ds.metadata()
    if meta is not None:
        import scipy.sparse as sp
        if sp.issparse(X):
            X = np.hstack([X.toarray(), meta])
        else:
            X = np.hstack([X, meta])
    return X


def run_experiment(ds: BiomedDataset, feat: str, model_fn, model_name: str,
                   cv: int = 5, seed: int = 42):
    """Run one (dataset, feature, model) combo with CV."""
    print(f"  [{ds.name}] feat={feat} model={model_name}")
    X = _get_features(ds, feat)
    y = ds.labels()

    if ds.name == "pgb":
        y = y.argmax(axis=1) if y.shape[1] > 1 else y

    is_multilabel = ds.task_type == "multilabel" and ds.name != "pgb"
    clf = OneVsRestClassifier(model_fn()) if is_multilabel else model_fn()

    scores = cross_val_score(clf, X, y, cv=cv, scoring="f1_macro",
                             n_jobs=1 if feat == "biobert" else -1)
    t0 = time.time()
    clf.fit(X, y)
    train_time = time.time() - t0

    result = {
        "dataset": ds.name,
        "feature": feat,
        "model": model_name,
        "f1_macro_mean": scores.mean(),
        "f1_macro_std": scores.std(),
        "train_time_s": round(train_time, 2),
        "n_samples": len(ds),
        "n_labels": ds.n_labels,
    }
    logger.log(**result)
    return result


def run_all(datasets: list, feature_list: list, model_registry: dict, cv: int = 5):
    """Run full experiment matrix."""
    results = []
    for ds in datasets:
        for feat in feature_list:
            for name, fn in model_registry.items():
                # skip biobert for lda (incompatible feature space)
                if feat == "lda" and name in ("svm", "rf", "xgb", "ada"):
                    continue
                r = run_experiment(ds, feat, fn, name, cv=cv)
                results.append(r)
    logger.close()
    return results
