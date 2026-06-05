"""Fig 7 — Transfer Learning.

2×2 composite:
  (A) Full Experiment Waterfall
  (B) Fine-tune Gain Bars with significance
  (C) Pre-training Source Comparison
  (D) Feature × Model Synergy Matrix
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
tl = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                 "experiments/007_transfer_learning/results/transfer_learning.csv")
clf = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                  "experiments/001_classical_matrix/results/classical_matrix.csv")

# ═══════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 2, figsize=(10, 7.5))

# ── (A) Waterfall Chart ──
ax = axes[0, 0]
# Order: zero-shot → baselines → fine-tuned
exp_order = ["A1", "A2", "A4", "A5", "B3", "B1", "D2", "D1", "C2", "C1"]
# Filter to available
available = [e for e in exp_order if e in tl["exp_id"].values]
f1_map = {r["exp_id"]: r["f1_macro"] for _, r in tl.iterrows()}
vals = [f1_map[e] for e in available]
labels = [f"{e}: {r['method'].split(':')[0] if ':' in str(r['method']) else r['method']}"
          for e, r in zip(available, [tl[tl["exp_id"] == e].iloc[0] for e in available])]
labels_short = available  # Use exp_id for brevity

colors = []
for e in available:
    if e.startswith("A"):
        colors.append(C["red"])
    elif e.startswith("B"):
        colors.append(C["blue"])
    elif e.startswith("C"):
        colors.append(C["green"])
    else:
        colors.append(C["purple"])

ax.bar(labels_short, vals, color=colors, width=0.5, edgecolor="white")
ax.set_ylabel("F1-macro")
ax.set_title("(A) Transfer Learning Waterfall", loc="left", fontweight="bold")
ax.axhline(y=0, color="black", lw=0.3)

# ── (B) Fine-tune Gain ──
ax = axes[0, 1]
baseline = f1_map.get("B1", 0)
fine_tune_c1 = f1_map.get("C1", 0)
fine_tune_c2 = f1_map.get("C2", 0)
groups = ["B1\nST→ST LR", "C1\nPML→ST MLP", "C2\nOHSUMED→ST MLP"]
gvals = [baseline, fine_tune_c1, fine_tune_c2]
gcolors = [C["blue"], C["green"], C["orange"]]
bars = ax.bar(groups, gvals, color=gcolors, width=0.5, edgecolor="white")

# Annotate gain
for i, (val, base) in enumerate(zip(gvals, [baseline] * 3)):
    if i > 0 and val > 0:
        gain = (val - baseline) / baseline * 100 if baseline > 0 else 0
        ax.annotate(f"+{gain:.1f}%",
                    (i, val), fontsize=7, ha="center", va="bottom",
                    fontweight="bold", color=C["green"] if gain > 0 else C["red"],
                    xytext=(0, 5), textcoords="offset points")

ax.set_ylabel("F1-macro")
ax.set_title("(B) Fine-tune Gain", loc="left", fontweight="bold")

# ── (C) Pre-training Source ──
ax = axes[1, 0]
# PML vs OHSUMED pre-training
sources = ["PML → ST\n(+9.6%)", "OHSUMED → ST\n(+1.9%)"]
source_vals = [fine_tune_c1, fine_tune_c2]
source_baseline = [baseline, baseline]
x_src = np.arange(len(sources))
w_src = 0.3
ax.bar(x_src - w_src/2, source_baseline, w_src, color=C["gray"],
       alpha=0.4, label="Baseline (ST→ST)", edgecolor="white")
ax.bar(x_src + w_src/2, source_vals, w_src,
       color=[C["green"], C["orange"]], label="Fine-tuned", edgecolor="white")
ax.set_xticks(x_src)
ax.set_xticklabels(sources, fontsize=7)
ax.set_ylabel("F1-macro")
ax.set_title("(C) Pre-training Source", loc="left", fontweight="bold")
ax.legend(fontsize=6, frameon=False)

# ── (D) Feature × Model Synergy Matrix ──
ax = axes[1, 1]
FEATURES = ["tfidf", "biobert", "lda", "meta"]
MODELS_s = ["AdaBoost", "LogisticReg", "NaiveBayes", "RandomForest",
            "SVM", "XGBoost", "k-NN"]
FEAT_L = {"tfidf": "TF-IDF", "biobert": "BioBERT", "lda": "LDA", "meta": "Meta"}
MODEL_L = {"AdaBoost": "Ada", "LogisticReg": "LR", "NaiveBayes": "NB",
           "RandomForest": "RF", "SVM": "SVM", "XGBoost": "XGB", "k-NN": "kNN"}

# Compute z-score normalized synergy matrix (pooled across datasets)
synergy = np.zeros((len(MODELS_s), len(FEATURES)))
for i, model in enumerate(MODELS_s):
    for j, feat in enumerate(FEATURES):
        vals = clf[(clf["model"] == model) & (clf["feature"] == feat)]["f1_macro"]
        if not vals.empty:
            synergy[i, j] = vals.mean()

# Z-score normalize
synergy_z = (synergy - synergy.mean()) / (synergy.std() + 1e-8)

im = ax.imshow(synergy_z, aspect="auto", cmap="RdBu_r",
               norm=Normalize(-1.5, 1.5))
ax.set_xticks(range(len(FEATURES)))
ax.set_xticklabels([FEAT_L[f] for f in FEATURES], fontsize=7)
ax.set_yticks(range(len(MODELS_s)))
ax.set_yticklabels([MODEL_L[m] for m in MODELS_s], fontsize=7)
ax.set_title("(D) Feature × Model Synergy (Z-score)", loc="left",
             fontweight="bold")

# Annotate top synergies
for i in range(len(MODELS_s)):
    for j in range(len(FEATURES)):
        val = synergy_z[i, j]
        if abs(val) > 0.5:
            color = "white" if abs(val) > 1 else "black"
            ax.text(j, i, f"{val:+.1f}", ha="center", va="center",
                    fontsize=5.5, color=color)

cbar = plt.colorbar(im, ax=ax, shrink=0.75, pad=0.02)
cbar.set_label("Z-score", fontsize=6)

plt.subplots_adjust(left=0.07, right=0.97, top=0.95, bottom=0.08,
                    hspace=0.4, wspace=0.35)
save(fig, "fig7_transfer_learning")
print("Fig 7 done.")
