"""Fig 8 — UMAP Embedding Visualization (uses cluster-extracted embeddings).

2×3 composite:
  (A) PML BioBERT 768d → UMAP 2D
  (B) ST BioBERT 768d → UMAP 2D
  (C) OHSUMED BioBERT (pending cluster)
  (D) PML TF-IDF 5000d → UMAP 2D (direct cosine)
  (E) PGB Node2Vec [placeholder]
  (F) Fine-tuning Effect [placeholder]

Embeddings: _cache/umap_*.npz extracted on cluster (no local BioBERT).
"""

import sys
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy import sparse

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import load_dataset, get_cached_features
from plot_utils import save


def compute_umap(X, n_neighbors=30, min_dist=0.3):
    from umap import UMAP
    if sparse.issparse(X):
        X = X.toarray()
    return UMAP(n_components=2, n_neighbors=n_neighbors,
                min_dist=min_dist, metric="cosine",
                random_state=42, n_jobs=1, verbose=True).fit_transform(X)


def load_emb(key):
    p = REPO / "experiments" / "_cache" / f"umap_{key}.npz"
    if p.exists():
        d = np.load(p, allow_pickle=True)
        return d["X"], d["y"], d.get("label_names", None)
    return None, None, None


fig, axes = plt.subplots(2, 3, figsize=(12, 8))
print("Loading...", flush=True)

for col, key, title, cmap in [
    (0, "pml",  "(A) PML BioBERT UMAP", "tab20"),
    (1, "st",   "(B) ST BioBERT UMAP",  "tab10"),
    (2, "ohsu", "(C) OHSUMED BioBERT UMAP", "tab10"),
]:
    ax = axes[0, col]
    X, y, ln = load_emb(key)
    if X is not None:
        print(f"  {key}: computing UMAP on {X.shape[0]}×{X.shape[1]}...", flush=True)
        U = compute_umap(X)
        ax.scatter(U[:, 0], U[:, 1], c=y, cmap=cmap, s=2, alpha=0.6)
        if col == 1 and y is not None:  # ST legend
            n = min(6, len(np.unique(y)))
            h = [plt.Line2D([0], [0], marker="o", color="w",
                  markerfacecolor=plt.cm.tab10(i/n), markersize=4)
                 for i in range(n)]
            lab = [str(l)[:20] for l in (ln.tolist() if ln is not None and len(ln) > 0
                                         else [f"C{i}" for i in range(n)])]
            ax.legend(h, lab, fontsize=4.5, loc="lower left", frameon=False, ncol=2)
        print(f"  {key} done", flush=True)
    else:
        ax.text(0.5, 0.5, "pending\ncluster", ha="center", va="center",
                fontsize=7, color="gray", transform=ax.transAxes)
    ax.set_title(title, loc="left", fontweight="bold")
    ax.set_xticks([]); ax.set_yticks([])

# (D) PML TF-IDF UMAP
ax = axes[1, 0]
try:
    X, _ = get_cached_features(load_dataset("pml"), "tfidf")
    rng = np.random.RandomState(42)
    idx = rng.choice(X.shape[0], 2000, replace=False)
    U = compute_umap(X[idx])
    ds = load_dataset("pml")
    y = ds.labels().argmax(axis=1)
    ax.scatter(U[:, 0], U[:, 1], c=y[idx], cmap="tab20", s=2, alpha=0.6)
    ax.set_title("(D) PML TF-IDF UMAP (cosine)", loc="left", fontweight="bold")
    print("  (D) done", flush=True)
except Exception as e:
    ax.text(0.5, 0.5, f"error", ha="center", va="center",
            fontsize=7, color="gray", transform=ax.transAxes)
    print(f"  (D) {e}", flush=True)
ax.set_xticks([]); ax.set_yticks([])

# (E) (F) placeholders
for col, title in [(1, "(E) PGB Node2Vec\n(needs cluster)"),
                     (2, "(F) Fine-tuning\n(needs checkpoint)")]:
    ax = axes[1, col]
    ax.text(0.5, 0.5, title, ha="center", va="center",
            fontsize=8, color="gray", transform=ax.transAxes)
    ax.set_title(title.split("\n")[0], loc="left", fontweight="bold")

plt.subplots_adjust(left=0.05, right=0.98, top=0.96, bottom=0.05,
                    hspace=0.3, wspace=0.25)
save(fig, "fig8_umap_embeddings")
print("Fig 8 done.", flush=True)
