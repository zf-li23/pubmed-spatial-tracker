"""Fig 6 — ST Benchmark + Transfer Learning (merged from former fig6 + fig7).

3×4 composite:
  Row 0: (A) ST bars  |  (B) Feature Importance (span 2 cols) | cb
  Row 1: (C) Acc vs F1|  (D) Tag Co-occurrence Network (span 2 cols)
  Row 2: (E) TL Waterfall | (F) Pre-training Cost-Benefit (span 2 cols)
"""
import sys, numpy as np, pandas as pd, matplotlib.pyplot as plt
from pathlib import Path
from collections import Counter
from matplotlib.colors import CenteredNorm
from matplotlib.lines import Line2D
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
p = Path(__file__).resolve().parent
sys.path.insert(0, str(p))
from plot_utils import save, C, PALETTE, sig_annotate

REPO = p.parent.parent
st = pd.read_csv(REPO / "experiments" / "006_st_benchmark" / "results" / "st_benchmark.csv")
ann = pd.read_csv(REPO / "data" / "spatial_tracker" / "annotated_articles.csv")
tl = pd.read_csv(REPO / "experiments" / "007_transfer_learning" / "results" / "transfer_learning.csv")

fig = plt.figure(figsize=(13, 11))
gs = fig.add_gridspec(3, 4, width_ratios=[1, 1, 1, 0.04],
                      height_ratios=[1.2, 1.1, 0.7],
                      hspace=0.4, wspace=0.22, left=0.06, right=0.93, top=0.95, bottom=0.06)

# ═══════════════════════════════════════════════════════════════
# Row 0: (A) Feature Importance — full width
# ═══════════════════════════════════════════════════════════════
ax = fig.add_subplot(gs[0, :3])
texts = ann["title"].fillna("")
vec = TfidfVectorizer(max_features=2000, stop_words="english", sublinear_tf=True)
X_t = vec.fit_transform(texts)
fn = vec.get_feature_names_out()
cl = ["Research","Protocol","Technology","Data Resource","Benchmark","Review"]
ci = {c: i for i, c in enumerate(cl)}
yn = np.array([ci.get(c, -1) for c in ann["category"].values])
ok = yn >= 0
X_t, yn = X_t[ok], yn[ok]
svm = LinearSVC(C=1.0, dual="auto", random_state=42, max_iter=2000)
svm.fit(X_t, yn)
n_top = 4
ct, fn_l = {}, list(fn)
for i, cat in enumerate(cl):
    ti = np.argsort(svm.coef_[i])[-n_top:][::-1]
    ct[cat] = [(fn[idx], svm.coef_[i][idx]) for idx in ti]
th, tw = {}, {}
for i, cat in enumerate(cl):
    for term, w in ct[cat]:
        tw[(cat, term)] = w
        if term not in th:
            tidx = fn_l.index(term)
            th[term] = int(np.argmax([svm.coef_[j][tidx] for j in range(len(cl))]))
at = list(dict.fromkeys([t for ts in ct.values() for t, _ in ts]))
at.sort(key=lambda t: (th.get(t, 0), -max(svm.coef_[th.get(t, 0)][fn_l.index(t)], 0)))
heat = np.zeros((len(cl), len(at)))
for i, cat in enumerate(cl):
    for j, term in enumerate(at):
        heat[i, j] = tw.get((cat, term), 0)
im = ax.imshow(heat, aspect="auto", cmap="RdBu_r", norm=CenteredNorm())
ax.set_xticks([])
gb = []; cc = th[at[0]]; gs0 = 0
for j, term in enumerate(at):
    if th[term] != cc:
        gb.append((gs0, j, cc)); gs0 = j; cc = th[term]
gb.append((gs0, len(at), cc))
DC6 = [C["blue"],C["green"],C["orange"],C["purple"],C["brown"],C["gray"]]
for s, e, cix in gb:
    mid = (s + e - 1) / 2
    ax.text(mid, 6.6, cl[cix].replace(" ", "\n"), ha="center", va="top", fontsize=6.5, fontweight="bold", color=DC6[cix])
    for j in range(s, e):
        ax.text(j, 5.6, at[j], ha="center", va="top", fontsize=5.5, rotation=25, color="gray")
    if e < len(at): ax.axvline(e - 0.5, color="white", lw=1.5, ls="--", alpha=0.5)
