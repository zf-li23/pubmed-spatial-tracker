"""Fig 8 — UMAP Embedding Visualization.

2×3 composite:
  (A) PML BioBERT 768d → UMAP 2D (colored by MeSH)
  (B) ST BioBERT 768d → UMAP 2D (colored by category)
  (C) OHSUMED BioBERT 768d → UMAP 2D (subsample)
  (D) PML TF-IDF 5000d → UMAP 2D (direct cosine, no PCA)
  (E) PGB Node2Vec [placeholder — needs cluster graph]
  (F) ST Fine-tuning Effect [placeholder — needs checkpoint]
"""

import sys, os
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from scipy import sparse

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

REPO = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "experiments"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from _common import load_dataset, get_cached_features
from plot_utils import save, C


def compute_umap(X, n_neighbors=30, min_dist=0.3):
    from umap import UMAP
    if sparse.issparse(X):
        X = X.toarray()
    reducer = UMAP(n_components=2, n_neighbors=n_neighbors,
                   min_dist=min_dist, metric="cosine",
                   random_state=42, n_jobs=-1)
    return reducer.fit_transform(X)


def get_biobert_embeddings(ds):
    from transformers import BertTokenizer, BertModel
    import torch
    from src.config import BIOBERT_MODEL

    cache_path = REPO / "experiments" / "_cache" / f"{ds.name}_biobert_embeddings.npy"
    if cache_path.exists():
        print(f"  [cache HIT] {ds.name} BioBERT")
        return np.load(cache_path)

    print(f"  Computing BioBERT embeddings for {ds.name} ({len(ds)} docs)...")
    tokenizer = BertTokenizer.from_pretrained(BIOBERT_MODEL, local_files_only=True)
    model = BertModel.from_pretrained(BIOBERT_MODEL, local_files_only=True)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = model.to(device).eval()

    texts, B = ds.texts(), 64
    all_embs = []
    for i in range(0, len(texts), B):
        batch = texts[i:i + B]
        enc = tokenizer(batch, padding=True, truncation=True,
                        max_length=128, return_tensors="pt")
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            out = model(**enc)
        mask = enc["attention_mask"].unsqueeze(-1).float()
        emb = (out.last_hidden_state * mask).sum(dim=1) / mask.sum(dim=1)
        all_embs.append(emb.cpu().numpy())

    result = np.vstack(all_embs)
    np.save(cache_path, result)
    print(f"  [saved] {cache_path}")
    return result


# ═══════════════════════════════════════════════
fig, axes = plt.subplots(2, 3, figsize=(12, 8))
print("Loading datasets...")

# ── (A) PML BioBERT UMAP ──
ax = axes[0, 0]
try:
    pml = load_dataset("pml")
    X = get_biobert_embeddings(pml)
    y = pml.labels().argmax(axis=1)
    U = compute_umap(X)
    idx = np.random.RandomState(42).choice(len(U), min(3000, len(U)), replace=False)
    ax.scatter(U[idx, 0], U[idx, 1], c=y[idx], cmap="tab20", s=1, alpha=0.6)
    ax.set_title("(A) PML BioBERT UMAP", loc="left", fontweight="bold")
    print("  (A) done")
except Exception as e:
    ax.text(0.5, 0.5, f"unavailable\n{str(e)[:60]}", ha="center", va="center",
            fontsize=7, color="gray", transform=ax.transAxes)
    print(f"  (A) failed: {e}")
ax.set_xticks([]); ax.set_yticks([])

# ── (B) ST BioBERT UMAP ──
ax = axes[0, 1]
try:
    st = load_dataset("st")
    X_st = get_biobert_embeddings(st)
    y_st = st.labels().argmax(axis=1)
    U_st = compute_umap(X_st)
    ax.scatter(U_st[:, 0], U_st[:, 1], c=y_st, cmap="tab10", s=0.5, alpha=0.6)
    ln = getattr(st, "label_names", [f"C{i}" for i in range(6)])
    handles = [plt.Line2D([0], [0], marker="o", color="w",
                          markerfacecolor=plt.cm.tab10(i/6), markersize=4)
               for i in range(6)]
    ax.legend(handles, ln, fontsize=4.5, loc="lower left", frameon=False, ncol=2)
    ax.set_title("(B) ST BioBERT UMAP", loc="left", fontweight="bold")
    print("  (B) done")
except Exception as e:
    ax.text(0.5, 0.5, f"unavailable", ha="center", va="center",
            fontsize=7, color="gray", transform=ax.transAxes)
    print(f"  (B) failed: {e}")
ax.set_xticks([]); ax.set_yticks([])

# ── (C) OHSUMED BioBERT UMAP ──
ax = axes[0, 2]
try:
    ohs = load_dataset("ohsumed", min_df=10, max_samples=3000)
    X_o = get_biobert_embeddings(ohs)
    y_o = ohs.labels()
    if hasattr(y_o, "toarray"):
        y_o = y_o.toarray()
    top10 = np.argsort(-y_o.sum(axis=0))[:10]
    y_o = np.argmax(y_o[:, top10], axis=1)
    U_o = compute_umap(X_o)
    ax.scatter(U_o[:, 0], U_o[:, 1], c=y_o, cmap="tab10", s=1, alpha=0.5)
    ax.set_title("(C) OHSUMED BioBERT UMAP", loc="left", fontweight="bold")
    print("  (C) done")
except Exception as e:
    ax.text(0.5, 0.5, f"unavailable", ha="center", va="center",
            fontsize=7, color="gray", transform=ax.transAxes)
    print(f"  (C) failed: {e}")
ax.set_xticks([]); ax.set_yticks([])

# ── (D) PML TF-IDF UMAP (direct, no PCA) ──
ax = axes[1, 0]
try:
    X_tf, _ = get_cached_features(load_dataset("pml"), "tfidf")
    X_tf_s = X_tf[:min(5000, X_tf.shape[0])]
    U_tf = compute_umap(X_tf_s)
    # Reload labels independent of panel A
    ds2 = load_dataset("pml")
    y2 = ds2.labels().argmax(axis=1)
    n_pts = U_tf.shape[0]
    ax.scatter(U_tf[:, 0], U_tf[:, 1], c=y2[:n_pts], cmap="tab20", s=1, alpha=0.6)
    ax.set_title("(D) PML TF-IDF UMAP", loc="left", fontweight="bold")
    print("  (D) done")
except Exception as e:
    ax.text(0.5, 0.5, f"unavailable", ha="center", va="center",
            fontsize=7, color="gray", transform=ax.transAxes)
    print(f"  (D) failed: {e}")
ax.set_xticks([]); ax.set_yticks([])

# ── (E) PGB Node2Vec [placeholder] ──
ax = axes[1, 1]
ax.text(0.5, 0.5, "(E) PGB Node2Vec UMAP\n(needs cluster graph data)",
        ha="center", va="center", fontsize=9, color="gray",
        transform=ax.transAxes)
ax.set_title("(E) PGB Node2Vec UMAP", loc="left", fontweight="bold")

# ── (F) Fine-tuning Effect [placeholder] ──
ax = axes[1, 2]
ax.text(0.5, 0.5, "(F) Fine-tuning Effect\n(needs checkpoint)",
        ha="center", va="center", fontsize=9, color="gray",
        transform=ax.transAxes)
ax.set_title("(F) ST Fine-tuning Effect", loc="left", fontweight="bold")

plt.subplots_adjust(left=0.05, right=0.98, top=0.96, bottom=0.05,
                    hspace=0.3, wspace=0.25)
save(fig, "fig8_umap_embeddings")
print("Fig 8 done.")
