"""Fig 3 — Unsupervised, Multi-label & Graph Methods (merged fig3+fig4+fig5).

6×2 composite stacked vertically:
  R0-1: DL & Unsupervised  (A BioBERT vs Best, B LDA NMI, C Unsup vs Sup, D Cost-Benefit)
  R2-3: Multi-label         (E BR/CC/LP, F F1 vs Time, G OHSUMED zoom, H Robustness)
  R4-5: Graph Methods       (I Node2Vec, J Graph Methods, K ST Graph, L Label Complexity)
"""
import sys, numpy as np, pandas as pd, matplotlib.pyplot as plt
from pathlib import Path
from collections import Counter
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from scipy import stats as sp_stats
p = Path(__file__).resolve().parent
sys.path.insert(0, str(p))
from plot_utils import save, C, PALETTE, sig_annotate, paired_ttest_from_folds

REPO = p.parent.parent
bmlp = pd.read_csv(REPO / "experiments" / "002_biobert_mlp" / "results" / "biobert_mlp.csv")
lda = pd.read_csv(REPO / "experiments" / "003_lda_cluster" / "results" / "lda_cluster.csv")
clf = pd.read_csv(REPO / "experiments" / "001_classical_matrix" / "results" / "classical_matrix.csv")
ml = pd.read_csv(REPO / "experiments" / "004_multilabel_strategy" / "results" / "multilabel_strategy.csv")
gm = pd.read_csv(REPO / "experiments" / "005_graph_models" / "results" / "graph_models.csv")
tl = pd.read_csv(REPO / "experiments" / "007_transfer_learning" / "results" / "transfer_learning.csv")

lda = lda.drop_duplicates(subset=["dataset"])
bc = {}
for ds in ["ohsumed","pubmed_multilabel","pgb"]:
    s = clf[clf["dataset"]==ds].dropna(subset=["f1_macro"])
    if not s.empty: bc[ds] = s["f1_macro"].max()
datasets = ["ohsumed","pubmed_multilabel","pgb"]
ds_lbl = ["OHSUMED","PML","PGB"]
ds_col = [C["blue"],C["green"],C["orange"]]

fig, axes = plt.subplots(6, 2, figsize=(10, 16))
plt.subplots_adjust(left=0.08, right=0.96, top=0.97, bottom=0.03, hspace=0.5, wspace=0.35)

# ═══════════════════════════
#  Fig 3: DL & Unsupervised
# ═══════════════════════════
# (A) BioBERT+MLP vs Best Classical
ax = axes[0, 0]
x = np.arange(3); w = 0.3
bmlp_v = [bmlp[bmlp["dataset"]==ds]["f1_macro"].values[0] if not bmlp[bmlp["dataset"]==ds].empty else 0 for ds in datasets]
cl_v = [bc.get(ds, 0) for ds in datasets]
for i in range(3):
    ax.bar(x[i]-w/2, cl_v[i], w, color=ds_col[i], edgecolor="white", linewidth=0.5, alpha=0.9)
    ax.bar(x[i]+w/2, bmlp_v[i], w, color=ds_col[i], edgecolor="white", linewidth=0.5, alpha=0.9, hatch="////")
ax.legend(handles=[Patch(facecolor="gray",edgecolor="white",label="Best Classical"),
                   Patch(facecolor="gray",edgecolor="white",hatch="////",label="BioBERT+MLP")], fontsize=5.5, frameon=False, ncol=2)
if bmlp_v[0] < 0.01: ax.text(0+w/2, bmlp_v[0]+0.002, f"{bmlp_v[0]:.4f}", ha="center", fontsize=6, color=C["blue"])
ax.set_xticks(x); ax.set_xticklabels(ds_lbl, fontsize=7)
ax.set_ylabel("F1-macro", fontsize=7)
ax.set_title("(A) BioBERT+MLP vs Best Classical", loc="left", fontweight="bold", fontsize=8)