ax.set_yticks(range(len(cl))); ax.set_yticklabels(cl, fontsize=6.5)
ax.set_title("(A) Top TF-IDF Terms by Category", loc="left", fontweight="bold", fontsize=9)
plt.colorbar(im, ax=ax, fraction=0.03, pad=0.01, label="SVM coeff")

# ═══════════════════════════════════════════════════════════════
# Row 1: (B) ST bars  (C) Acc vs F1  (D) Tag Network
# ═══════════════════════════════════════════════════════════════

# (B) ST Benchmark bars
ax = fig.add_subplot(gs[1, 0])
methods = [r["method"] for _, r in st.iterrows()]
f1_v, f1_e = st["f1_macro"].values, st["f1_macro_std"].values
cls_b = [C["blue"], C["green"], C["orange"]]
ax.bar(methods, f1_v, yerr=f1_e, color=cls_b, width=0.5, capsize=3, edgecolor="white")
ax.set_ylabel("F1-macro", fontsize=7)
ax.set_title("(B) ST Benchmark", loc="left", fontweight="bold", fontsize=8)
ax.set_xticks(range(len(methods)))
ax.set_xticklabels(methods, rotation=15, ha="right", fontsize=6.5)

def _cp(fa, fb):
    from scipy import stats as S
    if pd.isna(fa) or pd.isna(fb) or not str(fa).strip(): return None
    try:
        a = np.array([float(x) for x in str(fa).split(",")])
        b = np.array([float(x) for x in str(fb).split(",")])
        return S.ttest_rel(a, b)[1] if len(a) == len(b) else S.ttest_ind(a, b)[1]
    except: return None

bt = [f1_v[k] + f1_e[k] for k in range(len(methods))]
by = max(bt)
for i in range(len(methods)):
    for j in range(i + 1, len(methods)):
        pv = _cp(st.iloc[i].get("f1_macro_folds"), st.iloc[j].get("f1_macro_folds"))
        sig_annotate(ax, i, j, by + 0.04 * (abs(j - i) - 1), pv)
ax.set_ylim(0, by + 0.04 * (len(methods) - 1) + by * 0.15)

# (C) Accuracy vs F1
ax = fig.add_subplot(gs[1, 1])
ax.scatter(st["accuracy"].values, f1_v, color=cls_b, s=60, zorder=5, edgecolors="white", linewidth=0.5)
for i, m in enumerate(methods):
    ax.annotate(m.split("+")[-1] if "+" in m else m, (st["accuracy"].values[i], f1_v[i]),
                fontsize=6.5, ha="center", va="bottom", xytext=(0, 6), textcoords="offset points")
ax.set_xlabel("Accuracy", fontsize=7); ax.set_ylabel("F1-macro", fontsize=7)
ax.set_xlim(0.91, 0.945); ax.set_ylim(0.6, 0.87)
ax.set_title("(C) Acc vs F1", loc="left", fontweight="bold", fontsize=8)

# (D) Tag Network
ax = fig.add_subplot(gs[1, 2])
def sc(s):
    r = []; [r.extend([x.strip() for x in str(v).split("; ")]) for v in s.dropna()]; return r
all_tags = sc(ann["tags"])
tc = Counter(all_tags)
tt = [t for t, _ in tc.most_common(10)]
cooc = np.zeros((10, 10))
for _, row in ann.iterrows():
    tags = set(str(row["tags"]).split("; ")) if pd.notna(row["tags"]) else set()
    for i, t1 in enumerate(tt):
        for j, t2 in enumerate(tt):
            if i < j and t1 in tags and t2 in tags: cooc[i, j] += 1; cooc[j, i] += 1
for i in range(10): cooc[i, i] = tc[tt[i]]
em = cooc.copy(); np.fill_diagonal(em, 0); emx = em.max() or 1
nx, ny = [], []
for i in range(10):
    a = 2 * np.pi * i / 10 - np.pi / 2
    nx.append(np.cos(a)); ny.append(np.sin(a))
for i in range(10):
    for j in range(i + 1, 10):
        if cooc[i, j] > 0:
            ax.plot([nx[i], nx[j]], [ny[i], ny[j]], color="gray", lw=max(0.2, cooc[i, j] / emx * 3), alpha=0.4, zorder=1)
