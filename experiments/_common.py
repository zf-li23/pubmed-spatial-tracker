"""Shared experiment utilities with feature caching.

Cache strategy:
  Feature extraction (X matrix + y labels) is cached per (dataset, feature) pair.
  This avoids redundant BioBERT embedding / TF-IDF fitting across experiments.
  Cache is stored in experiments/_cache/ as .npz files.
"""

import csv, sys, time, os, json, hashlib
from pathlib import Path
from datetime import datetime

import numpy as np
from scipy import sparse

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

# ── Paths ──
HERE = Path(__file__).resolve().parent
REPO = HERE.parent
SRC = REPO / "src"
CACHE_DIR = HERE / "_cache"
sys.path.insert(0, str(REPO))


# ═══════════════════════════════════════════════════════════════
# Dataset / Model / Feature registry
# ═══════════════════════════════════════════════════════════════

def load_dataset(name, **kwargs):
    from src.datasets.ohsumed import OHSUMEDLoader
    from src.datasets.pubmed_multilabel import PMLLoader
    from src.datasets.pgb import PGBLoader
    from src.datasets.spatial_tracker import STLoader
    from src.config import OHSUMED_PATH, PML_PATH, PGB_DIR

    registry = {
        "ohsumed": lambda: OHSUMEDLoader(str(OHSUMED_PATH), **kwargs),
        "pml":     lambda: PMLLoader(str(PML_PATH), **kwargs),
        "pgb":     lambda: PGBLoader(str(PGB_DIR), **kwargs),
        "st":      lambda: STLoader(**kwargs),
    }
    return registry[name]()


def get_model(name):
    from src.models.classical import MODELS as cls
    from src.models.ensemble import MODELS as ens
    all_models = {**cls, **ens}
    if name not in all_models:
        raise ValueError(f"Unknown model: {name}, options: {list(all_models)}")
    return all_models[name]


def get_feature(name):
    """Return feature extractor class by short name."""
    from src.features.tfidf import TFIDFExtractor
    from src.features.biobert import BioBERTExtractor
    from src.features.lda_features import LDAExtractor
    from src.features.metadata import MetaExtractor
    from src.features.node2vec import Node2VecExtractor
    registry = {
        "tfidf":   TFIDFExtractor,
        "biobert": BioBERTExtractor,
        "lda":     LDAExtractor,
        "meta":    MetaExtractor,
        "node2vec": Node2VecExtractor,
    }
    if name not in registry:
        raise ValueError(f"Unknown feature: {name}, options: {list(registry)}")
    return registry[name]


# ═══════════════════════════════════════════════════════════════
# Feature cache
# ═══════════════════════════════════════════════════════════════

def _cache_key(ds_name, feat_name, ds_kwargs):
    """Deterministic cache key from dataset identity."""
    raw = f"{ds_name}|{feat_name}|{json.dumps(ds_kwargs, sort_keys=True, default=str)}"
    h = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"{ds_name}_{feat_name}_{h}"


def get_cached_features(ds, feat_name, ds_kwargs=None):
    """Return (X, y) for a dataset+feature pair, using disk cache.

    On first call:  compute features, save to _cache/.
    On later calls: load from _cache/ (instant).

    Special cases:
      - 'meta':     MetaExtractor needs dataset.metadata()
      - 'node2vec': Node2Vec needs PGB citation graph (build_graph=True)
    """
    if ds_kwargs is None:
        ds_kwargs = {}
    key = _cache_key(ds.name, feat_name, ds_kwargs)
    cache_path = CACHE_DIR / f"{key}.npz"

    if cache_path.exists():
        print(f"  [cache HIT]  {key}")
        data = np.load(cache_path, allow_pickle=True)
        is_sp = bool(data.get("is_sparse", False))
        if is_sp:
            X = sparse.csr_matrix((data["X_data"], data["X_indices"], data["X_indptr"]),
                                  shape=tuple(data["X_shape"]))
        else:
            X = data["X"]
        y = data["y"]
        return X, y

    print(f"  [cache MISS] {key}  → computing features...")
    t0 = time.time()

    if feat_name == "meta":
        from src.features.metadata import MetaExtractor
        X = MetaExtractor(dataset=ds).fit_transform()
    elif feat_name == "node2vec":
        from src.features.node2vec import Node2VecExtractor
        graph = ds.get_graph() if hasattr(ds, "get_graph") else None
        if graph is None:
            raise ValueError("node2vec requires PGB dataset with build_graph=True")
        X = Node2VecExtractor().fit_transform(graph=graph, n_nodes=len(ds))
    else:
        feat_cls = get_feature(feat_name)
        X = feat_cls().fit_transform(ds.texts())

    y = ds.labels()
    if hasattr(y, "toarray"):
        y = y.toarray()

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    is_sparse = sparse.issparse(X)
    if is_sparse:
        X_csr = X.tocsr()
        np.savez_compressed(cache_path,
                            X_data=X_csr.data, X_indices=X_csr.indices,
                            X_indptr=X_csr.indptr, X_shape=np.array(X_csr.shape),
                            y=y, is_sparse=True)
    else:
        np.savez_compressed(cache_path, X=X, y=y, is_sparse=False)

    elapsed = time.time() - t0
    print(f"  [cache SAVED] {key}  ({elapsed:.1f}s)")
    return X, y


