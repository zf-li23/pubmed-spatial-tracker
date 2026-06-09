"""Interactive 3D UMAP visualization for all embedding spaces.

Usage:
    python fig8_3d_interactive.py

Generates interactive HTML plots using Plotly.
One file per embedding space + a combined dashboard.
"""

import sys, numpy as np
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent.parent
CACHE = REPO / "experiments" / "_cache"
OUT = REPO / "report" / "figures"

PANELS = [
    ("PML BioBERT", "umap_3d_pml.npz", "tab20", range(16)),
    ("ST BioBERT", "umap_3d_st.npz", "tab10", range(6)),
    ("OHSUMED BioBERT", "umap_3d_ohsu.npz", "tab10", range(10)),
    ("PGB Node2Vec", "umap_3d_pgb.npz", "tab10", range(3)),
    ("ST Fine-tuned BioBERT", "umap_3d_st_finetuned.npz", "tab10", range(6)),
]

from plotly.offline import plot
import plotly.graph_objects as go

for title, fname, _, _ in PANELS:
    path = CACHE / fname
    if not path.exists():
        print(f"  {fname}: not found, skipping")
        continue
    data = np.load(path, allow_pickle=True)
    coords = data["coords_3d"]
    y = data["y"]

    fig = go.Figure(data=[
        go.Scatter3d(
            x=coords[:, 0], y=coords[:, 1], z=coords[:, 2],
            mode="markers",
            marker=dict(size=2, color=y, colorscale="Viridis",
                        opacity=0.7),
            text=[f"Class {c}" for c in y],
        )
    ])
    fig.update_layout(
        title=title,
        scene=dict(xaxis_title="UMAP 1", yaxis_title="UMAP 2", zaxis_title="UMAP 3"),
        width=900, height=700,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    out_path = OUT / fname.replace(".npz", "_interactive.html")
    plot(fig, filename=str(out_path), auto_open=False)
    print(f"  Saved {out_path.name}")

print("All interactive plots done.")
