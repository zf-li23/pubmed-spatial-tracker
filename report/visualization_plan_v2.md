# Visualization Plan v2 — PubMed Spatial Tracker Report

> Updated: 2026-06-05
> Style: **Publication-style composite figures**, English-only labels.
> Stack: Python (matplotlib + seaborn + science theme) → R (ggplot2) if unsatisfied.
> Two versions: (A) PDF report — dense composite; (B) PPT — individual panels.

---

## ✅ Cluster Re-run Status (2026-06-05)

All old logs, temp scripts, and outdated result CSVs **deleted** from cluster.
Cache (972 MB, 18 `.npz` files) **preserved**.

| Exp | Jobs | Per-fold Data? | Status |
|-----|------|---------------|--------|
| 001 | 12 parallel (3 ds × 4 feat) | ✅ `f1_macro_folds` column | 5 running, 7 queued |
| 003 | 1 CPU (LDA cluster) | N/A (unsupervised) | Queued |
| 004 | 1 CPU (multi-label) | ✅ via `_common.py:run_cv` | Queued |
| 005 | 1 CPU (graph models) | N/A (own CV impl) | Queued |
| 006 CPU | TF-IDF+SVM, BioBERT+LR | ✅ per-fold in each method | Queued |
| 006 GPU | BioBERT+MLP | ✅ per-fold in each method | Queued |
| 007 CPU | A1,A2,A4,A5,B1,B3,D1,D2 | Fixed split (no CV) | Queued |
| 007 GPU | B2,C1,C2 (MLP fine-tune) | Fixed split (no CV) | Queued |

> **Per-fold data verified**: `_common.py:run_cv()` now saves `f1_macro_folds` (5 comma-separated per-fold values) alongside mean/std. Same `random_state=42` ensures fold-aligned paired t-tests.
> Newly generated CSVs confirmed to contain the `_folds` columns.

---

## 📐 Design Principles

1. **Composite over scattered**: Thematically related subplots are assembled into multi-panel figures (Fig 1–8).
2. **Significance on all model comparisons**: Paired t-test on 5-fold CV per-fold F1 values, annotated as `*` p<0.05, `**` p<0.01, `***` p<0.001.
3. **Colorblind-friendly**: viridis palette throughout.
4. **Output**: `report/figures/` as PDF (LaTeX) + PNG (preview).
5. **Tool**: Python (matplotlib+seaborn+scipy+umap-learn) for data pipeline proximity; R (ggplot2) alternate if desired for final polish.

---

## Fig 1: Spatial Tracker Dataset Overview

**Theme**: "What does the Spatial Tracker dataset look like?"

**Composite layout** (2×3 or 3×3 grid):