sz = [max(20, tc[tt[i]] / tc[tt[0]] * 300) for i in range(10)]
ax.scatter(nx, ny, s=sz, c=C["blue"], alpha=0.8, edgecolors="white", linewidth=0.5, zorder=5)
for i in range(10):
    lbl = tt[i].replace("Spatial ", "Sp.\n").replace("Cell-Cell Communication", "Cell-Cell\nCommunication")
    ax.annotate(lbl, (nx[i], ny[i]), fontsize=4.5, ha="center", va="center",
               bbox=dict(boxstyle="round,pad=0.15", facecolor="white", alpha=0.8, edgecolor="none"))
ax.set_xlim(-1.3, 1.3); ax.set_ylim(-1.3, 1.3); ax.set_aspect("equal"); ax.axis("off")
ax.set_title("(D) Tag Co-occurrence", loc="left", fontweight="bold", fontsize=8)

# ── (E) TL Waterfall ──
ax = fig.add_subplot(gs[2, 0])
fm = {r["exp_id"]: r["f1_macro"] for _, r in tl.iterrows()}
eo = ["A1","A2","A4","A5","B3","B1","B2","D2","D1","C2","C1"]
avail = [e for e in eo if e in tl["exp_id"].values]
vals = [fm[e] for e in avail]
lm = {"A1":"Zero: OHSU→ST\n(LR)","A2":"Zero: PML→ST\n(LR)","A4":"Zero: PML→ST\n(XGB)","A5":"Zero: PGB→ST\n(LR)",
      "B1":"ST→ST\n(LR)","B2":"ST→ST\n(MLP)","B3":"ST→ST\n(XGB)","C1":"PML→ST\n(MLP+FT)","C2":"OHSU→ST\n(MLP+FT)","D1":"GCN","D2":"GraphSAGE"}
ls = [lm.get(e, e) for e in avail]
cs = [C["red"] if e[0]=="A" else C["blue"] if e[0]=="B" else C["green"] if e[0]=="C" else C["purple"] for e in avail]
ax.bar(range(len(ls)), vals, color=cs, width=0.5, edgecolor="white")
ax.set_xticks(range(len(ls))); ax.set_xticklabels(ls, fontsize=5, rotation=25, ha="right")
ax.set_ylabel("F1-macro", fontsize=7)
ax.set_title("(E) TL Waterfall", loc="left", fontweight="bold", fontsize=8)

# ── (F) Pre-training Cost ──
ax = fig.add_subplot(gs[2, 1:3])
b2 = tl[tl["exp_id"]=="B2"].iloc[0]; c1 = tl[tl["exp_id"]=="C1"].iloc[0]; c2 = tl[tl["exp_id"]=="C2"].iloc[0]
b2t, c1p, c1f = b2["train_time_s"], c1["pretrain_time_s"], c1["finetune_time_s"]
c2p, c2f = c2["pretrain_time_s"], c2["finetune_time_s"]
ax.barh(0, b2t, 0.4, color=C["blue"], edgecolor="white", label="Train")
ax.barh(1, c1p, 0.4, color=C["gray"], edgecolor="white", label="Pre-train")
ax.barh(1, c1f, 0.4, left=c1p, color=C["green"], edgecolor="white", label="Fine-tune")
ax.barh(2, c2p, 0.4, color=C["gray"], edgecolor="white")
ax.barh(2, c2f, 0.4, left=c2p, color=C["orange"], edgecolor="white")
f1m = fm.get("B2", 0); f1c1 = fm.get("C1", 0); f1c2 = fm.get("C2", 0)
for yp, tt, f1v, clr in [(0, b2t, f1m, C["blue"]), (1, c1p+c1f, f1c1, C["green"]), (2, c2p+c2f, f1c2, C["orange"])]:
    ax.text(tt + 15, yp, f"F1={f1v:.4f}", va="center", fontsize=6.5, color=clr, fontweight="bold")
ax.set_yticks(range(3)); ax.set_yticklabels(["ST→ST","PML→ST","OHSU→ST"], fontsize=6.5)
ax.set_xlabel("Time (s)", fontsize=7)
ax.set_title("(F) Pre-training Cost", loc="left", fontweight="bold", fontsize=8)
ax.legend(fontsize=5, frameon=False, loc="lower right")

save(fig, "fig4_st_benchmark_transfer")
print("Fig 4 done.")
