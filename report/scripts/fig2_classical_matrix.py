
"""Fig 2 — Classical Algorithm Matrix: stacked layout."""
import sys, numpy as np, pandas as pd, matplotlib.pyplot as plt
from pathlib import Path
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
p = Path(__file__).resolve().parent
sys.path.insert(0, str(p))
from plot_utils import save, C, PALETTE, sig_annotate

REPO = p.parent.parent
df = pd.read_csv(REPO / "experiments" / "001_classical_matrix" / "results" / "classical_matrix_with_folds.csv")
Dl = {"ohsumed": "OHSUMED\n(1,650 labels)", "pubmed_multilabel": "PubMed-MultiLabel\n(16 labels)", "pgb": "PGB\n(3 labels)"}
Fl = ["tfidf","biobert","lda","meta"]
FL = dict(zip(Fl,["TF-IDF","BioBERT","LDA","Meta"]))
FC = dict(zip(Fl,[C["blue"],C["green"],C["orange"],C["purple"]]))
Ml = ["AdaBoost","LogisticReg","NaiveBayes","RandomForest","SVM","XGBoost","k-NN"]
MS = dict(zip(Ml,["Ada","LR","NB","RF","SVM","XGB","kNN"]))
DC = [C["blue"],C["green"],C["orange"]]
def cp(fa,fb):
    from scipy import stats as S
    if pd.isna(fa) or pd.isna(fb) or not str(fa).strip(): return None
    try:
        a=np.array([float(x) for x in str(fa).split(",")]); b=np.array([float(x) for x in str(fb).split(",")])
        return S.ttest_rel(a,b)[1] if len(a)==len(b) else S.ttest_ind(a,b)[1]
    except: return None

# Heatmaps
mats = {}
for ds in Dl:
    s = df[df["dataset"]==ds]; m = np.full((7,4),np.nan)
    for i,mo in enumerate(Ml):
        for j,fe in enumerate(Fl):
            r = s[(s["model"]==mo)&(s["feature"]==fe)]
            if not r.empty and "f1_macro" in r.columns: m[i,j]=r["f1_macro"].values[0]
    mats[ds]=m
av = np.concatenate([m.flatten() for m in mats.values()]); av=av[~np.isnan(av)]
vm,vx=0,np.percentile(av,95)*1.05
dls=list(Dl.keys())

fig = plt.figure(figsize=(10,10))
gs = fig.add_gridspec(4,4,width_ratios=[1,1,1,0.06],height_ratios=[1.2,0.5,0.8,0.65],hspace=0.45,wspace=0.22,left=0.05,right=0.92,top=0.94,bottom=0.07)

for ci,ds in enumerate(dls):
    ax=fig.add_subplot(gs[0,ci]); mat=mats[ds]
    im=ax.imshow(mat,aspect="auto",cmap="YlOrRd",norm=Normalize(vm,vx))
    for i in range(7):
        for j in range(4):
            v=mat[i,j]
            if not np.isnan(v): ax.text(j,i,f"{v:.3f}",ha="center",va="center",fontsize=5.2,color="white" if v>(vm+vx)/2 else "black")
    ax.set_xticks(range(4)); ax.set_xticklabels([FL[f] for f in Fl],rotation=30,ha="right",fontsize=7)
    ax.set_yticks(range(7)); ax.set_yticklabels([MS[m] for m in Ml],fontsize=7)
    ax.set_title(f"({chr(65+ci)}) {Dl[ds]}",loc="center",fontweight="bold",fontsize=8)
cax=fig.add_subplot(gs[0,3]); plt.colorbar(im,cax=cax).set_label("F1-macro",fontsize=7)

ax=fig.add_subplot(gs[1,0])
bd={}
for ds in Dl:
    s=df[df["dataset"]==ds]; bd[ds]=s.loc[s["f1_macro"].idxmax(),"f1_macro"] if not s.empty else 0
ba=ax.bar(["OHSUMED","PML","PGB"],[bd[k] for k in dls],color=DC,width=0.5)
ax.set_ylabel("Best F1-macro",fontsize=7); ax.set_title("(D) Best per Dataset",loc="left",fontweight="bold",fontsize=8)
for b,v in zip(ba,[bd[k] for k in dls]): ax.text(b.get_x()+b.get_width()/2,b.get_height()+0.005,f"{v:.3f}",ha="center",fontsize=6.5)

ax=fig.add_subplot(gs[1,1:4])
# Shift E right to increase D-E gap
_be=ax.get_position(); ax.set_position([_be.x0+0.04,_be.y0,_be.width-0.04,_be.height])
DSH=dict(zip(dls,["OHSU","PML","PGB"]))
tdf=pd.DataFrame([{"l":f"{DSH[ds]}/{FL[f]}","t":s2["train_time_s"].mean()} for ds in dls for f in Fl for s2 in [df[(df["dataset"]==ds)&(df["feature"]==f)]] if not s2.empty]).sort_values("t")
ax.barh(range(len(tdf)),tdf["t"].values,color=C["blue"],height=0.6)
ax.set_yticks(range(len(tdf))); ax.set_yticklabels(tdf["l"].values,fontsize=5.5)
ax.set_xlabel("Time (s, log)",fontsize=7); ax.set_xscale("log")
ax.set_title("(E) Training Time",loc="left",fontweight="bold",fontsize=8)

