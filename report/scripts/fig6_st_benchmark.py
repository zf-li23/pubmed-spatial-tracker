"""Fig 6 — Spatial Tracker Benchmark + Category Co-occurrence Network.

2×2 composite:
  (A) Three Methods comparison with significance
  (B) Confusion Matrices (3 subpanels)
  (C) Accuracy vs F1-macro dot plot
  (D) Category Co-occurrence Network
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
from plot_utils import save, C, PALETTE, sig_annotate, paired_ttest_from_folds

# ── Load data ──
st = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                 "experiments/006_st_benchmark/results/st_benchmark.csv")
ann = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                  "data/spatial_tracker/annotated_articles.csv")

# ═══════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(9.5, 8))
gs = fig.add_gridspec(2, 3, hspace=0.45, wspace=0.4,
                      left=0.07, right=0.96, top=0.95, bottom=0.08)

# ── (A) Three Methods Bar Chart ──
ax = fig.add_subplot(gs[0, 0])
methods = [r["method"] for _, r in st.iterrows()]
f1_vals = st["f1_macro"].values
f1_errs = st["f1_macro_std"].values
colors = [C["blue"], C["green"], C["orange"]]
bars = ax.bar(methods, f1_vals, yerr=f1_errs, color=colors, width=0.5,
              capsize=3, edgecolor="white")
ax.set_ylabel("F1-macro")
ax.set_title("(A) ST Benchmark", loc="left", fontweight="bold")
ax.set_xticklabels(methods, rotation=20, ha="right", fontsize=6.5)

# Significance (using per-fold data if available)
for i in range(len(methods)):
    for j in range(i + 1, len(methods)):
        fold_i = st.iloc[i].get("f1_macro_folds", None)
        fold_j = st.iloc[j].get("f1_macro_folds", None)
        if fold_i is not None and fold_j is not None and pd.notna(fold_i) and pd.notna(fold_j):
            p = paired_ttest_from_folds(str(fold_i), str(fold_j))
            y_max = max(f1_vals[i] + f1_errs[i], f1_vals[j] + f1_errs[j]) * 1.03
            sig_annotate(ax, i, j, y_max, p)
        else:
            sig_annotate(ax, i, j,
                         max(f1_vals[i] + f1_errs[i], f1_vals[j] + f1_errs[j]) * 1.03,
                         None)

# ── (B) Confusion Matrices (placeholder — need per-fold predictions) ──
ax = fig.add_subplot(gs[0, 1:])
ax.text(0.5, 0.5, "Confusion Matrices\n(requires per-fold predictions\nfrom cluster re-run)",
        ha="center", va="center", fontsize=9, color="gray", transform=ax.transAxes)
ax.set_title("(B) Confusion Matrices (pending)", loc="left", fontweight="bold")

# ── (C) Accuracy vs F1-macro ──
ax = fig.add_subplot(gs[1, 0])
acc_vals = st["accuracy"].values
for i, method in enumerate(methods):
    ax.scatter(acc_vals[i], f1_vals[i], color=colors[i], s=60, zorder=5,
               edgecolors="white", linewidth=0.5)
    ax.annotate(method.split("+")[-1] if "+" in method else method,
                (acc_vals[i], f1_vals[i]),
                fontsize=6.5, ha="center", va="bottom",
                xytext=(0, 6), textcoords="offset points")
ax.set_xlabel("Accuracy")
ax.set_ylabel("F1-macro")
ax.set_title("(C) Accuracy vs F1-macro", loc="left", fontweight="bold")

# ── (D) Category Co-occurrence Network ──
ax = fig.add_subplot(gs[1, 1:])

# Build co-occurrence matrix
def split_col(series):
    items = []
    for v in series.dropna():
        for x in str(v).split("; "):
            items.append(x.strip())
    return items

all_tags = split_col(ann["tags"])
tag_counts = Counter(all_tags)
top_tags = [t for t, _ in tag_counts.most_common(10)]

# Co-occurrence
cooc = np.zeros((len(top_tags), len(top_tags)))
for _, row in ann.iterrows():
    tags = set(str(row["tags"]).split("; ")) if pd.notna(row["tags"]) else set()
    for i, t1 in enumerate(top_tags):
        for j, t2 in enumerate(top_tags):
            if i < j and t1 in tags and t2 in tags:
                cooc[i, j] += 1
                cooc[j, i] += 1

# Diag = frequency
for i, t in enumerate(top_tags):
    cooc[i, i] = tag_counts[t]

# Normalize for edges
edge_mat = cooc.copy()
np.fill_diagonal(edge_mat, 0)
edge_max = edge_mat.max()

# Draw network
node_x = []
node_y = []
radius = 1.0
for i in range(len(top_tags)):
    angle = 2 * np.pi * i / len(top_tags) - np.pi / 2
    node_x.append(radius * np.cos(angle))
    node_y.append(radius * np.sin(angle))

# Edges
for i in range(len(top_tags)):
    for j in range(i + 1, len(top_tags)):
        if cooc[i, j] > 0:
            lw = max(0.2, cooc[i, j] / edge_max * 3)
            ax.plot([node_x[i], node_x[j]], [node_y[i], node_y[j]],
                    color="gray", lw=lw, alpha=0.4, zorder=1)

# Nodes
sizes = [max(20, tag_counts[t] / tag_counts.most_common(1)[0][1] * 300)
         for t in top_tags]
ax.scatter(node_x, node_y, s=sizes, c=C["blue"], alpha=0.8,
           edgecolors="white", linewidth=0.5, zorder=5)

# Labels
for i, t in enumerate(top_tags):
    ax.annotate(t.replace("Spatial ", "").replace(" &", "\n&"),
                (node_x[i], node_y[i]),
                fontsize=5.5, ha="center", va="center",
                color="white" if tag_counts[t] > 500 else "black",
                fontweight="bold")

ax.set_xlim(-1.5, 1.5); ax.set_ylim(-1.5, 1.5)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title("(D) Tag Co-occurrence Network", loc="left", fontweight="bold")

save(fig, "fig6_st_benchmark")
print("Fig 6 done.")
