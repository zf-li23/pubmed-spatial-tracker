"""Fig 3 — Deep Learning & Unsupervised Methods.

2×2 composite:
  (A) BioBERT+MLP vs Best Classical per dataset
  (B) LDA Clustering NMI
  (C) Unsupervised vs Supervised gap (dual-axis)
  (D) Cost-Benefit Pareto Frontier
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from plot_utils import save, C, PALETTE

# ── Load data ──
bmlp = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                   "experiments/002_biobert_mlp/results/biobert_mlp.csv")
lda = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                  "experiments/003_lda_cluster/results/lda_cluster.csv")
clf = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                  "experiments/001_classical_matrix/results/classical_matrix.csv")

# Dedup LDA (2 duplicate runs per dataset)
lda = lda.drop_duplicates(subset=["dataset"])

# Best classical per dataset from Exp 001
best_classical = {}
for ds in ["ohsumed", "pubmed_multilabel", "pgb"]:
    sub = clf[clf["dataset"] == ds].dropna(subset=["f1_macro"])
    if not sub.empty:
        best_classical[ds] = sub["f1_macro"].max()

# ═══════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 2, figsize=(9, 7))

# ── (A) BioBERT+MLP vs Best Classical ──
ax = axes[0, 0]
datasets = ["ohsumed", "pubmed_multilabel", "pgb"]
ds_labels = ["OHSUMED", "PML", "PGB"]
ds_colors = [C["blue"], C["green"], C["orange"]]
x = np.arange(len(datasets))
w = 0.3
bmlp_vals = []
for ds in datasets:
    row = bmlp[bmlp["dataset"] == ds]
    bmlp_vals.append(row["f1_macro"].values[0] if not row.empty else 0)
classical_vals = [best_classical.get(ds, 0) for ds in datasets]

for i in range(len(datasets)):
    ax.bar(x[i] - w/2, classical_vals[i], w, color=ds_colors[i],
           edgecolor="white", linewidth=0.5, alpha=0.9)
    ax.bar(x[i] + w/2, bmlp_vals[i], w, color=ds_colors[i],
           edgecolor="white", linewidth=0.5, alpha=0.9, hatch="////")

# Legend handles
from matplotlib.patches import Patch
legend_elements_a = [
    Patch(facecolor="gray", edgecolor="white", label="Best Classical"),
    Patch(facecolor="gray", edgecolor="white", hatch="////", label="BioBERT+MLP"),
]
ax.legend(handles=legend_elements_a, fontsize=6.5, frameon=False, ncol=2)

# Annotate tiny OHSUMED MLP value
if bmlp_vals[0] < 0.01:
    ax.text(0 + w/2, bmlp_vals[0] + 0.002, f"{bmlp_vals[0]:.4f}",
            ha="center", fontsize=6.5, color=C["blue"])

ax.set_xticks(x)
ax.set_xticklabels(ds_labels, fontsize=7.5)
ax.set_ylabel("F1-macro")
ax.set_title("(A) BioBERT+MLP vs Best Classical", loc="left", fontweight="bold")

# ── (B) LDA Clustering NMI ──
ax = axes[0, 1]
lda_vals = [float(lda[lda["dataset"] == ds]["nmi"].values[0])
            if not lda[lda["dataset"] == ds].empty else 0
            for ds in datasets]
colors = [C["blue"], C["green"], C["orange"]]
ax.bar(ds_labels, lda_vals, color=colors, width=0.5, edgecolor="white")
for i, v in enumerate(lda_vals):
    ax.text(i, v + 0.01, f"{v:.3f}", ha="center", fontsize=7)
ax.set_ylabel("NMI")
ax.set_title("(B) LDA Clustering Quality (NMI)", loc="left", fontweight="bold")

# ── (C) Unsupervised vs Supervised Gap ──
ax = axes[1, 0]
ax2 = ax.twinx()
ax.bar(np.arange(len(datasets)) - 0.15, lda_vals, 0.3,
       color=C["purple"], label="NMI (unsupervised)", edgecolor="white")
ax.set_ylabel("NMI")
ax.set_ylim(0, max(lda_vals) * 1.6)

ax2.bar(np.arange(len(datasets)) + 0.15,
        [best_classical.get(ds, 0) for ds in datasets], 0.3,
        color=C["green"], alpha=0.6, label="F1 (supervised)", edgecolor="white")
ax2.set_ylabel("F1-macro (best classical)", color=C["green"])
max_f1 = max([best_classical.get(ds, 0) for ds in datasets])
ax2.set_ylim(0, max_f1 * 1.6)

ax.set_xticks(range(len(datasets)))
ax.set_xticklabels(ds_labels)
ax.set_title("(C) Unsupervised vs Supervised", loc="left", fontweight="bold")

# Combined legend
lines1, labels1 = ax.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax.legend(lines1 + lines2, labels1 + labels2, fontsize=6, frameon=False, loc="upper left")

# ── (D) Cost-Benefit Landscape ──
ax = axes[1, 1]
from matplotlib.lines import Line2D

# Collect F1 + time from Exp 001 (classical matrix)
for ds_name, ds_key, marker, ds_color in [
    ("OHSUMED", "ohsumed", "o", C["blue"]),
    ("PML", "pubmed_multilabel", "s", C["green"]),
    ("PGB", "pgb", "^", C["orange"]),
]:
    sub = clf[clf["dataset"] == ds_key].dropna(subset=["f1_macro", "train_time_s"])
    ax.scatter(sub["train_time_s"], sub["f1_macro"],
               c=ds_color, marker=marker, s=18, alpha=0.5,
               edgecolors="none", label=ds_name)

# Exp 006 ST points
st = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                 "experiments/006_st_benchmark/results/st_benchmark.csv")
ax.scatter(st["train_time_s"], st["f1_macro"],
           c=C["red"], marker="D", s=30, alpha=0.8,
           edgecolors="black", linewidth=0.3, label="ST")

# Exp 002 BioBERT+MLP points
for _, r in bmlp.iterrows():
    ds_label = r["dataset"]
    c_map = {"ohsumed": C["blue"], "pubmed_multilabel": C["green"], "pgb": C["orange"]}
    ax.scatter(r["train_time_s"], r["f1_macro"],
               c=c_map.get(ds_label, "gray"), marker="v", s=35, alpha=0.9,
               edgecolors="black", linewidth=0.5, label=f"BioBERT+MLP")

# Best point label
all_times = []
all_f1s = []
for _, r in clf.dropna(subset=["f1_macro", "train_time_s"]).iterrows():
    all_times.append(r["train_time_s"]); all_f1s.append(r["f1_macro"])
for _, r in st.iterrows():
    all_times.append(r["train_time_s"]); all_f1s.append(r["f1_macro"])
for _, r in bmlp.iterrows():
    if "train_time_s" in r and "f1_macro" in r:
        all_times.append(r["train_time_s"]); all_f1s.append(r["f1_macro"])

best_idx = np.argmax(all_f1s)
ax.annotate(f"Best F1={all_f1s[best_idx]:.3f}",
            (all_times[best_idx], all_f1s[best_idx]),
            fontsize=6, ha="center", va="bottom",
            xytext=(0, 8), textcoords="offset points")

# Legend
ds_legend = [
    Line2D([0], [0], marker="o", color="w", markerfacecolor=C["blue"],
           markersize=5, label="OHSUMED (Exp 001)"),
    Line2D([0], [0], marker="s", color="w", markerfacecolor=C["green"],
           markersize=5, label="PML (Exp 001)"),
    Line2D([0], [0], marker="^", color="w", markerfacecolor=C["orange"],
           markersize=5, label="PGB (Exp 001)"),
    Line2D([0], [0], marker="D", color="w", markerfacecolor=C["red"],
           markersize=5, label="ST (Exp 006)"),
    Line2D([0], [0], marker="v", color="w", markerfacecolor="gray",
           markersize=5, label="BioBERT+MLP (Exp 002)"),
]
ax.legend(handles=ds_legend, fontsize=5.5, frameon=False, loc="upper left", ncol=1)

ax.set_xscale("log")
ax.set_xlabel("Training Time (s, log scale)")
ax.set_ylabel("F1-macro")
ax.set_title("(D) Cost-Benefit Landscape", loc="left", fontweight="bold")

plt.subplots_adjust(left=0.08, right=0.96, top=0.95, bottom=0.08,
                    hspace=0.4, wspace=0.35)
save(fig, "fig3_dl_unsupervised")
print("Fig 3 done.")