def tn(dk):
    s=df[df["dataset"]==dk].dropna(subset=["f1_macro"]); return s.nlargest(5,"f1_macro")
ax=fig.add_subplot(gs[2,0])
t5=tn("pubmed_multilabel")
lb=[f"{FL[r['feature']]}/{MS[r['model']]}" for _,r in t5.iterrows()]
va,er=t5["f1_macro"].values,t5["f1_macro_std"].values
ax.bar(range(len(lb)),va,yerr=er,color=[FC[r["feature"]] for _,r in t5.iterrows()],width=0.6,capsize=2,edgecolor="white",linewidth=0.3)
if len(va)>1:
    by=max(va[k]+er[k] for k in range(len(va)))
    for i in range(1,len(va)):
        sig_annotate(ax,0,i,by+0.045*(i-1),cp(t5.iloc[0].get("f1_macro_folds"),t5.iloc[i].get("f1_macro_folds")))
    ax.set_ylim(0,by+0.045*(len(va)-2)+by*0.2)
ax.set_xticks(range(len(lb))); ax.set_xticklabels(lb,rotation=30,ha="right",fontsize=6.5)
ax.set_ylabel("F1-macro",fontsize=7); ax.set_title("(F) PML — Top 5",loc="left",fontweight="bold",fontsize=8)

ax=fig.add_subplot(gs[2,1])
t5=tn("ohsumed")
lb=[f"{FL[r['feature']]}/{MS[r['model']]}" for _,r in t5.iterrows()]
va,er=t5["f1_macro"].values,t5["f1_macro_std"].values
ax.bar(range(len(lb)),va,yerr=er,color=[FC[r["feature"]] for _,r in t5.iterrows()],width=0.6,capsize=2,edgecolor="white",linewidth=0.3)
ax.set_xticks(range(len(lb))); ax.set_xticklabels(lb,rotation=30,ha="right",fontsize=6.5)
ax.set_ylabel("F1-macro",fontsize=7); ax.set_title("(G) OHSUMED — Top 5",loc="left",fontweight="bold",fontsize=8)

ax=fig.add_subplot(gs[2,2:4])
x,w=np.arange(4),0.22
for idx,ds in enumerate(["pubmed_multilabel","ohsumed","pgb"]):
    bp=[df[(df["dataset"]==ds)&(df["feature"]==f)]["f1_macro"].max() if not df[(df["dataset"]==ds)&(df["feature"]==f)].empty else 0 for f in Fl]
    ax.bar(x+idx*w,bp,w,color=DC[idx],label=["PML","OHSUMED","PGB"][idx],edgecolor="white",linewidth=0.3)
ax.set_xticks(x+w); ax.set_xticklabels([FL[f] for f in Fl],fontsize=7)
ax.set_ylabel("Best F1-macro",fontsize=7); ax.set_title("(H) Feature Effectiveness",loc="left",fontweight="bold",fontsize=8)
ax.legend(fontsize=6,frameon=False,ncol=3)

ax=fig.add_subplot(gs[3,:])
for ds,mk in [("ohsumed","o"),("pubmed_multilabel","s"),("pgb","^")]:
    sub=df[df["dataset"]==ds].dropna(subset=["f1_macro","train_time_s"])
    for feat,clr in FC.items():
        sf=sub[sub["feature"]==feat]
        if not sf.empty: ax.scatter(sf["train_time_s"],sf["f1_macro"],c=clr,marker=mk,s=12,alpha=0.7,edgecolors="none")
ax.set_xscale("log"); ax.set_xlabel("Training Time (s, log)",fontsize=7); ax.set_ylabel("F1-macro",fontsize=7)
ax.set_title("(I) Performance vs. Time",loc="left",fontweight="bold",fontsize=8)
dl=[Line2D([0],[0],marker="o",color="w",markerfacecolor="gray",markersize=5,label="OHSUMED"),
    Line2D([0],[0],marker="s",color="w",markerfacecolor="gray",markersize=5,label="PML"),
    Line2D([0],[0],marker="^",color="w",markerfacecolor="gray",markersize=5,label="PGB")]
fl=[Line2D([0],[0],color=c,lw=2,label=l) for l,c in [("TF-IDF",C["blue"]),("BioBERT",C["green"]),("LDA",C["orange"]),("Meta",C["purple"])]]
l1=ax.legend(handles=dl,loc="upper right",fontsize=5.5,frameon=False,title="Dataset",title_fontsize=6)
ax.add_artist(l1)
ax.legend(handles=fl,loc="upper left",fontsize=5.5,frameon=False,title="Feature",title_fontsize=6)
save(fig,"fig2_classical_matrix"); print("Fig 2 done.")
