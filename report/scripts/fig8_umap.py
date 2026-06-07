"""Fig 8 — UMAP Embedding Visualization (pre-computed 2D coordinates).

2×3 composite with legends on all panels:
  (A) PML BioBERT       — 2K/16 MeSH categories  — umap_2d_pml.npz
  (B) ST BioBERT        — 2K/6 LLM categories     — umap_2d_st.npz
  (C) OHSUMED BioBERT   — 2K/top-10 MeSH          — umap_2d_ohsu.npz
  (D) PML TF-IDF        — 2K/16 categories         — live UMAP
  (E) PGB Node2Vec      — 5K nodes/3 types         — umap_2d_pgb.npz
  (F) Fine-tuning Effect [placeholder]

Interactive 3D: python fig8_3d_interactive.py
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


def load_2d(key):
    p = REPO / "experiments" / "_cache" / f"umap_2d_{key}.npz"
    if p.exists():
        d = np.load(p, allow_pickle=True)
        return d["coords_2d"], d["y"], d.get("label_names", None)
    return None, None, None


def legend(ax, y, label_names, n, cmap):
    """Compact legend."""
    u = np.unique(y)[:n]
    cmap_obj = plt.colormaps.get_cmap(cmap)
    h = [plt.Line2D([0],[0], marker="o", color="w",
          markerfacecolor=cmap_obj(i/len(u)), markersize=3)
         for i in range(len(u))]
    try:
        ln_len = len(label_names)
    except TypeError:
        ln_len = 0
    labs = []
    for i in u:
        idx = int(i)
        labs.append(str(label_names[idx])[:18] if label_names is not None and
                     idx < ln_len else f"C{idx}")
    ax.legend(h, labs, fontsize=4.5, loc="lower left", frameon=False, ncol=2)


fig, axes = plt.subplots(2, 3, figsize=(12, 8))

# Row 1: BioBERT embeddings
datasets_row1 = [
    ("pml",  "(A) PML BioBERT\n(2K, 16 MeSH categories)",        "tab20", 8),
    ("st",   "(B) ST BioBERT\n(2K, 6 LLM categories)",           "tab10", 6),
    ("ohsu", "(C) OHSUMED BioBERT\n(2K, top-10 MeSH terms)",      "tab10", 10),
]
for col, (key, title, cmap, n) in enumerate(datasets_row1):
    ax = axes[0, col]
    coords, y, ln = load_2d(key)
    if coords is not None:
        ax.scatter(coords[:, 0], coords[:, 1], c=y, cmap=cmap,
                   s=2.5, alpha=0.6, edgecolors="none")
        legend(ax, y, ln, n, cmap)
        print(f"  {key}: {coords.shape[0]} pts", flush=True)
    else:
        ax.text(0.5, 0.5, "unavailable", ha="center", va="center",
                fontsize=7, color="gray", transform=ax.transAxes)
    ax.set_title(title, loc="left", fontweight="bold", fontsize=7)
    ax.set_xticks([]); ax.set_yticks([])

# (D) PML TF-IDF
ax = axes[1, 0]
try:
    from umap import UMAP
    X, _ = get_cached_features(load_dataset("pml"), "tfidf")
    rng = np.random.RandomState(42)
    idx = rng.choice(X.shape[0], 2000, replace=False)
    U = UMAP(n_components=2, metric="cosine", random_state=42,
             verbose=False).fit_transform(
        X[idx].toarray() if sparse.issparse(X) else X[idx])
    ds = load_dataset("pml")
    y = ds.labels().argmax(axis=1)
    ax.scatter(U[:, 0], U[:, 1], c=y[idx], cmap="tab20",
               s=2.5, alpha=0.6, edgecolors="none")
    ln = getattr(ds, "label_names", None)
    legend(ax, y[idx], ln, 8, "tab20")
    print("  tfidf: 2000 pts", flush=True)
except Exception as e:
    ax.text(0.5, 0.5, "error", ha="center", va="center",
            fontsize=7, color="gray", transform=ax.transAxes)
    print(f"  tfidf error: {e}", flush=True)
ax.set_title("(D) PML TF-IDF\n(2K, cosine UMAP)", loc="left", fontweight="bold", fontsize=7)
ax.set_xticks([]); ax.set_yticks([])

# (E) PGB Node2Vec (5000 points, 3 classes)
ax = axes[1, 1]
coords, y, ln = load_2d("pgb")
if coords is not None:
    ax.scatter(coords[:, 0], coords[:, 1], c=y, cmap="tab10",
               s=1.2, alpha=0.5, edgecolors="none")
    legend(ax, y, ln, 3, "tab10")
    print(f"  pgb: {coords.shape[0]} pts", flush=True)
else:
    ax.text(0.5, 0.5, "unavailable", ha="center", va="center",
            fontsize=7, color="gray", transform=ax.transAxes)
ax.set_title("(E) PGB Node2Vec\n(5K nodes, 3 types)", loc="left", fontweight="bold", fontsize=7)
ax.set_xticks([]); ax.set_yticks([])

# (F) placeholder
ax = axes[1, 2]
ax.text(0.5, 0.5, "(F) Fine-tuning Effect\n(needs checkpoint)", ha="center",
        va="center", fontsize=8, color="gray", transform=ax.transAxes)
ax.set_title("(F) Fine-tuning Effect", loc="left", fontweight="bold", fontsize=7)

plt.subplots_adjust(left=0.05, right=0.98, top=0.96, bottom=0.05,
                    hspace=0.35, wspace=0.25)
save(fig, "fig8_umap_embeddings")
print("Fig 8 done.", flush=True)
