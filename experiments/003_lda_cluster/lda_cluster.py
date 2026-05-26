"""003 — LDA + Clustering: unsupervised topic discovery evaluation

Uses LDA topic distributions as features for KMeans clustering.
Evaluated with NMI and ARI against ground-truth labels (where available).

Grid:
    OHSUMED (10K) × LDA+KMeans
    PML     (10K) × LDA+KMeans
    PGB     (5K)  × LDA+KMeans
    = 3 runs

K is set to the number of ground-truth labels for each dataset.
"""
from pathlib import Path
import sys, time
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))

import numpy as np
from tqdm import tqdm
from _common import load_dataset, get_cached_features, save_results

OUT = HERE / "results"

DATASETS = {
    "ohsumed": {"min_df": 10, "max_samples": 10000},
    "pml":     {},
    "pgb":     {"build_graph": False, "max_samples": 5000},
}

FEATURE = "lda"


def run_cluster(ds, ds_kwargs):
    """KMeans on LDA features, NMI/ARI vs ground truth."""
    from sklearn.cluster import KMeans
    from sklearn.metrics import normalized_mutual_info_score, adjusted_rand_score

    X, y_raw = get_cached_features(ds, FEATURE, ds_kwargs)
    if hasattr(y_raw, "toarray"):
        y_raw = y_raw.toarray()

    # Get single-label ground truth for clustering eval
    if ds.name == "pgb":
        y_true = y_raw.argmax(axis=1)
    else:
        # Use dominant label (or label with highest score) as pseudo-ground-truth
        if y_raw.ndim > 1:
            y_true = y_raw.argmax(axis=1)
        else:
            y_true = y_raw

    n_clusters = ds.n_labels
    t0 = time.time()

    km = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
    y_pred = km.fit_predict(X)

    elapsed = time.time() - t0
    return {
        "dataset": ds.name, "feature": FEATURE, "model": "KMeans",
        "n_samples": len(ds), "n_clusters": n_clusters,
        "nmi": round(normalized_mutual_info_score(y_true, y_pred), 4),
        "ari": round(adjusted_rand_score(y_true, y_pred), 4),
        "train_time_s": round(elapsed, 2),
    }


if __name__ == "__main__":
    rows = []
    for ds_name, ds_kw in tqdm(DATASETS.items(), desc="003", unit="ds"):
        ds = load_dataset(ds_name, **ds_kw)
        print(f"\n{'='*50}")
        print(f"  {ds_name}: {len(ds)} docs, {ds.n_labels} labels")
        print(f"{'='*50}")

        try:
            r = run_cluster(ds, ds_kw)
            rows.append(r)
            print(f"  NMI={r['nmi']:.4f}  ARI={r['ari']:.4f}  time={r['train_time_s']:.1f}s")
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback; traceback.print_exc()

    save_results(rows, OUT / "lda_cluster.csv")
    print(f"\n✅ 003 done — {len(rows)} results")