# (B) LDA NMI
ax = axes[0, 1]
lda_v = [float(lda[lda["dataset"]==ds]["nmi"].values[0]) if not lda[lda["dataset"]==ds].empty else 0 for ds in datasets]
ax.bar(ds_lbl, lda_v, color=ds_col, width=0.5, edgecolor="white")
for i, v in enumerate(lda_v): ax.text(i, v+0.01, f"{v:.3f}", ha="center", fontsize=6.5)
ax.set_ylabel("NMI", fontsize=7)
ax.set_title("(B) LDA Clustering (NMI)", loc="left", fontweight="bold", fontsize=8)

# (C) Unsupervised vs Supervised
ax = axes[1, 0]; ax2 = ax.twinx()
ax.bar(np.arange(3)-0.15, lda_v, 0.3, color=C["purple"], label="NMI (unsupervised)", edgecolor="white")
ax.set_ylabel("NMI", fontsize=7); ax.set_ylim(0, max(lda_v)*1.6)
ax2.bar(np.arange(3)+0.15, [bc.get(ds,0) for ds in datasets], 0.3, color=C["green"], alpha=0.6, label="F1 (supervised)", edgecolor="white")
ax2.set_ylabel("F1-macro", fontsize=7, color=C["green"]); ax2.set_ylim(0, max([bc.get(ds,0) for ds in datasets])*1.6)
ax.set_xticks(range(3)); ax.set_xticklabels(ds_lbl, fontsize=7)
ax.set_title("(C) Unsupervised vs Supervised", loc="left", fontweight="bold", fontsize=8)
l1, lb1 = ax.get_legend_handles_labels(); l2, lb2 = ax2.get_legend_handles_labels()
ax.legend(l1+l2, lb1+lb2, fontsize=6, frameon=False, loc="upper left")

# (D) Cost-Benefit
ax = axes[1, 1]
pts = []
for ds, mk, dc in [("ohsumed","o",C["blue"]),("pubmed_multilabel","s",C["green"]),("pgb","^",C["orange"])]:
    sub = clf[clf["dataset"]==ds].dropna(subset=["f1_macro","train_time_s"])
    for _, r in sub.iterrows(): pts.append((r["train_time_s"], r["f1_macro"], ds, mk, dc))
st6 = pd.read_csv(REPO/"experiments"/"006_st_benchmark"/"results"/"st_benchmark.csv")
for _, r in st6.iterrows(): pts.append((r["train_time_s"], r["f1_macro"], "ST", "D", C["red"]))
for _, r in bmlp.iterrows():
    if "train_time_s" in r and "f1_macro" in r: pts.append((r["train_time_s"], r["f1_macro"], r["dataset"], "v", C["purple"]))
ts_v = np.array([p[0] for p in pts]); f1s = np.array([p[1] for p in pts])
ax.scatter(ts_v, f1s, c=[p[4] for p in pts], s=20, alpha=0.6, edgecolors="none")
bi = np.argmax(f1s)
ax.annotate(f"Best F1={f1s[bi]:.3f}", (ts_v[bi], f1s[bi]), fontsize=6, ha="center", va="bottom", xytext=(0,8), textcoords="offset points")
ax.set_xscale("log"); ax.set_xlabel("Time (s, log)", fontsize=7); ax.set_ylabel("F1-macro", fontsize=7)
ax.set_title("(D) Cost-Benefit", loc="left", fontweight="bold", fontsize=8)

# ═══════════════════════════
#  Fig 4: Multi-label Strategy
# ═══════════════════════════
# (E) BR vs CC vs LP
ax = axes[2, 0]
pml_ml = ml[ml["dataset"]=="pubmed_multilabel"]
stg = pml_ml["strategy"].values.astype(str); sv = pml_ml["f1_macro"].values; se = pml_ml["f1_macro_std"].values
ax.bar(stg, sv, yerr=se, color=[C["blue"],C["green"],C["orange"]], width=0.5, capsize=3, edgecolor="white")
sf = [str(pml_ml.iloc[k].get("f1_macro_folds",None)) for k in range(len(stg))]
for i in range(len(stg)):
    for j in range(i+1, len(stg)):
        fi, fj = sf[i], sf[j]
        if pd.notna(fi) and pd.notna(fj) and fi.strip() and fj.strip():
            from scipy import stats as S
            try:
                pv = S.ttest_rel([float(x) for x in fi.split(",")], [float(x) for x in fj.split(",")])[1]
            except: pv = None
        else: pv = None
        ym = max(sv[i]+se[i], sv[j]+se[j])*1.03
        sig_annotate(ax, i, j, ym, pv)
