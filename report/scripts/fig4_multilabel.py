"""Fig 4 — Multi-label Strategies + Model Robustness.

2×2 composite:
  (A) BR vs CC vs LP (PML) with significance
  (B) Strategy × Time Cost
  (C) OHSUMED zoom (all near 0)
  (D) Model Robustness box plot
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from plot_utils import save, C, PALETTE, sig_annotate, paired_ttest_from_folds

# ── Load ──
ml = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                 "experiments/004_multilabel_strategy/results/multilabel_strategy.csv")
clf = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                  "experiments/001_classical_matrix/results/classical_matrix.csv")

# ═══════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 2, figsize=(9, 7))

# ── (A) BR vs CC vs LP (PML) ──
ax = axes[0, 0]
pml_ml = ml[ml["dataset"] == "pubmed_multilabel"]
strategies = pml_ml["strategy"].values.astype(str)
strategy_vals = pml_ml["f1_macro"].values
strategy_errs = pml_ml["f1_macro_std"].values

colors = [C["blue"], C["green"], C["orange"]]
bars = ax.bar(strategies, strategy_vals, yerr=strategy_errs, color=colors,
              width=0.5, capsize=3, edgecolor="white")
# Significance: pairwise between strategies
strategy_folds = [str(pml_ml.iloc[i].get("f1_macro_folds", None)) for i in range(len(strategies))]
for i in range(len(strategies)):
    for j in range(i + 1, len(strategies)):
        fi, fj = strategy_folds[i], strategy_folds[j]
        if pd.notna(fi) and pd.notna(fj) and fi.strip() and fj.strip():
            p = paired_ttest_from_folds(fi, fj)
        else:
            p = None
        y_max = max(strategy_vals[i] + strategy_errs[i],
                    strategy_vals[j] + strategy_errs[j]) * 1.03
        sig_annotate(ax, i, j, y_max, p)
ax.set_ylabel("F1-macro")
ax.set_title("(A) Multi-label Strategy (PML)", loc="left", fontweight="bold")

# ── (B) Strategy × Time ──
ax = axes[0, 1]
ax2 = ax.twinx()
ax.bar(strategies, strategy_vals, color=colors, width=0.4, alpha=0.7,
       edgecolor="white")
times = pml_ml["train_time_s"].values
ax2.plot(strategies, times, "ko-", lw=1, markersize=5, label="Time")
ax.set_ylabel("F1-macro")
ax2.set_ylabel("Time (s)", color="gray")
ax.set_title("(B) F1 vs Time Cost (PML)", loc="left", fontweight="bold")
ax2.legend(fontsize=6, frameon=False)

# ── (C) OHSUMED zoom ──
ax = axes[1, 0]
ohs_ml = ml[ml["dataset"] == "ohsumed"]
ohs_strat = ohs_ml["strategy"].values.astype(str)
ohs_vals = ohs_ml["f1_macro"].values
ax.bar(ohs_strat, ohs_vals, color=[C["blue"], C["green"], C["orange"]],
       width=0.5, edgecolor="white")
ax.set_ylabel("F1-macro")
ax.set_title("(C) OHSUMED (1,650 labels)", loc="left", fontweight="bold")
ax.set_ylim(0, max(ohs_vals) * 1.3)
for i, v in enumerate(ohs_vals):
    ax.text(i, v + 0.0002, f"{v:.4f}", ha="center", fontsize=7)

# ── (D) Model Robustness Box Plot ──
ax = axes[1, 1]
MODELS = ["NaiveBayes", "k-NN", "SVM", "LogisticReg",
          "RandomForest", "AdaBoost", "XGBoost"]
MODEL_L = {"NaiveBayes": "NB", "k-NN": "kNN", "SVM": "SVM",
           "LogisticReg": "LR", "RandomForest": "RF",
           "AdaBoost": "Ada", "XGBoost": "XGB"}

# Collect F1 per model across all features & datasets
box_data = []
for model in MODELS:
    vals = clf[(clf["model"] == model) & (clf["dataset"] == "pubmed_multilabel")]["f1_macro"].dropna()
    box_data.append(vals.values)

bp = ax.boxplot(box_data, labels=[MODEL_L[m] for m in MODELS],
                patch_artist=True, widths=0.6, showfliers=True,
                flierprops={"markersize": 3, "markerfacecolor": "gray"})
for patch, color in zip(bp["boxes"], [C["blue"]] * 3 + [C["green"]] * 2 + [C["orange"]] * 2):
    patch.set_facecolor(color)
    patch.set_alpha(0.6)

ax.set_ylabel("F1-macro (PML)")
ax.set_title("(D) Model Robustness Across Features", loc="left",
             fontweight="bold")

plt.subplots_adjust(left=0.08, right=0.96, top=0.95, bottom=0.08,
                    hspace=0.4, wspace=0.35)
save(fig, "fig4_multilabel")
print("Fig 4 done.")
