"""Shared plotting utilities for report figures.

All figure scripts import from this module for consistent styling.
"""

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import scienceplots
import numpy as np
import pandas as pd
from pathlib import Path
from collections import Counter
from scipy import stats

# ── Paths ──
REPO = Path(__file__).resolve().parent.parent.parent
FIGURES = REPO / "report" / "figures"
FIGURES.mkdir(parents=True, exist_ok=True)

# ── Global style ──
plt.style.use(["science", "no-latex"])
plt.rcParams.update({
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "font.size": 8,
    "axes.titlesize": 9,
    "axes.labelsize": 8,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "lines.linewidth": 0.8,
})

# ── Color palette (colorblind-friendly) ──
C = {
    "blue":   "#0173B2",
    "orange": "#DE8F05",
    "green":  "#029E73",
    "red":    "#D55E00",
    "purple": "#CC78BC",
    "brown":  "#CA9161",
    "pink":   "#FBAFE4",
    "gray":   "#949494",
    "yellow": "#ECE133",
    "teal":   "#56B4E9",
}
PALETTE = list(C.values())


def save(fig, name):
    """Save figure to both PDF and PNG."""
    fig.savefig(FIGURES / f"{name}.pdf")
    fig.savefig(FIGURES / f"{name}.png")
    print(f"  → saved {name}.pdf / .png")


def sig_annotate(ax, x1, x2, y, p_val, bar_offset=0.02):
    """Draw significance bracket and stars between two bars.

    Parameters
    ----------
    ax : Axes
    x1, x2 : int  — bar indices
    y : float    — height of bracket (top of the taller bar + offset)
    p_val : float or None
        None means incompatible fold counts — draws bracket with '—'.
    bar_offset : fraction of y-axis range added for the bracket line
    """
    if p_val is None:
        label = "—"
    elif np.isnan(p_val):
        return
    elif p_val < 0.001:
        label = "***"
    elif p_val < 0.01:
        label = "**"
    elif p_val < 0.05:
        label = "*"
    else:
        label = "ns"

    ylim = ax.get_ylim()
    bracket_top = y + (ylim[1] - ylim[0]) * bar_offset
    bracket_mid = bracket_top - (ylim[1] - ylim[0]) * 0.005

    ax.plot([x1, x1, x2, x2], [y, bracket_mid, bracket_mid, y],
            lw=0.6, color="black", clip_on=False)
    ax.text((x1 + x2) / 2, bracket_top, label, ha="center", va="bottom",
            fontsize=7, fontweight="bold")


def paired_ttest_from_folds(folds_str_a, folds_str_b):
    """Compute paired t-test p-value from comma-separated fold values.

    Returns None if fold arrays have different lengths (e.g. 3-fold vs 5-fold).
    """
    try:
        a = np.array([float(x) for x in str(folds_str_a).split(",")])
        b = np.array([float(x) for x in str(folds_str_b).split(",")])
        if len(a) != len(b):
            return None
        t_stat, p = stats.ttest_rel(a, b)
        return p
    except (ValueError, TypeError):
        return None


# ── Data loaders ──

def load_classical_matrix(path=None):
    """Load classical algorithm matrix results (Exp 001).

    Works with both old format (no _folds columns) and new format.
    """
    if path is None:
        path = REPO / "experiments/001_classical_matrix/results/classical_matrix.csv"
    return pd.read_csv(path)


def load_annotation_data():
    """Load annotated articles."""
    return pd.read_csv(REPO / "data/spatial_tracker/annotated_articles.csv")
