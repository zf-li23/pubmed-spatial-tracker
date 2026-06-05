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
x = np.arange(len(datasets))
w = 0.3
bmlp_vals = []
for ds in datasets:
    row = bmlp[bmlp["dataset"] == ds]
    bmlp_vals.append(row["f1_macro"].values[0] if not row.empty else 0)
classical_vals = [best_classical.get(ds, 0) for ds in datasets]

ax.bar(x - w/2, classical_vals, w, color=C["green"], label="Best Classical",
       edgecolor="white")
ax.bar(x + w/2, bmlp_vals, w, color=C["blue"], label="BioBERT+MLP",
       edgecolor="white")
ax.set_xticks(x)
ax.set_xticklabels(ds_labels)
ax.set_ylabel("F1-macro")
ax.set_title("(A) BioBERT+MLP vs Best Classical", loc="left", fontweight="bold")
ax.legend(fontsize=7, frameon=False)

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
ax.bar(np.arange(len(datasets)) + 0.15,
       [best_classical.get(ds, 0) for ds in datasets], 0.3,
       color=C["green"], label="F1 (supervised)", edgecolor="white")
ax.set_xticks(range(len(datasets)))
ax.set_xticklabels(ds_labels)
ax.set_ylabel("Score")
ax.set_title("(C) Unsupervised vs Supervised", loc="left", fontweight="bold")
lines1, labels1 = ax.get_legend_handles_labels()
ax.legend(lines1, labels1, fontsize=6, frameon=False, loc="upper left")

# ── (D) Cost-Benefit Pareto ──
ax = axes[1, 1]
# Collect F1 + time from Exp 001 + 006 + 002
points = []
for ds, marker, ds_color in [("ohsumed", "o", C["blue"]),
                               ("pubmed_multilabel", "s", C["green"]),
                               ("pgb", "^", C["orange"])]:
    sub = clf[clf["dataset"] == ds].dropna(subset=["f1_macro", "train_time_s"])
    for _, r in sub.iterrows():
        points.append((r["train_time_s"], r["f1_macro"], ds, marker, ds_color))

# Add Exp 006 ST points
st = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                 "experiments/006_st_benchmark/results/st_benchmark.csv")
for _, r in st.iterrows():
    points.append((r["train_time_s"], r["f1_macro"], "ST", "D", C["red"]))

# Add Exp 002 points
for _, r in bmlp.iterrows():
    if "train_time_s" in r and "f1_macro" in r:
        points.append((r["train_time_s"], r["f1_macro"],
                       r["dataset"], "v", C["purple"]))

times = np.array([p[0] for p in points])
f1s = np.array([p[1] for p in points])
colors = [p[4] for p in points]
markers = [p[3] for p in points]

# Plot
for ds_name, m in [("OHSUMED", "o"), ("PML", "s"), ("PGB", "^"), ("ST", "D")]:
    idxs = [i for i, p in enumerate(points) if p[4] == {
        "OHSUMED": C["blue"], "PML": C["green"], "PGB": C["orange"],
        "ST": C["red"],
        "ohsumed": C["blue"], "pubmed_multilabel": C["green"],
        "pgb": C["orange"]
    }.get(p[2], p[4]) if p[3] == m or ds_name == p[2].replace("pubmed_multilabel", "PML").replace("ohsumed", "OHSUMED").replace("pgb", "PGB")]
    # Simpler: just plot all
    pass

# Specific points for BioBERT models
ax.scatter(times, f1s, c=colors, s=20, alpha=0.6, edgecolors="none")

# Labels for key methods
best_idx = np.argmax(f1s)
ax.annotate(f"Best:\nF1={f1s[best_idx]:.3f}",
            (times[best_idx], f1s[best_idx]),
            fontsize=6, ha="center", va="bottom",
            xytext=(0, 8), textcoords="offset points")

ax.set_xscale("log")
ax.set_xlabel("Training Time (s, log scale)")
ax.set_ylabel("F1-macro")
ax.set_title("(D) Cost-Benefit Landscape", loc="left", fontweight="bold")

plt.subplots_adjust(left=0.08, right=0.96, top=0.95, bottom=0.08,
                    hspace=0.4, wspace=0.35)
save(fig, "fig3_dl_unsupervised")
print("Fig 3 done.")