ax.set_ylabel("F1-macro", fontsize=7)
ax.set_title("(E) Multi-label Strategy (PML)", loc="left", fontweight="bold", fontsize=8)

# (F) F1 vs Time
ax = axes[2, 1]; ax2 = ax.twinx()
ax.bar(stg, sv, color=[C["blue"],C["green"],C["orange"]], width=0.4, alpha=0.7, edgecolor="white")
ax2.plot(stg, pml_ml["train_time_s"].values, "ko-", lw=1, markersize=5, label="Time")
ax.set_ylabel("F1-macro", fontsize=7); ax2.set_ylabel("Time (s)", fontsize=7, color="gray")
ax.set_title("(F) F1 vs Time", loc="left", fontweight="bold", fontsize=8)
ax2.legend(fontsize=5.5, frameon=False)

# (G) OHSUMED zoom
ax = axes[3, 0]
ohs_ml = ml[ml["dataset"]=="ohsumed"]; os_v = ohs_ml["f1_macro"].values
ax.bar(ohs_ml["strategy"].values.astype(str), os_v, color=[C["blue"],C["green"],C["orange"]], width=0.5, edgecolor="white")
ax.set_ylim(0, max(os_v)*1.3)
for i, v in enumerate(os_v): ax.text(i, v+0.0002, f"{v:.4f}", ha="center", fontsize=6.5)
ax.set_ylabel("F1-macro", fontsize=7)
ax.set_title("(G) OHSUMED (1,650 labels)", loc="left", fontweight="bold", fontsize=8)

# (H) Model Robustness
ax = axes[3, 1]
MOD = ["NaiveBayes","k-NN","SVM","LogisticReg","RandomForest","AdaBoost","XGBoost"]
MODL = dict(zip(MOD,["NB","kNN","SVM","LR","RF","Ada","XGB"]))
bd = [clf[(clf["model"]==m)&(clf["dataset"]=="pubmed_multilabel")]["f1_macro"].dropna().values for m in MOD]
bp = ax.boxplot(bd, labels=[MODL[m] for m in MOD], patch_artist=True, widths=0.6, showfliers=True,
               flierprops={"markersize":3,"markerfacecolor":"gray"})
for patch, c in zip(bp["boxes"], [C["blue"]]*3+[C["green"]]*2+[C["orange"]]*2):
    patch.set_facecolor(c); patch.set_alpha(0.6)
ax.set_ylabel("F1-macro (PML)", fontsize=7)
ax.set_title("(H) Model Robustness", loc="left", fontweight="bold", fontsize=8)

# ═══════════════════════════
#  Fig 5: Graph Methods
# ═══════════════════════════
def _cpg(fa, fb):
    from scipy import stats as S
    if pd.isna(fa) or pd.isna(fb) or not str(fa).strip(): return None
    try:
        a = np.array([float(x) for x in str(fa).split(",")])
        b = np.array([float(x) for x in str(fb).split(",")])
        return S.ttest_rel(a,b)[1] if len(a)==len(b) else S.ttest_ind(a,b)[1]
    except: return None

# (I) Node2Vec
ax = axes[4, 0]
n2v = gm[gm["feature"]=="node2vec"].reset_index(drop=True)
nm = [r["model"].replace("Node2Vec+","") for _, r in n2v.iterrows()]
nv = n2v["f1_macro"].values; ne = n2v["f1_macro_std"].values
ax.bar(range(len(nm)), nv, color=C["blue"], width=0.5, edgecolor="white")
ax.set_xticks(range(len(nm))); ax.set_xticklabels(nm, fontsize=6.5)
ax.set_ylabel("F1-macro", fontsize=7)
ax.set_title("(I) Node2Vec + Classifiers", loc="left", fontweight="bold", fontsize=8)
if len(n2v) > 1:
    bi = nv.argmax(); by = max(nv[k]+ne[k] for k in range(len(nv)))
    for i in range(len(n2v)):
        if i == bi: continue
        pv = _cpg(n2v.iloc[bi].get("f1_macro_folds"), n2v.iloc[i].get("f1_macro_folds"))
        sig_annotate(ax, bi, i, by+0.015*(abs(i-bi)-1), pv)
    ax.set_ylim(0, by+0.015*(len(n2v)-2)+by*0.15)

