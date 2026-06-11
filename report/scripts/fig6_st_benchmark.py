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
from plot_utils import save, C, PALETTE, sig_annotate

# ── Load data ──
st = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                 "experiments/006_st_benchmark/results/st_benchmark.csv")
ann = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                  "data/spatial_tracker/annotated_articles.csv")

# ═══════════════════════════════════════════════════════════════
fig = plt.figure(figsize=(9.5, 8))
gs = fig.add_gridspec(2, 3, hspace=0.45, wspace=0.4,
                      left=0.07, right=0.96, top=0.95, bottom=0.15)

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
ax.set_xticks(range(len(methods)))
ax.set_xticklabels(methods, rotation=20, ha="right", fontsize=6.5)

# Significance: paired t-test when folds match, unpaired (independent) when not
def _calc_p(fold_str_a, fold_str_b):
    """Try paired t-test first (same n_folds), fall back to independent t-test."""
    from scipy import stats as sp_stats
    if pd.isna(fold_str_a) or pd.isna(fold_str_b) or not str(fold_str_a).strip():
        return None
    try:
        a = np.array([float(x) for x in str(fold_str_a).split(",")])
        b = np.array([float(x) for x in str(fold_str_b).split(",")])
        if len(a) == len(b):
            _, p = sp_stats.ttest_rel(a, b)  # paired
        else:
            _, p = sp_stats.ttest_ind(a, b)  # unpaired (Welch's)
        return p
    except:
        return None

# Uniform bracket height for significance, stair-step for overlap
bar_tops = [f1_vals[k] + f1_errs[k] for k in range(len(methods))]
base_y = max(bar_tops)
for i in range(len(methods)):
    for j in range(i + 1, len(methods)):
        fold_i = st.iloc[i].get("f1_macro_folds", None)
        fold_j = st.iloc[j].get("f1_macro_folds", None)
        p = _calc_p(fold_i, fold_j)
        step = 0.04 * (abs(j - i) - 1)
        sig_annotate(ax, i, j, base_y + step, p)
ax.set_ylim(0, base_y + 0.04 * (len(methods) - 1) + (base_y * 0.15))

# ── (B) Feature Importance: Top TF-IDF Terms per Category ──
ax = fig.add_subplot(gs[0, 1:])

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC

texts = ann["title"].fillna("")
vec = TfidfVectorizer(max_features=2000, stop_words="english", sublinear_tf=True)
X_title = vec.fit_transform(texts)
feature_names = vec.get_feature_names_out()

cat_labels = ["Research", "Protocol", "Technology", "Data Resource",
              "Benchmark", "Review"]
cat_to_idx = {c: i for i, c in enumerate(cat_labels)}
y_num = np.array([cat_to_idx.get(c, -1) for c in ann["category"].values])
valid = y_num >= 0
X_title, y_num = X_title[valid], y_num[valid]

clf = LinearSVC(C=1.0, dual="auto", random_state=42, max_iter=2000)
clf.fit(X_title, y_num)

# Top 4 terms per category, then assign each to its dominant category
n_top = 4
cat_terms = {}  # cat -> [(term, weight), ...]
for i, cat in enumerate(cat_labels):
    top_idx = np.argsort(clf.coef_[i])[-n_top:][::-1]
    cat_terms[cat] = [(feature_names[idx], clf.coef_[i][idx]) for idx in top_idx]

# Assign each term to its home category (where it has highest coeff)
term_home = {}  # term -> cat_idx
term_weight = {}  # (cat, term) -> weight
fn_list = list(feature_names)
for i, cat in enumerate(cat_labels):
    for term, w in cat_terms[cat]:
        term_weight[(cat, term)] = w
        if term not in term_home:
            term_idx = fn_list.index(term)
            weights = [clf.coef_[j][term_idx] for j in range(len(cat_labels))]
            term_home[term] = int(np.argmax(weights))

# Sort terms: grouped by home category, then by descending weight
all_terms = list(dict.fromkeys([t for terms in cat_terms.values() for t, _ in terms]))
def _sort_key(t):
    h = term_home.get(t, 0)
    return (h, -max(clf.coef_[h][fn_list.index(t)], 0))
all_terms.sort(key=_sort_key)

# Build heatmap
heat = np.zeros((len(cat_labels), len(all_terms)))
for i, cat in enumerate(cat_labels):
    for j, term in enumerate(all_terms):
        heat[i, j] = term_weight.get((cat, term), 0)

# Plot
from matplotlib.colors import CenteredNorm
from matplotlib.patches import Rectangle
im = ax.imshow(heat, aspect="auto", cmap="RdBu_r", norm=CenteredNorm())

# Find group boundaries
group_bounds = []
current_cat = term_home[all_terms[0]]
group_start = 0
for j, term in enumerate(all_terms):
    if term_home[term] != current_cat:
        group_bounds.append((group_start, j, current_cat))
        group_start = j
        current_cat = term_home[term]
group_bounds.append((group_start, len(all_terms), current_cat))

# X-axis: category group labels at bottom, term labels below
ax.set_xticks([])
for start, end, cat_idx in group_bounds:
    mid = (start + end - 1) / 2
    # Category name below heatmap
    ax.text(mid, 6.6, cat_labels[cat_idx].replace(" ", "\n"),
            ha="center", va="top", fontsize=5.5, fontweight="bold",
            color=C[["blue","green","orange","purple","brown","gray"][cat_idx]])
    # Term labels between heatmap and category name
    for j in range(start, end):
        ax.text(j, 5.6, all_terms[j], ha="center", va="top",
                fontsize=4.5, rotation=25, color="gray")
    # Vertical separator between groups
    if end < len(all_terms):
        ax.axvline(end - 0.5, color="white", lw=1.5, linestyle="--", alpha=0.5)

ax.set_yticks(range(len(cat_labels)))
ax.set_yticklabels(cat_labels, fontsize=6.5)
ax.set_title("(C) Top TF-IDF Terms by Category", loc="left", fontweight="bold",
             fontsize=7.5)
plt.colorbar(im, ax=ax, fraction=0.05, pad=0.02, label="SVM coeff")

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
ax.set_title("(B) Accuracy vs F1-macro", loc="left", fontweight="bold")

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

# Labels with white background box for readability
for i, t in enumerate(top_tags):
    # Shorten long tag names by abbreviating common prefixes
    label = t.replace("Spatial ", "Sp.\n").replace("Cell-Cell Communication", "Cell-Cell\nCommunication")
    ax.annotate(label, (node_x[i], node_y[i]),
                fontsize=4.5, ha="center", va="center",
                bbox=dict(boxstyle="round,pad=0.15", facecolor="white",
                          alpha=0.8, edgecolor="none"))

ax.set_xlim(-1.5, 1.5); ax.set_ylim(-1.5, 1.5)
ax.set_aspect("equal")
ax.axis("off")
ax.set_title("(D) Tag Co-occurrence Network", loc="left", fontweight="bold")

save(fig, "fig6_st_benchmark")
print("Fig 6 done.")