# ═══════════════════════════════════════════════════════════════
# CV runner (with caching)
# ═══════════════════════════════════════════════════════════════

def run_cv(ds, feat_name, model_fn, cv=5, ds_kwargs=None):
    """Run cross-validation on a (dataset, feature, model) combination.

    Uses feature cache to avoid re-extracting the same features.
    """
    X, y = get_cached_features(ds, feat_name, ds_kwargs)

    # PGB special case: multi-class node classification
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
        # GaussianNB does not support sparse matrices; convert to dense
        if sparse.issparse(X_tr):
            X_tr = X_tr.toarray()
            X_te = X_te.toarray()
        y_tr, y_te = y[tr_idx], y[te_idx]
        clf = OneVsRestClassifier(copy.deepcopy(base), n_jobs=-1) if is_ml else copy.deepcopy(base)
        clf.fit(X_tr, y_tr)
        y_pred = clf.predict(X_te)
        return {
            "f1_macro": f1_score(y_te, y_pred, average="macro", zero_division=0),
            "f1_weighted": f1_score(y_te, y_pred, average="weighted", zero_division=0),
            "accuracy": accuracy_score(y_te, y_pred),
            "f1_micro": f1_score(y_te, y_pred, average="micro", zero_division=0),
            "f1_samples": f1_score(y_te, y_pred, average="samples", zero_division=0)
            if is_ml else None,
        }

    t0 = time.time()
    fold_results = Parallel(n_jobs=n_jobs)(
        delayed(_eval_fold)(tr, te)
        for tr, te in tqdm(splits, desc="CV", unit="fold", leave=False)
    )
    train_time = time.time() - t0

    # Auto-select scoring metrics based on task type
    if is_ml:
        scoring = ("f1_macro", "f1_micro", "f1_samples")
    elif ds.name == "pgb":
        scoring = ("f1_macro", "accuracy")
    else:
        scoring = ("f1_macro", "f1_weighted", "accuracy")

    res = {
        "dataset": ds.name, "feature": feat_name,
        "n_samples": len(ds), "n_labels": ds.n_labels,
        "train_time_s": round(train_time, 2),
    }
    for metric in scoring:
        vals = [fr[metric] for fr in fold_results if fr.get(metric) is not None]
        if vals:
            res[metric] = round(np.mean(vals), 4)
            res[f"{metric}_std"] = round(np.std(vals), 4)
            res[f"{metric}_folds"] = ",".join(f"{v:.4f}" for v in vals)
    return res


# ═══════════════════════════════════════════════════════════════
# I/O helpers
# ═══════════════════════════════════════════════════════════════

def save_results(rows, path, key_fields=None):
    """Save results to CSV, merging with any existing file.

    If path exists, existing rows are read and merged with new rows.
    Duplicates (matched by key_fields) are overwritten by new rows.
    This prevents loss of previously saved results on incremental saves.

    Parameters
    ----------
    rows : list[dict]
        New result rows to save.
    path : Path
        Output CSV path.
    key_fields : list[str] or None
        Fields used to identify duplicates. Default: first 2-3 fields.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        print("  (no rows to save)")
        return

    # Read existing rows if file exists
    existing = {}
    if path.exists():
        with open(path) as f:
            for r in csv.DictReader(f):
                # Use first 2-3 fields as unique key (dataset, feature, model)
                k = tuple(r.get(f, "") for f in (key_fields or list(r.keys())[:3]))
                existing[k] = r

    # Merge: new rows overwrite existing
    for r in rows:
        k = tuple(r.get(f, "") for f in (key_fields or list(r.keys())[:3]))
        existing[k] = r

    merged = list(existing.values())
    all_keys = set()
    for r in merged:
        all_keys.update(r.keys())

    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=sorted(all_keys))
        w.writeheader()
        w.writerows(merged)
    print(f"  -> saved {len(merged)} rows to {path}")


def model_label(name):
    """Human-readable model name."""
    labels = {"nb": "NaiveBayes", "knn": "k-NN", "svm": "SVM",
              "lr": "LogisticReg", "rf": "RandomForest",
              "ada": "AdaBoost", "xgb": "XGBoost"}
    return labels.get(name, name)

