"""Fig 2 — Classical Algorithm Matrix: Complete Performance Landscape.

Merged from former fig2a + fig2b.

3×5 composite:
  Row 0: OHSUMED Heatmap | PML Heatmap | PGB Heatmap | — | colorbar
  Row 1: PML Top-5       | OHSUMED Top-5 | Feature Effectiveness (span 3 cols)
  Row 2: Best Perf       | Training Time | Performance vs Time (span 3 cols)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from plot_utils import save, C, PALETTE, sig_annotate, paired_ttest_from_folds

REPO = Path(__file__).resolve().parent.parent.parent

# ── Load data ──
df = pd.read_csv(REPO / "experiments/001_classical_matrix/results/classical_matrix_with_folds.csv")

DATASETS = {"ohsumed": "OHSUMED\n(1,650 labels)",
            "pubmed_multilabel": "PubMed-MultiLabel\n(16 labels)",
            "pgb": "PGB\n(3 labels)"}
FEATURES = ["tfidf", "biobert", "lda", "meta"]
FEAT_LABELS = {"tfidf": "TF-IDF", "biobert": "BioBERT",
               "lda": "LDA", "meta": "Meta"}
FEAT_COLORS = {"tfidf": C["blue"], "biobert": C["green"],
               "lda": C["orange"], "meta": C["purple"]}
MODELS = ["AdaBoost", "LogisticReg", "NaiveBayes", "RandomForest",
          "SVM", "XGBoost", "k-NN"]
MODEL_SHORT = {"AdaBoost": "Ada", "LogisticReg": "LR",
               "NaiveBayes": "NB", "RandomForest": "RF",
               "SVM": "SVM", "XGBoost": "XGB", "k-NN": "kNN"}


def top_n_per_dataset(dataset_key, n=5):
    sub = df[df["dataset"] == dataset_key].dropna(subset=["f1_macro"])
    return sub.nlargest(n, "f1_macro")


def _calc_p(fold_a, fold_b):
    """Paired t-test if folds match, else unpaired."""
    from scipy import stats as sp_stats
    if pd.isna(fold_a) or pd.isna(fold_b) or not str(fold_a).strip():
        return None
    try:
        a = np.array([float(x) for x in str(fold_a).split(",")])
        b = np.array([float(x) for x in str(fold_b).split(",")])
        if len(a) == len(b):
            _, p = sp_stats.ttest_rel(a, b)
        else:
            _, p = sp_stats.ttest_ind(a, b)
        return p
    except Exception:
        return None


# ═══════════════════════════════════════════════════════════════
# Build figure
# ═══════════════════════════════════════════════════════════════

fig = plt.figure(figsize=(13, 9))
gs = fig.add_gridspec(3, 5, width_ratios=[1, 1, 1, 2, 0.04],
                      height_ratios=[1.1, 0.7, 0.55],
                      hspace=0.4, wspace=0.1,
                      left=0.06, right=0.92, top=0.94, bottom=0.08)

# ═══════════════════════════════════════════════════════════════
# Row 0: Heatmaps (A-C) + colorbar
# ═══════════════════════════════════════════════════════════════

# ── Pivot data into 3 heatmap matrices ──
matrices = {}
for ds in DATASETS:
    sub = df[df["dataset"] == ds]
    mat = np.full((len(MODELS), len(FEATURES)), np.nan)
    for i, model in enumerate(MODELS):
        for j, feat in enumerate(FEATURES):
            row = sub[(sub["model"] == model) & (sub["feature"] == feat)]
            if not row.empty and "f1_macro" in row.columns:
                mat[i, j] = row["f1_macro"].values[0]
    matrices[ds] = mat

all_vals = np.concatenate([m.flatten() for m in matrices.values()])
all_vals = all_vals[~np.isnan(all_vals)]
vmin, vmax = 0, np.percentile(all_vals, 95) * 1.05

dataset_list = list(DATASETS.keys())
for col_idx, ds in enumerate(dataset_list):
    ax = fig.add_subplot(gs[0, col_idx])
    mat = matrices[ds]
    im = ax.imshow(mat, aspect="auto", cmap="YlOrRd",
                   norm=Normalize(vmin, vmax))
    for i in range(len(MODELS)):
        for j in range(len(FEATURES)):
            val = mat[i, j]
            if not np.isnan(val):
                color = "white" if val > (vmin + vmax) / 2 else "black"
                ax.text(j, i, f"{val:.3f}", ha="center", va="center",
                        fontsize=5.2, color=color)
    ax.set_xticks(range(len(FEATURES)))
    ax.set_xticklabels([FEAT_LABELS[f] for f in FEATURES], rotation=30,
                       ha="right", fontsize=7)
    ax.set_yticks(range(len(MODELS)))
    ax.set_yticklabels([MODEL_SHORT[m] for m in MODELS], fontsize=7)
    ax.set_title(f"({chr(65+col_idx)}) {DATASETS[ds]}",
                 loc="center", fontweight="bold", fontsize=8)

# Colorbar
cax = fig.add_subplot(gs[0, 4])
cb = plt.colorbar(im, cax=cax)
cb.set_label("F1-macro", fontsize=7)

# ═══════════════════════════════════════════════════════════════
# Row 1: (D) PML Top-5  (E) OHSUMED Top-5  (F) Feature Effectiveness
# ═══════════════════════════════════════════════════════════════

# (D) PML Top-5
ax = fig.add_subplot(gs[1, 0])
pml_top = top_n_per_dataset("pubmed_multilabel")
labels = [f"{FEAT_LABELS.get(r['feature'], r['feature'])}/{MODEL_SHORT.get(r['model'], r['model'])}"
          for _, r in pml_top.iterrows()]
vals = pml_top["f1_macro"].values
errs = pml_top["f1_macro_std"].values
colors = [FEAT_COLORS.get(r["feature"], C["gray"]) for _, r in pml_top.iterrows()]
ax.bar(range(len(labels)), vals, yerr=errs, color=colors, width=0.6,
       capsize=2, edgecolor="white", linewidth=0.3)

# Significance stair-step
if len(vals) > 1:
    bar_tops = [vals[k] + errs[k] for k in range(len(vals))]
    base_y = max(bar_tops)
    for i in range(1, len(vals)):
        p = _calc_p(pml_top.iloc[0].get("f1_macro_folds"),
                    pml_top.iloc[i].get("f1_macro_folds"))
        step = 0.04 * (i - 1)
        sig_annotate(ax, 0, i, base_y + step, p)
    ax.set_ylim(0, base_y + 0.04 * (len(vals) - 2) + (base_y * 0.15))
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=6)
ax.set_ylabel("F1-macro", fontsize=6.5)
ax.set_title("(D) PML — Top 5", loc="left", fontweight="bold", fontsize=7.5)

# (E) OHSUMED Top-5
ax = fig.add_subplot(gs[1, 1])
ohs_top = top_n_per_dataset("ohsumed")
labels = [f"{FEAT_LABELS.get(r['feature'], r['feature'])}/{MODEL_SHORT.get(r['model'], r['model'])}"
          for _, r in ohs_top.iterrows()]
vals = ohs_top["f1_macro"].values
errs = ohs_top["f1_macro_std"].values
colors = [FEAT_COLORS.get(r["feature"], C["gray"]) for _, r in ohs_top.iterrows()]
ax.bar(range(len(labels)), vals, yerr=errs, color=colors, width=0.6,
       capsize=2, edgecolor="white", linewidth=0.3)
# No significance (no CV data for these OHSUMED rows)
ax.set_xticks(range(len(labels)))
ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=6)
ax.set_ylabel("F1-macro", fontsize=6.5)
ax.set_title("(E) OHSUMED — Top 5", loc="left", fontweight="bold", fontsize=7.5)

# (F) Feature Effectiveness
ax = fig.add_subplot(gs[1, 2:5])
feats = ["tfidf", "biobert", "lda", "meta"]
ds_order = ["pubmed_multilabel", "ohsumed", "pgb"]
x = np.arange(len(feats))
width = 0.22
DS_COLORS = [C["blue"], C["green"], C["orange"]]
for idx, ds in enumerate(ds_order):
    sub = df[df["dataset"] == ds]
    best_per_feat = []
    for feat in feats:
        sf = sub[sub["feature"] == feat].dropna(subset=["f1_macro"])
        best_per_feat.append(sf["f1_macro"].max() if not sf.empty else 0)
    ax.bar(x + idx * width, best_per_feat, width,
           color=DS_COLORS[idx],
           label={"pubmed_multilabel": "PML", "ohsumed": "OHSUMED",
                  "pgb": "PGB"}[ds],
           edgecolor="white", linewidth=0.3)
ax.set_xticks(x + width)
ax.set_xticklabels([FEAT_LABELS[f] for f in feats], fontsize=7)
ax.set_ylabel("Best F1-macro", fontsize=6.5)
ax.set_title("(F) Feature Effectiveness", loc="left", fontweight="bold", fontsize=7.5)
ax.legend(fontsize=6, frameon=False, ncol=3)

# ═══════════════════════════════════════════════════════════════
# Row 2: (G) Best Perf  (H) Training Time  (I) Perf vs Time
# ═══════════════════════════════════════════════════════════════

# (G) Best Performance per Dataset
ax = fig.add_subplot(gs[2, 0])
best_per_ds = {}
for ds in DATASETS:
    sub = df[df["dataset"] == ds]
    if not sub.empty:
        best = sub.loc[sub["f1_macro"].idxmax()]
        best_per_ds[ds] = best["f1_macro"]
ds_names_short = ["OHSUMED", "PML", "PGB"]
bars_g = ax.bar(ds_names_short, [best_per_ds[k] for k in dataset_list],
                color=DS_COLORS, width=0.5)
ax.set_ylabel("Best F1-macro", fontsize=6.5)
ax.set_title("(G) Best per Dataset", loc="left", fontweight="bold", fontsize=7.5)
for bar, val in zip(bars_g, [best_per_ds[k] for k in dataset_list]):
    ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
            f"{val:.3f}", ha="center", fontsize=6.5)

# (H) Training Time
ax = fig.add_subplot(gs[2, 1])
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
tdf["label"] = tdf["ds"].map({"ohsumed": "OHSU", "pubmed_multilabel": "PML",
                              "pgb": "PGB"}) + "/" + tdf["feat"].map(FEAT_LABELS)
tdf = tdf.sort_values("time", ascending=True)
ax.barh(range(len(tdf)), tdf["time"].values, color=C["blue"], height=0.6)
ax.set_yticks(range(len(tdf)))
ax.set_yticklabels(tdf["label"].values, fontsize=5.5)
ax.set_xlabel("Time (s, log)", fontsize=6.5)
ax.set_xscale("log")
ax.set_title("(H) Training Time", loc="left", fontweight="bold", fontsize=7.5)

# (I) Performance vs Training Time
ax = fig.add_subplot(gs[2, 2:5])
for ds, marker in [("ohsumed", "o"), ("pubmed_multilabel", "s"), ("pgb", "^")]:
    sub = df[df["dataset"] == ds].dropna(subset=["f1_macro", "train_time_s"])
    for feat, color in FEAT_COLORS.items():
        sf = sub[sub["feature"] == feat]
        if not sf.empty:
            ax.scatter(sf["train_time_s"], sf["f1_macro"], c=color,
                       marker=marker, s=12, alpha=0.7, edgecolors="none")

ax.set_xscale("log")
ax.set_xlabel("Training Time (s, log scale)", fontsize=6.5)
ax.set_ylabel("F1-macro", fontsize=6.5)
ax.set_title("(I) Performance vs. Time", loc="left", fontweight="bold", fontsize=7.5)

# Dual legend
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
leg_i = ax.legend(handles=ds_legend, loc="upper right", fontsize=5.5,
                  frameon=False, title="Dataset", title_fontsize=6)
ax.add_artist(leg_i)
ax.legend(handles=feat_legend, loc="upper left", fontsize=5.5,
          frameon=False, title="Feature", title_fontsize=6)

save(fig, "fig2_classical_matrix")
print("Fig 2 done.")