# (J) Graph Methods
ax = axes[4, 1]
gcn = gm[gm["model"]=="GCN"].iloc[0]; sage = gm[gm["model"]=="GraphSAGE"].iloc[0]
n2v_best = n2v.loc[n2v["f1_macro"].idxmax()]
mg = ["GCN","GraphSAGE","Node2Vec\n(best)"]
gv = [gcn["f1_macro"], sage["f1_macro"], n2v_best["f1_macro"]]
ge = [gcn["f1_macro_std"], sage["f1_macro_std"], n2v_best["f1_macro_std"]]
ax.bar(range(3), gv, color=[C["green"],C["orange"],C["blue"]], width=0.5, edgecolor="white")
ax.set_xticks(range(3)); ax.set_xticklabels(mg, fontsize=6.5)
for i in range(3): ax.text(i, gv[i]+0.005, f"{gv[i]:.4f}", ha="center", fontsize=6.5, fontweight="bold")
ax.set_ylabel("F1-macro", fontsize=7)
ax.set_title("(J) Graph Methods (PGB)", loc="left", fontweight="bold", fontsize=8)
rows = [gcn, sage, n2v_best]
by = max(gv[i]+ge[i] for i in range(3))
for i in range(3):
    for j in range(i+1, 3):
        pv = _cpg(rows[i].get("f1_macro_folds"), rows[j].get("f1_macro_folds"))
        sig_annotate(ax, i, j, by+0.02*(abs(j-i)-1), pv)
ax.set_ylim(0, by+0.02*(3-2)+by*0.18)

# (K) ST Graph
ax = axes[5, 0]
d1 = tl[tl["exp_id"]=="D1"]; d2 = tl[tl["exp_id"]=="D2"]; b1 = tl[tl["exp_id"]=="B1"]
st_gcn = d1["f1_macro"].values[0] if not d1.empty else 0
st_sage = d2["f1_macro"].values[0] if not d2.empty else 0
st_bl = b1["f1_macro"].values[0] if not b1.empty else 0
ax.bar(["BioBERT+LR\n(baseline)","GCN\n(k-NN)","GraphSAGE\n(k-NN)"],
       [st_bl, st_gcn, st_sage], color=[C["gray"],C["green"],C["orange"]], width=0.5, edgecolor="white")
for bar, val in zip(ax.patches, [st_bl, st_gcn, st_sage]):
    ax.text(bar.get_x()+bar.get_width()/2, val+0.005, f"{val:.4f}", ha="center", fontsize=6.5, fontweight="bold")
ax.set_ylabel("F1-macro", fontsize=7)
ax.set_title("(K) ST Graph Methods", loc="left", fontweight="bold", fontsize=8)

# (L) Label Complexity
ax = axes[5, 1]
lc = {"ohsumed":1650, "pubmed_multilabel":16, "pgb":3, "spatial_tracker":6}
pts = []
for ds, nl in lc.items():
    dfk = ds if ds != "spatial_tracker" else None
    if dfk:
        for feat in ["tfidf","biobert","lda","meta"]:
            s = clf[(clf["dataset"]==dfk)&(clf["feature"]==feat)].dropna(subset=["f1_macro"])
            if not s.empty: pts.append((nl, s["f1_macro"].max(), feat))
for _, r in st6.iterrows(): pts.append((6, r["f1_macro"], r["method"]))
xv = [x[0] for x in pts]; yv = [x[1] for x in pts]
fcl = {"tfidf":C["blue"],"biobert":C["green"],"lda":C["orange"],"meta":C["purple"]}
cfl = [fcl.get(x[2], C["gray"]) if x[2] not in ["TF-IDF+SVM","BioBERT+LR","BioBERT+MLP"] else C["red"] for x in pts]
ax.scatter(xv, yv, c=cfl, s=30, alpha=0.7, edgecolors="none")
lx = np.log10(xv); sl, itc, rv, _, _ = sp_stats.linregress(lx, yv)
xl = np.logspace(np.log10(min(xv)), np.log10(max(xv)), 100)
ax.plot(xl, sl*np.log10(xl)+itc, "--", color="gray", lw=0.8, alpha=0.6)
ax.set_xscale("log"); ax.set_xlabel("Number of Labels (log)", fontsize=7)
ax.set_ylabel("Best F1-macro", fontsize=7)
ax.set_title(f"(L) Label Complexity (r={rv:.2f})", loc="left", fontweight="bold", fontsize=8)

