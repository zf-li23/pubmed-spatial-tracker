"""Fig 1 — Spatial Tracker Dataset Overview.

3×3 composite figure showing annotation statistics:
  (A) Publication year trend
  (B) Category pie chart
  (C) Tag distribution (horizontal bar)
  (D) Tags per article histogram
  (E) Category × Tag heatmap
  (F) Technology platform bar
  (G) Biological topic bar
  (H) Annotation confidence donut
  (I) Boolean flags
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import Counter
from plot_utils import save, C, PALETTE

# ── Load data ──
df = pd.read_csv(Path(__file__).resolve().parent.parent.parent /
                 "data/spatial_tracker/annotated_articles.csv")

# Parse multi-valued fields
def split_col(series):
    """Split semicolon-separated values into a list and flatten."""
    items = []
    for v in series.dropna():
        for x in str(v).split("; "):
            items.append(x.strip())
    return items

all_tags = split_col(df["tags"])
all_tech = split_col(df["technology"])
all_bio  = split_col(df["biological_topic"])

tag_counts  = Counter(all_tags)
tech_counts = Counter(all_tech)
bio_counts  = Counter(all_bio)
cat_counts  = df["category"].value_counts()

# Tags per article
tags_per_art = df["tags"].dropna().apply(lambda x: len(str(x).split("; ")))


# ═══════════════════════════════════════════════════════════════
# Build figure
# ═══════════════════════════════════════════════════════════════

fig, axes = plt.subplots(3, 3, figsize=(9, 7.5))

# ── (A) Year Trend ──
ax = axes[0, 0]
years = df["pub_year"].value_counts().sort_index()
ax.fill_between(years.index, years.values, alpha=0.2, color=C["blue"])
ax.plot(years.index, years.values, color=C["blue"], lw=1.2)
ax.set_xlabel("Year"); ax.set_ylabel("Publications")
ax.set_title("(A) Publication Year Trend", loc="left", fontweight="bold")
ax.set_xlim(2016, 2026)
ax.yaxis.set_major_locator(plt.MaxNLocator(4))

# ── (B) Category Pie ──
ax = axes[0, 1]
colors = PALETTE[:len(cat_counts)]
wedges, texts = ax.pie(cat_counts.values, labels=None,
                        colors=colors, startangle=90, pctdistance=0.8)
ax.set_title("(B) Category", loc="left", fontweight="bold")
# Compact legend below
legend_labels = [f"{n} ({c/df.shape[0]*100:.0f}%)"
                 for n, c in zip(cat_counts.index, cat_counts.values)]
ax.legend(wedges, legend_labels, loc="center", bbox_to_anchor=(0.5, -0.12),
          ncol=3, fontsize=6, frameon=False)

# ── (C) Tag Distribution ──
ax = axes[0, 2]
top15 = tag_counts.most_common(15)
names, counts = zip(*reversed(top15))
ax.barh(names, counts, color=C["blue"], height=0.7)
ax.set_xlabel("Count")
ax.set_title("(C) Analysis Tag Distribution", loc="left", fontweight="bold")
ax.xaxis.set_major_locator(plt.MaxNLocator(4))

# ── (D) Tags per Article ──
ax = axes[1, 0]
tag_hist = tags_per_art.value_counts().sort_index()
ax.bar(tag_hist.index, tag_hist.values, color=C["green"], width=0.6,
       edgecolor="white", linewidth=0.3)
ax.set_xlabel("Tags per Article"); ax.set_ylabel("Count")
ax.set_title("(D) Tags per Article", loc="left", fontweight="bold")

# ── (E) Category × Tag Heatmap ──
ax = axes[1, 1]
# Build cross-tab
cat_order = ["Research", "Technology", "Review", "Protocol", "Data Resource", "Benchmark"]
tag_order = [t for t, _ in tag_counts.most_common(10)]
ct = np.zeros((len(cat_order), len(tag_order)))
for i, cat in enumerate(cat_order):
    subset = df[df["category"] == cat]
    cat_tags = split_col(subset["tags"])
    tc = Counter(cat_tags)
    total = subset.shape[0]
    for j, tag in enumerate(tag_order):
        ct[i, j] = tc.get(tag, 0) / total * 100 if total > 0 else 0

im = ax.imshow(ct, aspect="auto", cmap="YlOrRd", vmin=0)
ax.set_xticks(range(len(tag_order)))
ax.set_xticklabels(tag_order, rotation=45, ha="right", fontsize=6)
ax.set_yticks(range(len(cat_order)))
ax.set_yticklabels(cat_order, fontsize=7)
ax.set_title("(E) Category × Tag (%)", loc="left", fontweight="bold")
cbar = plt.colorbar(im, ax=ax, shrink=0.75, pad=0.02)
cbar.set_label("%", fontsize=6)

# ── (F) Technology Platform ──
ax = axes[1, 2]
top_tech = tech_counts.most_common(10)
tech_names, tech_vals = zip(*reversed(top_tech))
ax.barh(tech_names, tech_vals, color=C["orange"], height=0.7)
ax.set_xlabel("Count")
ax.set_title("(F) Technology Platform", loc="left", fontweight="bold")

# ── (G) Biological Topic ──
ax = axes[2, 0]
top_bio = bio_counts.most_common(10)
bio_names, bio_vals = zip(*reversed(top_bio))
ax.barh(bio_names, bio_vals, color=C["purple"], height=0.7)
ax.set_xlabel("Count")
ax.set_title("(G) Biological Topic", loc="left", fontweight="bold")

# ── (H) Confidence Donut ──
ax = axes[2, 1]
conf = df["confidence"].value_counts()
conf_colors = [C["green"], C["blue"], C["red"]]
conf_labels = [f"{k}\n({v/df.shape[0]*100:.0f}%)" for k, v in conf.items()]
ax.pie(conf.values, labels=conf_labels, colors=conf_colors,
       startangle=90, wedgeprops={"width": 0.4, "edgecolor": "white"})
ax.set_title("(H) Confidence", loc="left", fontweight="bold")

# ── (I) Boolean Flags ──
ax = axes[2, 2]
flags = {"has_new_data": "Has\nNew Data", "has_code": "Has\nCode",
         "is_preprint": "Is\nPreprint"}
x_labels = [flags[k] for k in flags]
true_counts = [int(df[k].sum()) for k in flags]
false_counts = [len(df) - c for c in true_counts]
x = np.arange(len(flags))
w = 0.35
ax.bar(x - w/2, true_counts, w, color=C["green"], label="True")
ax.bar(x + w/2, false_counts, w, color=C["gray"], label="False",
       alpha=0.5)
ax.set_xticks(x)
ax.set_xticklabels(x_labels, fontsize=7)
ax.set_ylabel("Count")
ax.set_title("(I) Boolean Attributes", loc="left", fontweight="bold")
ax.legend(fontsize=6, frameon=False)

# ── Final touches ──
plt.subplots_adjust(left=0.06, right=0.98, top=0.96, bottom=0.06,
                    hspace=0.55, wspace=0.45)
save(fig, "fig1_dataset_overview")
print("Fig 1 done.")



# ── Standalone panels ──
_PD = Path(__file__).resolve().parent.parent / "figures" / "panels"
_PD.mkdir(parents=True, exist_ok=True)
def _s(l, w, h, fn):
    import matplotlib.pyplot as plt
    pf = plt.figure(figsize=(w, h), facecolor="white")
    pa = pf.add_axes([0.1, 0.08, 0.87, 0.87]); fn(pa)
    pf.savefig(str(_PD / f"fig1_{l}.png"), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(pf)

_s("A", 5, 3.5, lambda ax: ax.text(0.5, 0.5, "Panel A (see composite)", ha="center", va="center", fontsize=10, color="gray"))
_s("B", 5, 3.5, lambda ax: ax.text(0.5, 0.5, "Panel B (see composite)", ha="center", va="center", fontsize=10, color="gray"))
_s("C", 5, 3.5, lambda ax: ax.text(0.5, 0.5, "Panel C (see composite)", ha="center", va="center", fontsize=10, color="gray"))
_s("D", 5, 3.5, lambda ax: ax.text(0.5, 0.5, "Panel D (see composite)", ha="center", va="center", fontsize=10, color="gray"))
_s("E", 5, 3.5, lambda ax: ax.text(0.5, 0.5, "Panel E (see composite)", ha="center", va="center", fontsize=10, color="gray"))
_s("F", 5, 3.5, lambda ax: ax.text(0.5, 0.5, "Panel F (see composite)", ha="center", va="center", fontsize=10, color="gray"))
_s("G", 5, 3.5, lambda ax: ax.text(0.5, 0.5, "Panel G (see composite)", ha="center", va="center", fontsize=10, color="gray"))
_s("H", 5, 3.5, lambda ax: ax.text(0.5, 0.5, "Panel H (see composite)", ha="center", va="center", fontsize=10, color="gray"))
_s("I", 5, 3.5, lambda ax: ax.text(0.5, 0.5, "Panel I (see composite)", ha="center", va="center", fontsize=10, color="gray"))
print("  panels A-I saved")
