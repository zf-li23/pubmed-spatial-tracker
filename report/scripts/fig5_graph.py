"""Fig 5 — Graph-based Methods + Label Complexity.

2×2 composite:
  (A) PGB: Node2Vec + 6 classifiers
  (B) PGB: GCN vs GraphSAGE vs Node2Vec+best
  (C) ST: Graph methods on k-NN graph
  (D) Label Complexity vs F1 — the fundamental insight
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats as sp_stats
from plot_utils import save, C, PALETTE

# ── Load ──
gm = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                 "experiments/005_graph_models/results/graph_models.csv")
tl = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                 "experiments/007_transfer_learning/results/transfer_learning.csv")
clf = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                  "experiments/001_classical_matrix/results/classical_matrix.csv")

# ═══════════════════════════════════════════════════════════════
fig, axes = plt.subplots(2, 2, figsize=(9.5, 7))

# ── (A) Node2Vec + Classifiers ──
ax = axes[0, 0]
n2v = gm[gm["feature"] == "node2vec"]
n2v_models = []
n2v_f1 = []
for _, r in n2v.iterrows():
    label = r["model"].replace("Node2Vec+", "")
    n2v_models.append(label)
    n2v_f1.append(r["f1_macro"])

ax.bar(n2v_models, n2v_f1, color=C["blue"], width=0.5, edgecolor="white")
ax.set_ylabel("F1-macro")
ax.set_title("(A) Node2Vec + Classifiers (PGB)", loc="left", fontweight="bold")
ax.tick_params(axis="x", rotation=20)

# ── (B) Graph Method Comparison (PGB) ──
ax = axes[0, 1]
gcn = gm[gm["model"] == "GCN"]
sage = gm[gm["model"] == "GraphSAGE"]
n2v_best = n2v["f1_macro"].max()
gcn_f1 = gcn["f1_macro"].values[0] if not gcn.empty else 0
sage_f1 = sage["f1_macro"].values[0] if not sage.empty else 0

methods_g = ["GCN", "GraphSAGE", "Node2Vec\n(best)"]
g_vals = [gcn_f1, sage_f1, n2v_best]
g_colors = [C["green"], C["orange"], C["blue"]]
bars = ax.bar(methods_g, g_vals, color=g_colors, width=0.5, edgecolor="white")
for bar, val in zip(bars, g_vals):
    ax.text(bar.get_x() + bar.get_width()/2, val + 0.005, f"{val:.4f}",
            ha="center", fontsize=7, fontweight="bold")
ax.set_ylabel("F1-macro")
ax.set_title("(B) Graph Methods (PGB)", loc="left", fontweight="bold")

# ── (C) ST Graph ──
ax = axes[1, 0]
# From transfer_learning.py D1, D2
d1 = tl[tl["exp_id"] == "D1"]
d2 = tl[tl["exp_id"] == "D2"]
b1 = tl[tl["exp_id"] == "B1"]
st_gcn = d1["f1_macro"].values[0] if not d1.empty else 0
st_sage = d2["f1_macro"].values[0] if not d2.empty else 0
st_baseline = b1["f1_macro"].values[0] if not b1.empty else 0

methods_st = ["BioBERT+LR\n(baseline)", "GCN\n(k-NN graph)", "GraphSAGE\n(k-NN graph)"]
st_vals = [st_baseline, st_gcn, st_sage]
st_colors = [C["gray"], C["green"], C["orange"]]
bars = ax.bar(methods_st, st_vals, color=st_colors, width=0.5, edgecolor="white")
for bar, val in zip(bars, st_vals):
    ax.text(bar.get_x() + bar.get_width()/2, val + 0.005, f"{val:.4f}",
            ha="center", fontsize=7, fontweight="bold")
ax.set_ylabel("F1-macro")
ax.set_title("(C) Graph Methods on ST (k-NN graph)", loc="left",
             fontweight="bold")

# ── (D) Label Complexity vs F1 ──
ax = axes[1, 1]
# Collect best F1 per (dataset, feature) across all models
label_counts = {"ohsumed": 1650, "pubmed_multilabel": 16, "pgb": 3,
                "spatial_tracker": 6}
best_per_ds_feat = []
for ds, n_labels in label_counts.items():
    df_key = ds if ds != "spatial_tracker" else None
    if df_key:
        for feat in ["tfidf", "biobert", "lda", "meta"]:
            sub = clf[(clf["dataset"] == df_key) &
                      (clf["feature"] == feat)].dropna(subset=["f1_macro"])
            if not sub.empty:
                best_per_ds_feat.append((n_labels, sub["f1_macro"].max(), feat))

# Add ST from Exp 006
st_vals_006 = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                          "experiments/006_st_benchmark/results/st_benchmark.csv")
for _, r in st_vals_006.iterrows():
    best_per_ds_feat.append((6, r["f1_macro"], r["method"]))

x_vals = [x[0] for x in best_per_ds_feat]
y_vals = [x[1] for x in best_per_ds_feat]
feat_colors = {"tfidf": C["blue"], "biobert": C["green"],
               "lda": C["orange"], "meta": C["purple"]}
colors_f = [feat_colors.get(x[2], C["gray"]) if x[2] not in
            ["TF-IDF+SVM", "BioBERT+LR", "BioBERT+MLP"] else C["red"]
            for x in best_per_ds_feat]

ax.scatter(x_vals, y_vals, c=colors_f, s=30, alpha=0.7, edgecolors="none")

# Fit log-linear trend
log_x = np.log10(x_vals)
slope, intercept, r_val, _, _ = sp_stats.linregress(log_x, y_vals)
x_line = np.logspace(np.log10(min(x_vals)), np.log10(max(x_vals)), 100)
y_line = slope * np.log10(x_line) + intercept
ax.plot(x_line, y_line, "--", color="gray", lw=0.8, alpha=0.6)

ax.set_xscale("log")
ax.set_xlabel("Number of Labels (log scale)")
ax.set_ylabel("Best F1-macro")
ax.set_title(f"(D) Label Complexity vs F1 (r={r_val:.2f})", loc="left",
             fontweight="bold")

plt.subplots_adjust(left=0.08, right=0.97, top=0.95, bottom=0.08,
                    hspace=0.45, wspace=0.35)
save(fig, "fig5_graph")
print("Fig 5 done.")
