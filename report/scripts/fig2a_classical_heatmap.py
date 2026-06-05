"""Fig 2A — Classical Algorithm Matrix: Performance Landscape.

2×3 composite: 3 datasets × unified colorbar + cross-dataset bar + time bar.

Uses the old classical_matrix.csv (mean/std only) as placeholder.
When cluster re-runs finish, update path to merged CSV with _folds columns.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from plot_utils import save, C, PALETTE

# ── Load data ──
df = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                 "experiments/001_classical_matrix/results/classical_matrix.csv")

DATASETS = {"ohsumed": "OHSUMED\n(1,650 labels)",
            "pubmed_multilabel": "PubMed-MultiLabel\n(16 labels)",
            "pgb": "PGB\n(3 labels)"}
FEATURES = ["tfidf", "biobert", "lda", "meta"]
FEAT_LABELS = {"tfidf": "TF-IDF", "biobert": "BioBERT",
               "lda": "LDA", "meta": "Meta"}
MODELS = ["AdaBoost", "LogisticReg", "NaiveBayes", "RandomForest",
          "SVM", "XGBoost", "k-NN"]
MODEL_SHORT = {"AdaBoost": "Ada", "LogisticReg": "LR",
               "NaiveBayes": "NB", "RandomForest": "RF",
               "SVM": "SVM", "XGBoost": "XGB", "k-NN": "kNN"}

# ── Pivot data into 3 heatmap matrices ──
matrices = {}
for ds, ds_label in DATASETS.items():
    sub = df[df["dataset"] == ds]
    mat = np.full((len(MODELS), len(FEATURES)), np.nan)
    for i, model in enumerate(MODELS):
        for j, feat in enumerate(FEATURES):
            row = sub[(sub["model"] == model) & (sub["feature"] == feat)]
            if not row.empty and "f1_macro" in row.columns:
                mat[i, j] = row["f1_macro"].values[0]
    matrices[ds] = mat

# ── Find global range ──
all_vals = np.concatenate([m.flatten() for m in matrices.values()])
all_vals = all_vals[~np.isnan(all_vals)]
vmin, vmax = 0, np.percentile(all_vals, 98)

# ═══════════════════════════════════════════════════════════════
# Build figure
# ═══════════════════════════════════════════════════════════════

fig = plt.figure(figsize=(10, 6.5))
gs = fig.add_gridspec(2, 4, width_ratios=[1, 1, 1, 0.08],
                      height_ratios=[1, 0.5],
                      hspace=0.45, wspace=0.15,
                      left=0.06, right=0.94, top=0.95, bottom=0.12)

# ── (A-C) Heatmaps ──
dataset_list = list(DATASETS.keys())
for col_idx, ds in enumerate(dataset_list):
    ax = fig.add_subplot(gs[0, col_idx])
    mat = matrices[ds]
    im = ax.imshow(mat, aspect="auto", cmap="YlOrRd",
                   norm=Normalize(vmin, vmax))

    # Annotate cells
    for i in range(len(MODELS)):
        for j in range(len(FEATURES)):
            val = mat[i, j]
            if not np.isnan(val):
                color = "white" if val > (vmin + vmax) / 2 else "black"
                ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                        fontsize=5.8, color=color)

    ax.set_xticks(range(len(FEATURES)))
    ax.set_xticklabels([FEAT_LABELS[f] for f in FEATURES], rotation=30,
                       ha="right", fontsize=7)
    ax.set_yticks(range(len(MODELS)))
    ax.set_yticklabels([MODEL_SHORT[m] for m in MODELS], fontsize=7)
    ax.set_title(f"({chr(65+col_idx)}) {DATASETS[ds]}",
                 loc="center", fontweight="bold", fontsize=8)

# Colorbar
cax = fig.add_subplot(gs[0, 3])
cb = plt.colorbar(im, cax=cax)
cb.set_label("F1-macro", fontsize=7)

# ── (D) Legend (empty) → reused as Cross-dataset Best ──
ax = fig.add_subplot(gs[1, :2])
best_per_ds = {}
for ds, ds_label in DATASETS.items():
    sub = df[df["dataset"] == ds]
    if not sub.empty:
        best = sub.loc[sub["f1_macro"].idxmax()]
        best_per_ds[ds] = best["f1_macro"]

ds_names_short = ["OHSUMED", "PML", "PGB"]
bars = ax.bar(ds_names_short, [best_per_ds[k] for k in dataset_list],
              color=[C["blue"], C["green"], C["orange"]], width=0.5)
ax.set_ylabel("Best F1-macro")
ax.set_title("(D) Best Performance per Dataset", loc="left",
             fontweight="bold")
for bar, val in zip(bars, [best_per_ds[k] for k in dataset_list]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01,
            f"{val:.3f}", ha="center", fontsize=7)

# ── (E) Training Time ──
ax = fig.add_subplot(gs[1, 2:])
time_data = []
for ds in dataset_list:
    sub = df[df["dataset"] == ds]
    for feat in FEATURES:
        sf = sub[sub["feature"] == feat]
        if not sf.empty:
            time_data.append({
                "ds": ds, "feat": feat,
                "time": sf["train_time_s"].mean()
            })

tdf = pd.DataFrame(time_data)
tdf["label"] = tdf["ds"].map({"ohsumed": "OHSUMED",
                              "pubmed_multilabel": "PML",
                              "pgb": "PGB"}) + "/" + tdf["feat"].map(FEAT_LABELS)
# Short labels
tdf = tdf.sort_values("time", ascending=True)
ax.barh(range(len(tdf)), tdf["time"].values, color=C["blue"], height=0.6)
ax.set_yticks(range(len(tdf)))
ax.set_yticklabels(tdf["label"].values, fontsize=6)
ax.set_xlabel("Training Time (s, log scale)")
ax.set_xscale("log")
ax.set_title("(E) Training Time by Feature × Dataset", loc="left",
             fontweight="bold")

save(fig, "fig2a_classical_heatmap")
print("Fig 2A done.")
