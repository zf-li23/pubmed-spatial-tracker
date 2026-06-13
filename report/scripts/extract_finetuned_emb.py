"""Compute fine-tuned BioBERT embeddings for ST (Panel F).

Fine-tunes BioBERT+MLP on ST (80% train), then extracts [CLS] embeddings
for all 9,147 docs. Saves to experiments/_cache/umap_st_finetuned.npz.

Usage on cluster (GPU node):
    conda activate biobert_env
    cd /path/to/pubmed-tracker
    python report/scripts/extract_finetuned_emb.py
"""

import sys, os, numpy as np
from pathlib import Path
HERE = Path(__file__).resolve().parent          # report/scripts/
REPO = HERE.parent.parent                        # repo root
sys.path.insert(0, str(REPO))
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from experiments._common import load_dataset
from src.models.deep import BioBERTFineTuner
from sklearn.model_selection import StratifiedKFold

CACHE = REPO / "experiments" / "_cache"
N_SUB = 2000  # subsample for UMAP (full 9K would be heavy)
SEED = 42

print("Loading ST dataset...", flush=True)
ds = load_dataset("st")
texts = ds.texts()
y = ds.labels().argmax(axis=1)
n_classes = ds.n_labels

# Use 80% for fine-tuning (same as Exp 007 split)
rng = np.random.RandomState(SEED)
perm = rng.permutation(len(ds))
n_train = int(len(ds) * 0.8)
train_idx = perm[:n_train]

texts_train = [texts[i] for i in train_idx]
y_train = y[train_idx]

print(f"Fine-tuning on {len(texts_train)} docs ({n_classes} classes)...", flush=True)
tuner = BioBERTFineTuner(n_labels=n_classes, epochs=3, batch_size=16,
                         multilabel=False)
tuner.fit(texts_train, y_train)

print("Extracting fine-tuned embeddings for all ST docs...", flush=True)
embeddings = tuner.extract_embeddings(texts, batch_size=64)
print(f"  Shape: {embeddings.shape}", flush=True)

# Subsample for UMAP
rng2 = np.random.RandomState(SEED)
idx = rng2.choice(len(ds), N_SUB, replace=False)
X_sub = embeddings[idx]
y_sub = y[idx]

out = CACHE / "umap_st_finetuned.npz"
np.savez_compressed(out, X=X_sub, y=y_sub,
                     label_names=np.array(getattr(ds, "label_names", []), dtype=object))
print(f"Saved {out} ({X_sub.shape[0]} pts)", flush=True)
print("Done.", flush=True)