save(fig, "fig3_unsupervised_multilabel_graph")
print("Fig 3 done.")



# ── Standalone panels ──
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch
from collections import Counter
from scipy import stats as S
from plot_utils import C, PALETTE, sig_annotate
_PD = Path(__file__).resolve().parent.parent / "figures" / "panels"
_PD.mkdir(parents=True, exist_ok=True)
def _s(l, w, h, fn):
    pf = plt.figure(figsize=(w, h), facecolor="white")
    pa = pf.add_axes([0.1, 0.08, 0.87, 0.87]); fn(pa)
    pf.savefig(str(_PD / f"fig3_{l}.png"), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(pf)

# Reload data
_REPO = Path(__file__).resolve().parent.parent.parent
_BMLP = pd.read_csv(_REPO / "experiments" / "002_biobert_mlp" / "results" / "biobert_mlp.csv")
_LDA = pd.read_csv(_REPO / "experiments" / "003_lda_cluster" / "results" / "lda_cluster.csv").drop_duplicates(subset=["dataset"])
_CLF = pd.read_csv(_REPO / "experiments" / "001_classical_matrix" / "results" / "classical_matrix.csv")
_ML = pd.read_csv(_REPO / "experiments" / "004_multilabel_strategy" / "results" / "multilabel_strategy.csv")
_GM = pd.read_csv(_REPO / "experiments" / "005_graph_models" / "results" / "graph_models.csv")
_TL = pd.read_csv(_REPO / "experiments" / "007_transfer_learning" / "results" / "transfer_learning.csv")
_DS = ["ohsumed","pubmed_multilabel","pgb"]
_DL = ["OHSUMED","PML","PGB"]
_DC = [C["blue"],C["green"],C["orange"]]
_BC = {}
for ds in _DS:
    s = _CLF[_CLF["dataset"]==ds].dropna(subset=["f1_macro"])
    if not s.empty: _BC[ds] = s["f1_macro"].max()

def _cp(fa, fb):
    if pd.isna(fa) or pd.isna(fb) or not str(fa).strip(): return None
    try:
        a = np.array([float(x) for x in str(fa).split(",")])
        b = np.array([float(x) for x in str(fb).split(",")])
        return S.ttest_rel(a,b)[1] if len(a)==len(b) else S.ttest_ind(a,b)[1]
    except: return None

# A: BioBERT vs Classical
_bv = [_BMLP[_BMLP["dataset"]==ds]["f1_macro"].values[0] if not _BMLP[_BMLP["dataset"]==ds].empty else 0 for ds in _DS]
_cv = [_BC.get(ds, 0) for ds in _DS]
_s("A", 5, 3.5, lambda ax: (
    [ax.bar(i-0.15, _cv[i], 0.3, color=_DC[i], edgecolor="white", linewidth=0.5, alpha=0.9) for i in range(3)],
    [ax.bar(i+0.15, _bv[i], 0.3, color=_DC[i], edgecolor="white", linewidth=0.5, alpha=0.9, hatch="////") for i in range(3)],
    ax.legend(handles=[Patch(facecolor="gray",edgecolor="white",label="Best Classical"),
                       Patch(facecolor="gray",edgecolor="white",hatch="////",label="BioBERT+MLP")], fontsize=7, frameon=False, ncol=2),
    ax.set_xticks(range(3)), ax.set_xticklabels(_DL, fontsize=8),
    ax.set_ylabel("F1-macro", fontsize=10),
    ax.set_title("BioBERT+MLP vs Best Classical", fontweight="bold", fontsize=11)))

# B: LDA NMI
_lda_v = [float(_LDA[_LDA["dataset"]==ds]["nmi"].values[0]) if not _LDA[_LDA["dataset"]==ds].empty else 0 for ds in _DS]
_s("B", 5, 3.5, lambda ax: (
    ax.bar(_DL, _lda_v, color=_DC, width=0.5, edgecolor="white"),
    [ax.text(i, v+0.01, f"{v:.3f}", ha="center", fontsize=8) for i, v in enumerate(_lda_v)],
    ax.set_ylabel("NMI", fontsize=10),
    ax.set_title("LDA Clustering Quality (NMI)", fontweight="bold", fontsize=11)))

# C: Unsup vs Sup
_s("C", 5, 3.5, lambda ax: (
    ax.bar(np.arange(3)-0.15, _lda_v, 0.3, color=C["purple"], label="NMI (unsupervised)", edgecolor="white"),
    ax2 := ax.twinx(),
    ax2.bar(np.arange(3)+0.15, [_BC.get(ds,0) for ds in _DS], 0.3, color=C["green"], alpha=0.6, label="F1 (supervised)", edgecolor="white"),
    ax.set_ylabel("NMI", fontsize=10), ax2.set_ylabel("F1-macro", fontsize=10, color=C["green"]),
    ax.set_xticks(range(3)), ax.set_xticklabels(_DL, fontsize=8),
    ax.set_title("Unsupervised vs Supervised", fontweight="bold", fontsize=11),
    ax.legend(fontsize=7, frameon=False, loc="upper left")))

# D: Cost-Benefit
_s("D", 5, 3.5, lambda ax: (
    ax.text(0.5, 0.5, "See composite Fig3-D", ha="center", va="center", fontsize=10, color="gray", transform=ax.transAxes),
    ax.set_title("Cost-Benefit Landscape", fontweight="bold", fontsize=11)))

# E: Multi-label Strategy
_pml_ml = _ML[_ML["dataset"]=="pubmed_multilabel"]
_sv = _pml_ml["f1_macro"].values; _se = _pml_ml["f1_macro_std"].values
_s("E", 5, 3.5, lambda ax: (
    ax.bar(_pml_ml["strategy"].values.astype(str), _sv, yerr=_se, color=[C["blue"],C["green"],C["orange"]], width=0.5, capsize=3, edgecolor="white"),
    ax.set_ylabel("F1-macro", fontsize=10),
    ax.set_title("Multi-label Strategy (PML)", fontweight="bold", fontsize=11)))

# F: F1 vs Time
_s("F", 5, 3.5, lambda ax: (
    ax.bar(_pml_ml["strategy"].values.astype(str), _sv, color=[C["blue"],C["green"],C["orange"]], width=0.4, alpha=0.7, edgecolor="white"),
    ax.set_ylabel("F1-macro", fontsize=10),
    ax.set_title("F1 vs Time Cost (PML)", fontweight="bold", fontsize=11)))

# G: OHSUMED zoom
_ohs_ml = _ML[_ML["dataset"]=="ohsumed"]
_osv = _ohs_ml["f1_macro"].values
_s("G", 5, 3.5, lambda ax: (
    ax.bar(_ohs_ml["strategy"].values.astype(str), _osv, color=[C["blue"],C["green"],C["orange"]], width=0.5, edgecolor="white"),
    [ax.text(i, v+0.0002, f"{v:.4f}", ha="center", fontsize=8) for i, v in enumerate(_osv)],
    ax.set_ylim(0, max(_osv)*1.3),
    ax.set_ylabel("F1-macro", fontsize=10),
    ax.set_title("OHSUMED (1,650 labels)", fontweight="bold", fontsize=11)))

# H: Model Robustness
_MOD = ["NaiveBayes","k-NN","SVM","LogisticReg","RandomForest","AdaBoost","XGBoost"]
_MODL = dict(zip(_MOD,["NB","kNN","SVM","LR","RF","Ada","XGB"]))
_bd = [_CLF[(_CLF["model"]==m)&(_CLF["dataset"]=="pubmed_multilabel")]["f1_macro"].dropna().values for m in _MOD]
_s("H", 5, 3.5, lambda ax: (
    [ax.boxplot(_bd, tick_labels=[_MODL[m] for m in _MOD], patch_artist=True, widths=0.6)],
    ax.set_ylabel("F1-macro (PML)", fontsize=10),
    ax.set_title("Model Robustness Across Features", fontweight="bold", fontsize=11)))

# I: Node2Vec
_n2v = _GM[_GM["feature"]=="node2vec"].reset_index(drop=True)
_nm = [r["model"].replace("Node2Vec+","") for _, r in _n2v.iterrows()]
_nv = _n2v["f1_macro"].values
_s("I", 5, 3.5, lambda ax: (
    ax.bar(range(len(_nm)), _nv, color=C["blue"], width=0.5, edgecolor="white"),
    ax.set_xticks(range(len(_nm))), ax.set_xticklabels(_nm, fontsize=7),
    ax.set_ylabel("F1-macro", fontsize=10),
    ax.set_title("Node2Vec + Classifiers", fontweight="bold", fontsize=11)))

# J: Graph Methods
_gcn = _GM[_GM["model"]=="GCN"].iloc[0]; _sage = _GM[_GM["model"]=="GraphSAGE"].iloc[0]
_n2v_best = _n2v.loc[_n2v["f1_macro"].idxmax()]
_s("J", 5, 3.5, lambda ax: (
    ax.bar(range(3), [_gcn["f1_macro"],_sage["f1_macro"],_n2v_best["f1_macro"]],
           color=[C["green"],C["orange"],C["blue"]], width=0.5, edgecolor="white"),
    ax.set_xticks(range(3)), ax.set_xticklabels(["GCN","GraphSAGE","Node2Vec\n(best)"], fontsize=7),
    ax.set_ylabel("F1-macro", fontsize=10),
    ax.set_title("Graph Methods (PGB)", fontweight="bold", fontsize=11)))

# K: ST Graph
_d1 = _TL[_TL["exp_id"]=="D1"]; _d2 = _TL[_TL["exp_id"]=="D2"]; _b1 = _TL[_TL["exp_id"]=="B1"]
_s("K", 5, 3.5, lambda ax: (
    ax.bar(["BioBERT+LR\n(baseline)","GCN\n(k-NN)","GraphSAGE\n(k-NN)"],
           [_b1["f1_macro"].values[0] if not _b1.empty else 0,
            _d1["f1_macro"].values[0] if not _d1.empty else 0,
            _d2["f1_macro"].values[0] if not _d2.empty else 0],
           color=[C["gray"],C["green"],C["orange"]], width=0.5, edgecolor="white"),
    ax.set_ylabel("F1-macro", fontsize=10),
    ax.set_title("ST Graph Methods", fontweight="bold", fontsize=11)))

# L: Label Complexity
_lc = {"ohsumed":1650,"pubmed_multilabel":16,"pgb":3}
_pts = []
for ds, nl in _lc.items():
    for feat in ["tfidf","biobert","lda","meta"]:
        s = _CLF[(_CLF["dataset"]==ds)&(_CLF["feature"]==feat)].dropna(subset=["f1_macro"])
        if not s.empty: _pts.append((nl, s["f1_macro"].max()))
_st6 = pd.read_csv(_REPO/"experiments"/"006_st_benchmark"/"results"/"st_benchmark.csv")
for _, r in _st6.iterrows(): _pts.append((6, r["f1_macro"]))
_xv = [x[0] for x in _pts]; _yv = [x[1] for x in _pts]
_lx = np.log10(_xv)
_sl, _itc, _rv, _, _ = S.linregress(_lx, _yv)
_s("L", 5, 3.5, lambda ax: (
    ax.scatter(_xv, _yv, c=C["blue"], s=30, alpha=0.7, edgecolors="none"),
    ax.plot(np.logspace(np.log10(min(_xv)),np.log10(max(_xv)),100),
            _sl*np.log10(np.logspace(np.log10(min(_xv)),np.log10(max(_xv)),100))+_itc, "--", color="gray", lw=0.8, alpha=0.6),
    ax.set_xscale("log"), ax.set_xlabel("Number of Labels (log)", fontsize=10),
    ax.set_ylabel("Best F1-macro", fontsize=10),
    ax.set_title(f"Label Complexity (r={_rv:.2f})", fontweight="bold", fontsize=11)))
print("  panels A-L saved")
