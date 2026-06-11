#!/usr/bin/env python3
"""Compute all paired t-tests across figures and save to CSV for verification."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
from scipy import stats
from plot_utils import paired_ttest_from_folds

REPO = Path(__file__).resolve().parent.parent.parent
OUT = REPO / "report" / "significance_report.csv"
rows = []

# ═══════════════════════════════════════════════════════════════
# 1) Fig 2B — Classical Matrix (Exp 001)
# ═══════════════════════════════════════════════════════════════
clf = pd.read_csv(REPO / "experiments/001_classical_matrix/results/classical_matrix_with_folds.csv")

for ds_name, ds_label in [("pubmed_multilabel", "PML"), ("ohsumed", "OHSUMED"), ("pgb", "PGB")]:
    sub = clf[clf["dataset"] == ds_name].dropna(subset=["f1_macro"]).nlargest(5, "f1_macro")
    if len(sub) < 2:
        continue
    for i in range(1, len(sub)):
        fold_a = sub.iloc[0].get("f1_macro_folds", None)
        fold_b = sub.iloc[i].get("f1_macro_folds", None)
        label_a = f"{sub.iloc[0]['feature']}/{sub.iloc[0]['model']}"
        label_b = f"{sub.iloc[i]['feature']}/{sub.iloc[i]['model']}"
        has_folds = pd.notna(fold_a) and pd.notna(fold_b) and str(fold_a).strip() and str(fold_b).strip()
        if has_folds:
            try:
                a = np.array([float(x) for x in str(fold_a).split(",")])
                b = np.array([float(x) for x in str(fold_b).split(",")])
                t_stat, p_val = stats.ttest_rel(a, b)
            except:
                t_stat, p_val = None, None
        else:
            t_stat, p_val = None, None
        rows.append({
            "figure": "Fig2B",
            "dataset": ds_label,
            "panel": "A" if ds_name == "pubmed_multilabel" else "B",
            "bar_A": label_a,
            "bar_B": label_b,
            "f1_A": round(sub.iloc[0]["f1_macro"], 4),
            "f1_B": round(sub.iloc[i]["f1_macro"], 4),
            "fold_vals_A": str(fold_a) if has_folds else "N/A",
            "fold_vals_B": str(fold_b) if has_folds else "N/A",
            "t_statistic": round(t_stat, 4) if t_stat is not None else "N/A",
            "p_value": f"{p_val:.6e}" if p_val is not None else "N/A",
            "significance": "***" if (p_val is not None and p_val < 0.001) else (
                           "**" if (p_val is not None and p_val < 0.01) else (
                           "*" if (p_val is not None and p_val < 0.05) else (
                           "ns" if (p_val is not None) else "—"))),
            "n_folds": len(str(fold_a).split(",")) if has_folds else 0,
        })

# ═══════════════════════════════════════════════════════════════
# 2) Fig 4 — Multi-label Strategy (Exp 004)
# ═══════════════════════════════════════════════════════════════
ml = pd.read_csv(REPO / "experiments/004_multilabel_strategy/results/multilabel_strategy.csv")

for ds_name in ["pubmed_multilabel", "ohsumed"]:
    sub = ml[ml["dataset"] == ds_name]
    strategies = sub["strategy"].values.astype(str)
    ds_label = "PML" if ds_name == "pubmed_multilabel" else "OHSUMED"
    for i in range(len(strategies)):
        for j in range(i + 1, len(strategies)):
            fi = sub.iloc[i].get("f1_macro_folds", None)
            fj = sub.iloc[j].get("f1_macro_folds", None)
            has_folds = pd.notna(fi) and pd.notna(fj) and str(fi).strip() and str(fj).strip()
            if has_folds:
                try:
                    a = np.array([float(x) for x in str(fi).split(",")])
                    b = np.array([float(x) for x in str(fj).split(",")])
                    t_stat, p_val = stats.ttest_rel(a, b)
                except:
                    t_stat, p_val = None, None
            else:
                t_stat, p_val = None, None
            rows.append({
                "figure": "Fig4",
                "dataset": ds_label,
                "panel": "A",
                "bar_A": strategies[i],
                "bar_B": strategies[j],
                "f1_A": round(sub.iloc[i]["f1_macro"], 4),
                "f1_B": round(sub.iloc[j]["f1_macro"], 4),
                "fold_vals_A": str(fi) if has_folds else "N/A",
                "fold_vals_B": str(fj) if has_folds else "N/A",
                "t_statistic": round(t_stat, 4) if t_stat is not None else "N/A",
                "p_value": f"{p_val:.6e}" if p_val is not None else "N/A",
                "significance": "***" if (p_val is not None and p_val < 0.001) else (
                               "**" if (p_val is not None and p_val < 0.01) else (
                               "*" if (p_val is not None and p_val < 0.05) else (
                               "ns" if (p_val is not None) else "—"))),
                "n_folds": len(str(fi).split(",")) if has_folds else 0,
            })

# ═══════════════════════════════════════════════════════════════
# 3) Fig 6 — ST Benchmark (Exp 006)
# ═══════════════════════════════════════════════════════════════
st = pd.read_csv(REPO / "experiments/006_st_benchmark/results/st_benchmark.csv")
methods = st["method"].values
for i in range(len(methods)):
    for j in range(i + 1, len(methods)):
        fi = st.iloc[i].get("f1_macro_folds", None)
        fj = st.iloc[j].get("f1_macro_folds", None)
        has_folds = pd.notna(fi) and pd.notna(fj) and str(fi).strip() and str(fj).strip()
        if has_folds:
            try:
                a = np.array([float(x) for x in str(fi).split(",")])
                b = np.array([float(x) for x in str(fj).split(",")])
                t_stat, p_val = stats.ttest_rel(a, b)
            except:
                t_stat, p_val = None, None
        else:
            t_stat, p_val = None, None
        rows.append({
            "figure": "Fig6",
            "dataset": "ST",
            "panel": "A",
            "bar_A": methods[i],
            "bar_B": methods[j],
            "f1_A": round(st.iloc[i]["f1_macro"], 4),
            "f1_B": round(st.iloc[j]["f1_macro"], 4),
            "fold_vals_A": str(fi) if has_folds else "N/A",
            "fold_vals_B": str(fj) if has_folds else "N/A",
            "t_statistic": round(t_stat, 4) if t_stat is not None else "N/A",
            "p_value": f"{p_val:.6e}" if p_val is not None else "N/A",
            "significance": "***" if (p_val is not None and p_val < 0.001) else (
                           "**" if (p_val is not None and p_val < 0.01) else (
                           "*" if (p_val is not None and p_val < 0.05) else (
                           "ns" if (p_val is not None) else "—"))),
            "n_folds": len(str(fi).split(",")) if has_folds else 0,
        })

# ═══════════════════════════════════════════════════════════════
# 4) Fig 5 — Graph Methods (Exp 005, now with per-fold data)
# ═══════════════════════════════════════════════════════════════
gm = pd.read_csv(REPO / "experiments/005_graph_models/results/graph_models.csv")
# Panel A: Node2Vec classifiers — best vs rest
n2v = gm[gm["feature"] == "node2vec"]
if len(n2v) > 1:
    best_row = n2v.loc[n2v["f1_macro"].idxmax()]
    for _, r in n2v.iterrows():
        if r["model"] == best_row["model"]:
            continue
        fi = best_row.get("f1_macro_folds", None)
        fj = r.get("f1_macro_folds", None)
        has_folds = pd.notna(fi) and pd.notna(fj) and str(fi).strip() and str(fj).strip()
        if has_folds:
            try:
                a = np.array([float(x) for x in str(fi).split(",")])
                b = np.array([float(x) for x in str(fj).split(",")])
                t_stat, p_val = stats.ttest_rel(a, b)
            except:
                t_stat, p_val = None, None
        else:
            t_stat, p_val = None, None
        rows.append({
            "figure": "Fig5",
            "dataset": "PGB",
            "panel": "A",
            "bar_A": best_row["model"],
            "bar_B": r["model"],
            "f1_A": round(best_row["f1_macro"], 4),
            "f1_B": round(r["f1_macro"], 4),
            "fold_vals_A": str(fi) if has_folds else "N/A",
            "fold_vals_B": str(fj) if has_folds else "N/A",
            "t_statistic": round(t_stat, 4) if t_stat is not None else "N/A",
            "p_value": f"{p_val:.6e}" if p_val is not None else "N/A",
            "significance": "***" if (p_val is not None and p_val < 0.001) else (
                           "**" if (p_val is not None and p_val < 0.01) else (
                           "*" if (p_val is not None and p_val < 0.05) else (
                           "ns" if (p_val is not None) else "—"))),
            "n_folds": len(str(fi).split(",")) if has_folds else 0,
        })

# Panel B: GCN vs GraphSAGE vs Node2Vec
graph_methods = gm[gm["feature"].isin(["tfidf+graph", "node2vec"])]
methods_list = graph_methods["model"].unique()
for i in range(len(methods_list)):
    for j in range(i + 1, len(methods_list)):
        ri = graph_methods[graph_methods["model"] == methods_list[i]].iloc[0]
        rj = graph_methods[graph_methods["model"] == methods_list[j]].iloc[0]
        fi = ri.get("f1_macro_folds", None)
        fj = rj.get("f1_macro_folds", None)
        has_folds = pd.notna(fi) and pd.notna(fj) and str(fi).strip() and str(fj).strip()
        if has_folds:
            try:
                a = np.array([float(x) for x in str(fi).split(",")])
                b = np.array([float(x) for x in str(fj).split(",")])
                t_stat, p_val = stats.ttest_rel(a, b)
            except:
                t_stat, p_val = None, None
        else:
            t_stat, p_val = None, None
        rows.append({
            "figure": "Fig5",
            "dataset": "PGB",
            "panel": "B",
            "bar_A": methods_list[i],
            "bar_B": methods_list[j],
            "f1_A": round(ri["f1_macro"], 4),
            "f1_B": round(rj["f1_macro"], 4),
            "fold_vals_A": str(fi) if has_folds else "N/A",
            "fold_vals_B": str(fj) if has_folds else "N/A",
            "t_statistic": round(t_stat, 4) if t_stat is not None else "N/A",
            "p_value": f"{p_val:.6e}" if p_val is not None else "N/A",
            "significance": "***" if (p_val is not None and p_val < 0.001) else (
                           "**" if (p_val is not None and p_val < 0.01) else (
                           "*" if (p_val is not None and p_val < 0.05) else (
                           "ns" if (p_val is not None) else "—"))),
            "n_folds": len(str(fi).split(",")) if has_folds else 0,
        })

# ═══════════════════════════════════════════════════════════════
# 5) Fig 7 — Transfer Learning (Exp 007, no CV → no per-fold data)
# ═══════════════════════════════════════════════════════════════
try:
    tl = pd.read_csv(REPO / "experiments/007_transfer_learning/results/transfer_learning.csv")
    if "f1_macro" in tl.columns and len(tl) > 1:
        for i in range(len(tl)):
            for j in range(i + 1, len(tl)):
                rows.append({
                    "figure": "Fig7",
                    "dataset": tl.iloc[i].get("method", f"run_{i}"),
                    "panel": "B",
                    "bar_A": tl.iloc[i].get("method", f"run_{i}"),
                    "bar_B": tl.iloc[j].get("method", f"run_{j}"),
                    "f1_A": round(tl.iloc[i]["f1_macro"], 4),
                    "f1_B": round(tl.iloc[j]["f1_macro"], 4),
                    "fold_vals_A": "N/A (no CV)",
                    "fold_vals_B": "N/A (no CV)",
                    "t_statistic": "N/A",
                    "p_value": "N/A",
                    "significance": "—",
                    "n_folds": 0,
                })
except Exception as e:
    print(f"  [SKIP Fig7] {e}")

# ── Save ──
result_df = pd.DataFrame(rows)
result_df.to_csv(OUT, index=False)
print(f"Significance report saved → {OUT}")
print(f"Total comparisons: {len(result_df)}")
print()
print(result_df.to_string(index=False))
