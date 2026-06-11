#!/usr/bin/env python3
"""Export individual panels for PPT use.

Usage: python report/scripts/export_panels.py
Output: report/figures/panels/{fig}_{label}.png
"""
import sys, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from plot_utils import FIGURES

PANEL_DIR = FIGURES / "panels"
PANEL_DIR.mkdir(parents=True, exist_ok=True)

def copy_bars(pax, ax):
    for p in ax.patches:
        if isinstance(p, Rectangle):
            kw = dict(facecolor=p.get_facecolor(), edgecolor=p.get_edgecolor(),
                      linewidth=p.get_linewidth(), hatch=p.get_hatch())
            pax.add_patch(Rectangle(p.get_xy(), p.get_width(), p.get_height(), **kw))

def copy_lines(pax, ax):
    for l in ax.lines:
        pax.plot(l.get_xdata(), l.get_ydata(), color=l.get_color(),
                lw=l.get_linewidth(), ls=l.get_linestyle(), alpha=l.get_alpha())

def copy_texts(pax, ax):
    for t in ax.texts:
        p = t.get_position()
        pax.text(p[0], p[1], t.get_text(), ha=t.get_ha(), va=t.get_va(),
                fontsize=t.get_fontsize(), color=t.get_color(),
                fontweight=t.get_fontweight(), transform=pax.transData)

def copy_scatter(pax, ax):
    for c in ax.collections:
        try:
            off = c.get_offsets()
            if len(off) > 0:
                pax.scatter(off[:,0], off[:,1], c=c.get_facecolors(),
                          s=c.get_sizes() or 12, alpha=c.get_alpha(),
                          edgecolors="none", marker="o")
        except: pass

def copy_imshow(pax, ax):
    for img in ax.images:
        arr = img.get_array()
        pax.imshow(arr, aspect="auto", cmap=img.get_cmap(),
                  norm=img.norm, extent=img.get_extent(), interpolation="nearest")

def setup_axes(pax, ax):
    pax.set_xlim(ax.get_xlim()); pax.set_ylim(ax.get_ylim())
    if ax.get_xscale() == "log": pax.set_xscale("log")
    if ax.get_yscale() == "log": pax.set_yscale("log")
    try:
        pax.set_xticks(ax.get_xticks()); pax.set_yticks(ax.get_yticks())
    except: pass
    pax.set_xticklabels([t.get_text() for t in ax.get_xticklabels()], fontsize=9)
    pax.set_yticklabels([t.get_text() for t in ax.get_yticklabels()], fontsize=9)
    pax.set_xlabel(ax.get_xlabel(), fontsize=10)
    pax.set_ylabel(ax.get_ylabel(), fontsize=10)
    pax.set_title(ax.get_title(), fontsize=12, fontweight="bold")

def export_fig(script, fig_label, panel_labels):
    print(f"  {fig_label}...", end=" ", flush=True)
    ns = {"__file__": str(script)}
    exec(open(script).read(), ns)
    fig = plt.gcf()
    # Get axes that have content (not colorbars)
    axes = [a for a in fig.axes if len(a.patches) > 0 or len(a.lines) > 0 or
            len(a.collections) > 0 or len(a.images) > 0]
    # Remove twinx axes (they'll be merged with parent)
    seen_positions = set()
    filtered = []
    for a in axes:
        pos = tuple(np.round(a.get_position().get_points().flatten(), 4))
        if pos not in seen_positions:
            seen_positions.add(pos)
            filtered.append(a)
    axes = filtered[:len(panel_labels)]
    for ax, label in zip(axes[:len(panel_labels)], panel_labels):
        ext = ax.get_position()
        fw, fh = fig.get_size_inches()
        pw, ph = ext.width * fw * 1.2, ext.height * fh * 1.2
        pfig = plt.figure(figsize=(pw, ph), facecolor="white")
        pax = pfig.add_axes([0.1, 0.08, 0.87, 0.87])
        setup_axes(pax, ax)
        copy_bars(pax, ax)
        copy_lines(pax, ax)
        copy_scatter(pax, ax)
        copy_imshow(pax, ax)
        copy_texts(pax, ax)
        # Copy legends
        leg = ax.get_legend()
        if leg:
            pax.legend(fontsize=8, frameon=False)
        pfig.savefig(PANEL_DIR / f"{fig_label}_{label}.png", dpi=200,
                    bbox_inches="tight", facecolor="white")
        plt.close(pfig)
    plt.close(fig)
    print(f"{len(axes)} panels")

# ── Export all ──
SCRIPTS = [
    ("fig2", "fig2_classical_matrix.py", "ABCDEFGHI"),
    ("fig3", "fig3_dl_unsupervised.py", "ABCD"),
    ("fig4", "fig4_multilabel.py", "ABCD"),
    ("fig5", "fig5_graph.py", "ABCD"),
    ("fig6", "fig6_st_benchmark.py", "ABCD"),
    ("fig7", "fig7_transfer_learning.py", "AB"),
]

base = Path(__file__).resolve().parent
for fig_label, script_name, labels in SCRIPTS:
    export_fig(base / script_name, fig_label, labels)

print(f"\nDone. {len(list(PANEL_DIR.glob('*.png')))} panels in {PANEL_DIR}/")
