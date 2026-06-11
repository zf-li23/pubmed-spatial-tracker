"""Fig 7 — Transfer Learning.

1×2 composite:
  (A) Full Experiment Waterfall
  (B) Pre-training Cost-Benefit (training time breakdown)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from plot_utils import save, C, PALETTE

# ── Load data ──
tl = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                 "experiments/007_transfer_learning/results/transfer_learning.csv")
clf = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                  "experiments/001_classical_matrix/results/classical_matrix.csv")

# ═══════════════════════════════════════════════════════════════
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

# ── (A) Waterfall Chart ──
ax = axes[0]
# Order: zero-shot → baselines → graph → fine-tuned
exp_order = ["A1", "A2", "A4", "A5", "B3", "B1", "B2", "D2", "D1", "C2", "C1"]
# Filter to available
available = [e for e in exp_order if e in tl["exp_id"].values]
f1_map = {r["exp_id"]: r["f1_macro"] for _, r in tl.iterrows()}
vals = [f1_map[e] for e in available]

# Short descriptive labels
label_map = {
    "A1": "Zero: OHSU→ST\n(LR)", "A2": "Zero: PML→ST\n(LR)",
    "A4": "Zero: PML→ST\n(XGB)", "A5": "Zero: PGB→ST\n(LR)",
    "B1": "ST→ST\n(LR)", "B2": "ST→ST\n(MLP)", "B3": "ST→ST\n(XGB)",
    "C1": "PML→ST\n(MLP+FT)", "C2": "OHSU→ST\n(MLP+FT)",
    "D1": "GCN", "D2": "GraphSAGE",
}
labels_short = [label_map.get(e, e) for e in available]

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

ax.bar(range(len(labels_short)), vals, color=colors, width=0.5, edgecolor="white")
ax.set_xticks(range(len(labels_short)))
ax.set_xticklabels(labels_short, fontsize=5.5, rotation=25, ha="right")
ax.set_ylabel("F1-macro")
ax.set_title("(A) Transfer Learning Waterfall", loc="left", fontweight="bold")
ax.axhline(y=0, color="black", lw=0.3)

# Group annotation
group_texts = [("Zero-shot", 1.5, C["red"]), ("Baseline", 5, C["blue"]),
               ("Graph", 7.5, C["purple"]), ("Fine-tune", 9.5, C["green"])]
for txt, x_pos, clr in group_texts:
    ax.text(x_pos, ax.get_ylim()[1]*0.95, txt, fontsize=6, fontweight="bold",
            color=clr, ha="center", va="top")

# ── (B) Pre-training Cost-Benefit ──
ax = axes[1]
# Training time breakdown
b2_time = tl[tl["exp_id"]=="B2"]["train_time_s"].values[0]
c1_pretrain = tl[tl["exp_id"]=="C1"]["pretrain_time_s"].values[0]
c1_finetune = tl[tl["exp_id"]=="C1"]["finetune_time_s"].values[0]
c2_pretrain = tl[tl["exp_id"]=="C2"]["pretrain_time_s"].values[0]
c2_finetune = tl[tl["exp_id"]=="C2"]["finetune_time_s"].values[0]
c1_total = c1_pretrain + c1_finetune
c2_total = c2_pretrain + c2_finetune

methods_t = ["ST→ST", "PML→ST", "OHSU→ST"]
bars_b2 = ax.barh(0, b2_time, height=0.4, color=C["blue"], edgecolor="white", label="Train")
bars_c1_pretrain = ax.barh(1, c1_pretrain, height=0.4, color=C["gray"], edgecolor="white", label="Pre-train")
bars_c1_finetune = ax.barh(1, c1_finetune, height=0.4, left=c1_pretrain, color=C["green"], edgecolor="white", label="Fine-tune")
bars_c2_pretrain = ax.barh(2, c2_pretrain, height=0.4, color=C["gray"], edgecolor="white")
bars_c2_finetune = ax.barh(2, c2_finetune, height=0.4, left=c2_pretrain, color=C["orange"], edgecolor="white")

# F1 annotations
f1_b2 = f1_map.get("B2", 0)
f1_c1 = f1_map.get("C1", 0)
f1_c2 = f1_map.get("C2", 0)
for y_pos, total, f1_val, clr in [
    (0, b2_time, f1_b2, C["blue"]),
    (1, c1_total, f1_c1, C["green"]),
    (2, c2_total, f1_c2, C["orange"]),
]:
    ax.text(total + 15, y_pos, f"F1={f1_val:.4f}", va="center", fontsize=6.5,
            color=clr, fontweight="bold")

ax.set_yticks(range(3))
ax.set_yticklabels(methods_t, fontsize=7)
ax.set_xlabel("Time (s)")
ax.set_title("(B) Pre-training Cost vs. Benefit", loc="left", fontweight="bold")
ax.legend(fontsize=5.5, frameon=False, loc="lower right")

plt.subplots_adjust(left=0.07, right=0.97, top=0.92, bottom=0.15, wspace=0.3)
save(fig, "fig7_transfer_learning")
print("Fig 7 done.")
save(fig, "fig7_transfer_learning")
print("Fig 7 done.")
