"""Shared plotting configuration for all report figures.

Usage:
    from report.scripts.plot_config import *

Conventions:
  - All labels in English
  - Colorblind-friendly palettes (viridis / tab10)
  - science theme for publication-quality output
  - Both PDF (for LaTeX) and PNG (for preview) saved
"""

import sys, os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import seaborn as sns

# ── Paths ──
REPO = Path(__file__).resolve().parent.parent.parent
FIGDIR = REPO / "report" / "figures"
PPT_DIR = FIGDIR / "ppt"
FIGDIR.mkdir(parents=True, exist_ok=True)
PPT_DIR.mkdir(parents=True, exist_ok=True)

# ── Style ──
try:
    plt.style.use(["science", "no-latex", "bright"])
except Exception:
    plt.style.use("seaborn-v0_8-whitegrid")

sns.set_context("paper", font_scale=1.0)
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "font.size": 8,
    "axes.labelsize": 9,
    "axes.titlesize": 9,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
})

# ── Color palettes ──
CATEGORY_COLORS = {
    "Research":        "#1f77b4",  # blue
    "Technology":      "#ff7f0e",  # orange
    "Review":          "#2ca02c",  # green
    "Protocol":        "#d62728",  # red
    "Data Resource":   "#9467bd",  # purple
    "Benchmark":       "#8c564b",  # brown
}

DATASET_COLORS = {
    "ohsumed":           "#1f77b4",
    "pubmed_multilabel": "#ff7f0e",
    "pgb":               "#2ca02c",
    "spatial_tracker":   "#d62728",
}

FEATURE_COLORS = {
    "tfidf":   "#e41a1c",
    "biobert": "#377eb8",
    "lda":     "#4daf4a",
    "meta":    "#984ea3",
    "node2vec":"#ff7f00",
}

MODEL_COLORS = {
    "NaiveBayes":  "#a6cee3",
    "k-NN":        "#1f78b4",
    "SVM":         "#b2df8a",
    "LogisticReg": "#33a02c",
    "RandomForest":"#fb9a99",
    "AdaBoost":    "#e31a1c",
    "XGBoost":     "#fdbf6f",
}

# ── Helpers ──

def save_both(name, fig=None, dpi=300):
    """Save figure as both PDF and PNG."""
    if fig is None:
        fig = plt.gcf()
    fig.savefig(FIGDIR / f"{name}.pdf", dpi=dpi)
    fig.savefig(FIGDIR / f"{name}.png", dpi=dpi)
    plt.close(fig)


def save_panel(name, fig=None, dpi=300):
    """Save individual panel for PPT use."""
    if fig is None:
        fig = plt.gcf()
    fig.savefig(PPT_DIR / f"{name}.png", dpi=dpi)
    plt.close(fig)


def label_panel(ax, label, loc="upper left", x=-0.04, y=1.03):
    """Add bold panel label (A), (B), etc."""
    ax.text(x, y, f"({label})", transform=ax.transAxes,
            fontsize=9, fontweight="bold", va="bottom", ha="left")


def paired_ttest_stars(vals1, vals2, alpha=0.05):
    """Return significance stars from two per-fold value lists.

    Uses paired t-test (same CV folds → random_state=42).
    """
    from scipy.stats import ttest_rel
    _, p = ttest_rel(vals1, vals2)
    if p < 0.001:
        return "***"
    elif p < 0.01:
        return "**"
    elif p < 0.05:
        return "*"
    return "ns"


def parse_folds(fold_str):
    """Parse comma-separated per-fold values from CSV."""
    if not fold_str or not isinstance(fold_str, str):
        return None
    return [float(x) for x in fold_str.split(",")]


def add_significance_bracket(ax, x1, x2, y, stars, h=0.015):
    """Draw significance bracket with stars between two bars."""
    ax.plot([x1, x1, x2, x2], [y, y + h, y + h, y], lw=0.8, color="black",
            clip_on=False)
    ax.text((x1 + x2) / 2, y + h, stars, ha="center", va="bottom",
            fontsize=8, fontweight="bold")
