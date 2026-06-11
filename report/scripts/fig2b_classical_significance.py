"""Fig 2B — Classical Matrix: Significance & Analysis.

2×2 composite:
  (A) PML Top-5 with error bars + significance stars
  (B) OHSUMED Top-5 with error bars + significance stars
  (C) Feature Effectiveness (best model per feature, grouped)
  (D) Performance vs. Training Time scatter
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from plot_utils import save, C, PALETTE, sig_annotate, paired_ttest_from_folds

# ── Load data (with _folds columns where available) ──
df = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                 "experiments/001_classical_matrix/results/classical_matrix_with_folds.csv")

DATASETS = {"ohsumed": "OHSUMED", "pubmed_multilabel": "PML", "pgb": "PGB"}
FEAT_LABELS = {"tfidf": "TF-IDF", "biobert": "BioBERT",
               "lda": "LDA", "meta": "Meta"}
FEAT_COLORS = {"tfidf": C["blue"], "biobert": C["green"],
               "lda": C["orange"], "meta": C["purple"]}

MODEL_SHORT = {"AdaBoost": "Ada", "LogisticReg": "LR", "NaiveBayes": "NB",
               "RandomForest": "RF", "SVM": "SVM", "XGBoost": "XGB",
               "k-NN": "kNN"}


def top_n_per_dataset(dataset_key, n=5):
    """Return top-n rows for a dataset, sorted by f1_macro desc."""
    sub = df[df["dataset"] == dataset_key].dropna(subset=["f1_macro"])
    return sub.nlargest(n, "f1_macro")


# ═══════════════════════════════════════════════════════════════
# Build figure
# ═══════════════════════════════════════════════════════════════

fig, axes = plt.subplots(2, 2, figsize=(9.5, 7.5))

# ── (A) PML Top-5 ──
ax = axes[0, 0]
pml_top = top_n_per_dataset("pubmed_multilabel")
labels = [f"{FEAT_LABELS.get(r['feature'], r['feature'])}/{MODEL_SHORT.get(r['model'], r['model'])}"
          for _, r in pml_top.iterrows()]
vals = pml_top["f1_macro"].values
errs = pml_top["f1_macro_std"].values
colors = [FEAT_COLORS.get(r["feature"], C["gray"]) for _, r in pml_top.iterrows()]
bars = ax.bar(range(len(labels)), vals, yerr=errs, color=colors, width=0.6,
              capsize=2, edgecolor="white", linewidth=0.3)

# Significance: best vs rest — stair-step heights (farther = higher)
if len(vals) > 1:
    best_val = vals[0]
    bar_tops = [vals[k] + errs[k] for k in range(len(vals))]
    base_y = max(bar_tops)
    for i in range(1, len(vals)):
        fold_a = pml_top.iloc[0].get("f1_macro_folds", None)
        fold_b = pml_top.iloc[i].get("f1_macro_folds", None)
        if fold_a is not None and fold_b is not None and pd.notna(fold_a) and pd.notna(fold_b):
            p = paired_ttest_from_folds(str(fold_a), str(fold_b))
        else:
            p = None
        # Stair-step: farther bars get higher brackets
        step = 0.035 * (i - 1)
        sig_annotate(ax, 0, i, base_y + step, p)
    # Add headroom for the tallest bracket
    ax.set_ylim(0, base_y + 0.035 * (len(vals) - 2) + (base_y * 0.12))

ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=6.5)
ax.set_ylabel("F1-macro")
ax.set_title("(A) PML — Top 5 Combinations", loc="left", fontweight="bold")

# ── (B) OHSUMED Top-5 (no CV data yet — no significance) ──
ax = axes[0, 1]
ohs_top = top_n_per_dataset("ohsumed")
labels = [f"{FEAT_LABELS.get(r['feature'], r['feature'])}/{MODEL_SHORT.get(r['model'], r['model'])}"
          for _, r in ohs_top.iterrows()]
vals = ohs_top["f1_macro"].values
errs = ohs_top["f1_macro_std"].values
colors = [FEAT_COLORS.get(r["feature"], C["gray"]) for _, r in ohs_top.iterrows()]
ax.bar(range(len(labels)), vals, yerr=errs, color=colors, width=0.6,
       capsize=2, edgecolor="white", linewidth=0.3)
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=35, ha="right", fontsize=6.5)
ax.set_ylabel("F1-macro")
ax.set_title("(B) OHSUMED — Top 5 Combinations", loc="left", fontweight="bold")

# ── (C) Feature Effectiveness ──
ax = axes[1, 0]
feats = ["tfidf", "biobert", "lda", "meta"]
ds_order = ["pubmed_multilabel", "ohsumed", "pgb"]
x = np.arange(len(feats))
width = 0.22
for idx, ds in enumerate(ds_order):
    sub = df[df["dataset"] == ds]
    best_per_feat = []
    for feat in feats:
        sf = sub[sub["feature"] == feat].dropna(subset=["f1_macro"])
        if not sf.empty:
            best_per_feat.append(sf["f1_macro"].max())
        else:
            best_per_feat.append(0)
    ax.bar(x + idx * width, best_per_feat, width,
           color=[C["blue"], C["green"], C["orange"]][idx],
           label=DATASETS[ds], edgecolor="white", linewidth=0.3)

ax.set_xticks(x + width)
ax.set_xticklabels([FEAT_LABELS[f] for f in feats])
ax.set_ylabel("Best F1-macro per Feature")
ax.set_title("(C) Feature Effectiveness", loc="left", fontweight="bold")
ax.legend(fontsize=6, frameon=False, ncol=3)

# ── (D) Performance vs. Training Time ──
ax = axes[1, 1]
for ds, marker in [("ohsumed", "o"), ("pubmed_multilabel", "s"), ("pgb", "^")]:
    sub = df[df["dataset"] == ds].dropna(subset=["f1_macro", "train_time_s"])
    for feat, color in FEAT_COLORS.items():
        sf = sub[sub["feature"] == feat]
        if not sf.empty:
            ax.scatter(sf["train_time_s"], sf["f1_macro"], c=color,
                       marker=marker, s=12, alpha=0.7, edgecolors="none")

ax.set_xscale("log")
ax.set_xlabel("Training Time (s, log scale)")
ax.set_ylabel("F1-macro")
ax.set_title("(D) Performance vs. Training Time", loc="left",
             fontweight="bold")

# Dual legend: dataset (markers) + feature (colors)
from matplotlib.lines import Line2D
ds_legend = [
    Line2D([0], [0], marker="o", color="w", markerfacecolor="gray",
           markersize=5, label="OHSUMED"),
    Line2D([0], [0], marker="s", color="w", markerfacecolor="gray",
           markersize=5, label="PML"),
    Line2D([0], [0], marker="^", color="w", markerfacecolor="gray",
           markersize=5, label="PGB"),
]
feat_legend = [
    Line2D([0], [0], color=FEAT_COLORS["tfidf"], lw=2, label="TF-IDF"),
    Line2D([0], [0], color=FEAT_COLORS["biobert"], lw=2, label="BioBERT"),
    Line2D([0], [0], color=FEAT_COLORS["lda"], lw=2, label="LDA"),
    Line2D([0], [0], color=FEAT_COLORS["meta"], lw=2, label="Meta"),
]
leg1 = ax.legend(handles=ds_legend, loc="upper right", fontsize=5.5,
                 frameon=False, title="Dataset", title_fontsize=6)
ax.add_artist(leg1)
ax.legend(handles=feat_legend, loc="upper left", fontsize=5.5,
          frameon=False, title="Feature", title_fontsize=6)

plt.subplots_adjust(left=0.08, right=0.97, top=0.95, bottom=0.08,
                    hspace=0.4, wspace=0.35)
save(fig, "fig2b_classical_significance")
print("Fig 2B done.")
