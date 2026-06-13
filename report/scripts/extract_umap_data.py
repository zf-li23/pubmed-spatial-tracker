"""Extract subsampled BioBERT embeddings from cluster cache for local UMAP.

Usage on cluster (experiments/ directory):
    conda activate pubmed-tracker
    cd /path/to/pubmed-tracker
    python report/scripts/extract_umap_data.py

Output: experiments/_cache/umap_*.npz  → rsync back to local
"""
import sys, os, numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent          # report/scripts/
REPO = HERE.parent.parent                        # repo root
sys.path.insert(0, str(REPO))
from experiments._common import load_dataset, get_cached_features

CACHE = REPO / "experiments" / "_cache"
SUB = 2000
SEED = 42

datasets = {
    "pml":  ("pml", {}),
    "st":   ("st", {}),
    "ohsu": ("ohsumed", {"min_df": 10, "max_samples": 3000}),
}

for key, (ds_name, ds_kw) in datasets.items():
    print(f"\n=== {key} ({ds_name}) ===", flush=True)
    ds = load_dataset(ds_name, **ds_kw)
    X, y_raw = get_cached_features(ds, "biobert", dict(ds_kw))

    rng = np.random.RandomState(SEED)
    n = min(SUB, X.shape[0])
    idx = rng.choice(X.shape[0], n, replace=False)

    X_sub = X[idx]
    if hasattr(y_raw, "toarray"):
        y_sub = y_raw.toarray()[idx]
    else:
        y_sub = y_raw[idx]

    # Multi-label → single class
    if y_sub.ndim > 1 and y_sub.shape[1] > 1:
        y_sub = y_sub.argmax(axis=1)

    label_names = getattr(ds, "label_names", None)
    out = CACHE / f"umap_{key}.npz"
    np.savez_compressed(out, X=X_sub, y=y_sub,
                         label_names=np.array(label_names, dtype=object))
    print(f"  Saved {out} ({X_sub.shape[0]} pts, X {X_sub.dtype}, y {y_sub.dtype})",
          flush=True)

print("\nDone. Files to rsync:", flush=True)
for f in sorted(CACHE.glob("umap_*.npz")):
    sz = os.path.getsize(f) / 1e6
    print(f"  {f.name}: {sz:.1f} MB", flush=True)
