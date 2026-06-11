"""Fig 8 — UMAP Embedding Visualization (pre-computed 2D coordinates).

2×3 composite with legends on all panels:
  (A) PML BioBERT       — 2K/16 MeSH categories  — umap_2d_pml.npz
  (B) PML TF-IDF        — 2K/16 categories         — live UMAP
  (C) OHSUMED BioBERT   — 2K/top-10 MeSH          — umap_2d_ohsu.npz
  (D) ST BioBERT        — 2K/6 LLM categories     — umap_2d_st.npz
  (E) ST Fine-tuned     — 2K/6 categories         — umap_2d_st_finetuned.npz
  (F) PGB Node2Vec      — 5K nodes/3 types         — umap_2d_pgb.npz

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

# ════════════════════════════════════════════════════════
# Row 0
# ════════════════════════════════════════════════════════

# (A) PML BioBERT
ax = axes[0, 0]
coords, y, ln = load_2d("pml")
if coords is not None:
    ax.scatter(coords[:, 0], coords[:, 1], c=y, cmap="tab20",
               s=2.5, alpha=0.6, edgecolors="none")
    legend(ax, y, ln, 8, "tab20")
    print(f"  pml: {coords.shape[0]} pts", flush=True)
else:
    ax.text(0.5, 0.5, "unavailable", ha="center", va="center",
            fontsize=7, color="gray", transform=ax.transAxes)
ax.set_title("(A) PML BioBERT\n(2K, 16 MeSH categories)", loc="left",
             fontweight="bold", fontsize=7)
ax.set_xticks([]); ax.set_yticks([])

# (B) PML TF-IDF
ax = axes[0, 1]
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
ax.set_title("(B) PML TF-IDF\n(2K, cosine UMAP)", loc="left",
             fontweight="bold", fontsize=7)
ax.set_xticks([]); ax.set_yticks([])

# (C) OHSUMED BioBERT
ax = axes[0, 2]
coords, y, ln = load_2d("ohsu")
if coords is not None:
    ax.scatter(coords[:, 0], coords[:, 1], c=y, cmap="tab10",
               s=2.5, alpha=0.6, edgecolors="none")
    legend(ax, y, ln, 10, "tab10")
    print(f"  ohsu: {coords.shape[0]} pts", flush=True)
else:
    ax.text(0.5, 0.5, "unavailable", ha="center", va="center",
            fontsize=7, color="gray", transform=ax.transAxes)
ax.set_title("(C) OHSUMED BioBERT\n(2K, top-10 MeSH terms)", loc="left",
             fontweight="bold", fontsize=7)
ax.set_xticks([]); ax.set_yticks([])

# ════════════════════════════════════════════════════════
# Row 1 — ST-focused + PGB
# ════════════════════════════════════════════════════════

# (D) ST BioBERT
ax = axes[1, 0]
coords, y, ln = load_2d("st")
if coords is not None:
    ax.scatter(coords[:, 0], coords[:, 1], c=y, cmap="tab10",
               s=2.5, alpha=0.6, edgecolors="none")
    legend(ax, y, ln, 6, "tab10")
    print(f"  st: {coords.shape[0]} pts", flush=True)
else:
    ax.text(0.5, 0.5, "unavailable", ha="center", va="center",
            fontsize=7, color="gray", transform=ax.transAxes)
ax.set_title("(D) ST BioBERT\n(2K, 6 LLM categories)", loc="left",
             fontweight="bold", fontsize=7)
ax.set_xticks([]); ax.set_yticks([])

# (E) ST Fine-tuned BioBERT
ax = axes[1, 1]
coords, y, ln = load_2d("st_finetuned")
if coords is not None:
    ax.scatter(coords[:, 0], coords[:, 1], c=y, cmap="tab10",
               s=2.5, alpha=0.6, edgecolors="none")
    ln_ds = list(np.unique(y))
    try:
        u = np.unique(y)[:6]
        cmap_obj = plt.colormaps.get_cmap("tab10")
        h = [plt.Line2D([0],[0], marker="o", color="w",
              markerfacecolor=cmap_obj(i/len(u)), markersize=3)
             for i in range(len(u))]
        ln_len = len(ln_ds) if ln_ds is not None else 0
        labs = [str(ln_ds[int(i)])[:18] if ln_ds is not None and int(i) < ln_len
                else f"C{int(i)}" for i in u]
        ax.legend(h, labs, fontsize=4.5, loc="lower left", frameon=False, ncol=2)
    except Exception:
        pass
    print(f"  st_finetuned: {coords.shape[0]} pts", flush=True)
else:
    ax.text(0.5, 0.5, "unavailable", ha="center", va="center",
            fontsize=7, color="gray", transform=ax.transAxes)
ax.set_title("(E) ST Fine-tuned BioBERT\n(post-finetune embedding)", loc="left",
             fontweight="bold", fontsize=7)
ax.set_xticks([]); ax.set_yticks([])

# (F) PGB Node2Vec
ax = axes[1, 2]
coords, y, ln = load_2d("pgb")
if coords is not None:
    ax.scatter(coords[:, 0], coords[:, 1], c=y, cmap="tab10",
               s=1.2, alpha=0.5, edgecolors="none")
    legend(ax, y, ln, 3, "tab10")
    print(f"  pgb: {coords.shape[0]} pts", flush=True)
else:
    ax.text(0.5, 0.5, "unavailable", ha="center", va="center",
            fontsize=7, color="gray", transform=ax.transAxes)
ax.set_title("(F) PGB Node2Vec\n(5K nodes, 3 types)", loc="left",
             fontweight="bold", fontsize=7)
ax.set_xticks([]); ax.set_yticks([])

plt.subplots_adjust(left=0.05, right=0.98, top=0.96, bottom=0.05,
                    hspace=0.35, wspace=0.25)
save(fig, "fig5_umap")
print("Fig 5 done.", flush=True)