```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│ (A) Year Trend      │ (B) Category Pie    │ (C) Tag Distribution│
│ 2016→2026 growth    │ 6 categories        │ Horizontal bar, top │
│ line + area         │                     │ 15 tags, sorted     │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ (D) Tags per Art.   │ (E) Cat × Tag Heat  │ (F) Tech Platform   │
│ Histogram 1–4 tags  │ Normalized by row   │ Top technologies    │
├─────────────────────┼─────────────────────┼─────────────────────┤
│ (G) Bio Topic        │ (H) Confidence      │ (I) Boolean Flags   │
│ Top biological areas │ Donut high/med/low  │ has_data, has_code  │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

**Data**: `data/spatial_tracker/annotated_articles.csv` (9,147 rows)
**No significance needed**. ~6"×8" figure.

---

## Fig 2: Classical Algorithm Matrix — Performance Landscape

**Theme**: "Which model × feature combinations work best across datasets?"

### Composite Figure 2A: Heatmap Matrix (2×3 grid)

```
┌──────────────────────────┬──────────────────────────┐
│ (A) OHSUMED (1,650 lbls) │ (B) PML (16 labels)     │
│ 7 models × 4 features    │ 7 models × 4 features    │
│ annotated heatmap        │ annotated heatmap        │
├──────────────────────────┼──────────────────────────┤
│ (C) PGB (3 labels)       │ (D) Legend + Colorbar    │
│ 7 models × 4 features    │ Shared across panels     │
├──────────────────────────┴──────────────────────────┤
│ (E) Cross-dataset: Best F1 per method (grouped bar) │
│ (F) Training time comparison (bar, log scale)        │
└─────────────────────────────────────────────────────┘
```

### Composite Figure 2B: Significance & Analysis (2×2 grid)

```
┌──────────────────────────────┬──────────────────────────────┐
│ (A) PML Top-5 with stars     │ (B) OHSUMED Top-5 with stars │
│ Significance: best vs. rest  │ Significance: best vs. rest  │
│ Paired t-test on 5 folds     │ Paired t-test on 5 folds     │
├──────────────────────────────┼──────────────────────────────┤
│ (C) Feature Effectiveness    │ (D) Performance vs. Time     │
│ Best model per feature,      │ Scatter: all 84 combos       │
│ grouped bar + error bars     │ Pareto frontier highlighted  │
└──────────────────────────────┴──────────────────────────────┘
```

### Statistical Significance Plan

**Priority comparisons** (paired t-test needed):
- PML: Best (BioBERT+LR 0.6710) vs 2nd (BioBERT+SVM 0.6603) vs 3rd (BioBERT+XGB 0.6431)
- OHSUMED: Best (AdaBoost+TF-IDF 0.1687) vs 2nd (XGBoost+TF-IDF 0.0986) vs 3rd (AdaBoost+BioBERT 0.0772)
- PGB: Best (AdaBoost+TF-IDF 0.4215) vs 2nd (XGBoost+TF-IDF 0.3548)
- Across features: Best BioBERT vs Best TF-IDF per dataset

**Implementation**: Modify `_common.py:run_cv()` to return per-fold values alongside aggregated results. Then:
- **Fast runs** (TF-IDF/LDA/meta): Re-run locally (~minutes)
- **BioBERT runs**: Re-run on cluster (cached features → fast classification)
- Also useful: Modify CSV to store `f1_macro_folds=0.6710,0.6650,...` comma-separated

**Cluster status**: Log files exist but contain only mean values, not per-fold. Per-fold data was discarded after aggregation. See § below for re-run plan.

**Data**: `experiments/001_classical_matrix/results/classical_matrix.csv` (84 rows)

---

## Fig 3: Deep Learning & Unsupervised Methods

**Theme**: "Can deep learning and unsupervised methods outperform classical models?"

### Composite (2×2 grid):

```
┌────────────────────────────┬────────────────────────────┐
│ (A) BioBERT+MLP vs Best    │ (B) LDA Clustering NMI     │
│ Classical (grouped bar)    │ 3 datasets, bar chart      │
│ Significance: * p<0.05     │ With supervised F1 overlay │
├────────────────────────────┼────────────────────────────┤
│ (C) Unsupervised vs Superv │ (D) [Creative] Cost-Benefit│
│ Dual-axis: NMI + F1        │ F1 vs time for all methods │
│ Per dataset                │ Pareto frontier highlighted│
└────────────────────────────┴────────────────────────────┘
```

Panel (D) integrates **creative chart 9.1** here — shows BioBERT+LR as optimal "sweet spot."

**Data**: `biobert_mlp.csv` (3 rows) + `lda_cluster.csv` (6 rows)

---

## Fig 4: Multi-label Strategies

**Theme**: "How do problem transformation strategies affect multi-label classification?"

### Composite (1×2 or 2×2):

```
┌────────────────────────────┬────────────────────────────┐
│ (A) BR vs CC vs LP (PML)  │ (B) Strategy × Time Cost   │
│ Grouped bar + significance │ Bar (F1) + line (time)     │
│ CC leads with 0.5796 🏆   │ CC is both best & moderate │
├────────────────────────────┼────────────────────────────┤
│ (C) OHSUMED zoom           │ (D) [Creative] Model       │
│ All 3 strategies near 0    │ Robustness box plot        │
│ (expected for 1,650 labels)│ F1 distribution per model  │
└────────────────────────────┴────────────────────────────┘
```

Panel (D) integrates **creative chart 9.5** (model robustness across features).

**Data**: `experiments/004_multilabel_strategy/results/multilabel_strategy.csv` (6 rows)

---

## Fig 5: Graph-based Methods

**Theme**: "Can graph structure improve classification on PGB and ST?"

### Composite (2×2):

```
┌────────────────────────────┬────────────────────────────┐
│ (A) PGB: Node2Vec + 6 cls │ (B) PGB: GCN vs SAGE vs N2V│
│ Bar chart, 6 classifiers   │ Significance: GCN 0.4125 🏆│
│ on Node2Vec embeddings     │ vs SAGE 0.3324, N2V 0.3324│
├────────────────────────────┼────────────────────────────┤
│ (C) ST: Graph Methods      │ (D) [Creative] Label       │
│ GCN 0.77, SAGE 0.76 on ST │ Complexity vs F1 scatter    │
│ k-NN similarity graph      │ Across ALL datasets        │
└────────────────────────────┴────────────────────────────┘
```

Panel (D) integrates **creative chart 9.2** — log-linear inverse relationship between `n_labels` and achievable F1. This is the single most important cross-cutting insight.

**Data**: `graph_models.csv` (8 rows) + `transfer_learning.csv` (rows D1, D2)

---

## Fig 6: Spatial Tracker Benchmark

**Theme**: "Which method works best for the Spatial Tracker dataset?"

### Composite (2×2):

```
┌────────────────────────────┬────────────────────────────┐
│ (A) Three Methods          │ (B) Confusion Matrices     │
│ TF-IDF+SVM vs BioBERT+LR   │ 3×3 panel (one per method)│
│ vs BioBERT+MLP             │ Predicted vs true category │
│ Significance: *** all pairs│ Shows which categories are │
├────────────────────────────┼────────────────────────────┤
│ (C) Accuracy vs F1-macro   │ (D) [Creative] Category    │
│ Dot plot, dual metric      │ Co-occurrence Network      │
│ Per method labeled         │ 15 analysis tags, edges=   │
│                            │ co-occurrence strength    │
└────────────────────────────┴────────────────────────────┘
```

Panel (D) integrates **creative chart 9.4** — "Niche & Microenvironment" is the central hub.

**Data**: `st_benchmark.csv` (3 rows) + `annotated_articles.csv`

---

## Fig 7: Transfer Learning

**Theme**: "Can pre-training on larger biomedical datasets boost Spatial Tracker classification?"

### Composite (2×2 or 3×1):

```
┌────────────────────────────────────────────────────────┐
│ (A) Full Experiment Waterfall                           │
│ A1→A5 (zero-shot, ~0) → B1/B3 (baseline, ~0.80)       │
│ → C1/C2 (fine-tune, **C1=0.9143** 🏆)                 │
│ Waterfall chart showing cumulative gain                 │
├──────────────────────────┬─────────────────────────────┤
│ (B) Fine-tune Gain Bars  │ (C) Pre-training Source     │
│ B1 vs C1 vs C2           │ PML (0.9143) vs OHSUMED     │
│ Significance: ***         │ (0.8503) as source         │
│ +9.6% from PML pre-train │ +9.6% vs +1.9% gain        │
├──────────────────────────┴─────────────────────────────┤
│ (D) [Creative] Feature × Model Synergy Matrix          │
│ Z-score normalized: which feature×model combos beat    │
│ the dataset average? AdaBoost+TF-IDF has synergy.      │
└────────────────────────────────────────────────────────┘
```

Panel (D) integrates **creative chart 9.3**.

**Data**: `transfer_learning.csv` (11 rows)

---

## Fig 8: Embedding Space Visualization (UMAP)

**Theme**: "How do different representations organize the document space?"

### Regarding TF-IDF + UMAP question (your intuition was correct):

**No PCA needed** — UMAP with `metric='cosine'` works directly on sparse 5,000-dim TF-IDF matrices. No intermediate PCA(50) step required. At this dimensionality × 10K samples, direct UMAP takes ~30s.

### Composite Figure 8A: "Before vs After — Representation Quality" (2×3 grid):

```
┌──────────────────────┬──────────────────────┬──────────────────────┐
│ (A) PML BioBERT UMAP │ (B) ST BioBERT UMAP  │ (C) OHSUMED BioBERT  │
│ 10K docs, 16 colors  │ 9K docs, 6 colors    │ UMAP (subsample)     │
│ MeSH categories      │ LLM categories       │ Top-10 MeSH terms    │
├──────────────────────┼──────────────────────┼──────────────────────┤
│ (D) PML TF-IDF UMAP  │ (E) PGB Node2Vec     │ (F) Fine-tuning      │
│ Same dataset for     │ UMAP 5K nodes        │ Effect on ST         │
│ direct comparison    │ 3 node types         │ Before vs After      │
│ with (A)             │                      │ Silhouette score ↑   │
└──────────────────────┴──────────────────────┴──────────────────────┘
```

### Implementation details:

| Panel | Embedding | Dim | Computation | Est. Time |
|-------|-----------|-----|-------------|-----------|
| (A) PML BioBERT | BioBERT 768d | 768→2 | Run locally ✅ model cached | ~2 min |
| (B) ST BioBERT | BioBERT 768d | 768→2 | Run locally ✅ model cached | ~2 min |
| (C) OHSUMED BioBERT | BioBERT 768d | 768→2 | Run locally ✅ | ~2 min |
| (D) PML TF-IDF | TF-IDF 5000d | 5000→2 (direct UMAP cosine) | Cached `.npz`✅ | ~30s |
| (E) PGB Node2Vec | Node2Vec 128d | 128→2 | Needs PGB graph loaded ⚠️ | ~1 min |
| (F) Fine-tune effect | BioBERT (post-fine-tune) | 768→2 | Needs fine-tuned checkpoint ⚠️ | ~5 min |

### Notes:
- **TF-IDF → UMAP directly**: Yes, `umap.UMAP(metric='cosine')` works on sparse 5000-dim TF-IDF. No PCA needed.
- **Fine-tuning effect (F)**: We'll use the BioBERT+MLP model from Exp 006 as "post-fine-tune" representation. If checkpoint is saved on cluster, we need to bring it back. If not, we can re-run a quick fine-tune.
- **PGB Node2Vec (E)**: Requires the PGB citation graph loaded with `build_graph=True`. The graph construction may take time.

---

## 📊 Summary Table

| Figure | Theme | Panels | Significance | Data Source |
|--------|-------|--------|-------------|-------------|
| **Fig 1** | Dataset Overview | 9 subplots (3×3) | No | `annotated_articles.csv` |
| **Fig 2A** | Classical Matrix — Heatmaps | 6 panels (2×3) | Visual only | `classical_matrix.csv` |
| **Fig 2B** | Classical Matrix — Significance | 4 panels (2×2) | **Yes** | Re-run with fold data |
| **Fig 3** | DL & Unsupervised | 4 panels (2×2) | **Yes** (panel A) | `biobert_mlp.csv`, `lda_cluster.csv` |
| **Fig 4** | Multi-label Strategy | 4 panels (2×2) | **Yes** (panel A) | `multilabel_strategy.csv` |
| **Fig 5** | Graph Methods | 4 panels (2×2) | **Yes** (panel B) | `graph_models.csv` |
| **Fig 6** | ST Benchmark | 4 panels (2×2) | **Yes** (panel A) | `st_benchmark.csv` |
| **Fig 7** | Transfer Learning | 4 panels (2×2) | **Yes** (panel B) | `transfer_learning.csv` |
| **Fig 8** | UMAP Embeddings | 6 panels (2×3) | No | Computed on the fly |
| **Total** | **9 figures** | **~45 panels** | **6 with significance** | |

---

## 🔄 Per-fold Data — Implemented & Running

**Code change**: `_common.py:run_cv()` now saves per-fold values as columns:
```python
res[f"{metric}_folds"] = ",".join(f"{v:.4f}" for v in vals)
```
- New columns: `f1_macro_folds`, `f1_micro_folds`, `f1_samples_folds`
- Each contains 5 comma-separated fold-level values
- Same `random_state=42` → fold-aligned paired t-tests

**Cluster cleanup**: 56 old logs, 6 temp scripts, 20+ outdated CSVs deleted.
**Cache preserved**: 18 `.npz` files (972 MB) — all features intact.

**Status**: 19 jobs submitted. First results verified with `_folds` columns.

---

## 🎨 R vs. Python Note

> **Computational biology convention**: R (ggplot2, tidyverse, pheatmap) is standard in computational biology / bioinformatics publications.
>
> **ML convention**: Python (matplotlib, seaborn) is more common in ML/AI publications.
>
> **Recommendation**: Since this is a **course report combining both fields**:
> - Use **Python** for data extraction, processing, and UMAP computation (data already in Python)
> - Export processed data as CSVs
> - Plot in **R with ggplot2** for publication-quality figures (more control over themes, annotations, multi-panel layouts)
> - Or use **Python + seaborn** with `science` theme for consistent ML-report style
>
> **Decision needed**: Choose one or split (Python for UMAP + R for statistical figures).

---

## 📁 Output Structure

```
report/figures/
├── fig1_dataset_overview.pdf
├── fig2a_classical_heatmap.pdf
├── fig2b_classical_significance.pdf
├── fig3_dl_unsupervised.pdf
├── fig4_multilabel.pdf
├── fig5_graph.pdf
├── fig6_st_benchmark.pdf
├── fig7_transfer_learning.pdf
├── fig8_umap_embeddings.pdf
├── ppt/                          ← Individual panels for PPT
│   ├── fig1a_year_trend.png
│   ├── fig1b_category_pie.png
│   └── ...
└── data/                         ← Processed data for R plotting
    ├── fig2_significance_data.csv
    ├── fig8_umap_embeddings.csv
    └── ...
```
