# Visualization Plan — PubMed Spatial Tracker Report

> Created: 2026-06-05
> All charts in **English** with statistical significance testing (asterisk annotation) on model performance figures.

---

## Part 1: Annotation & Data Overview (from `data/spatial_tracker/annotated_articles.csv`)

| # | Chart | Type | Description |
|---|-------|------|-------------|
| 1.1 | **Publication Year Trend** | Line + area chart | Number of spatial transcriptomics publications per year (2016–2026) showing exponential growth |
| 1.2 | **Category Distribution** | Horizontal bar + pie | 6 categories (Research, Technology, Review, Protocol, Data Resource, Benchmark) |
| 1.3 | **Analysis Tag Distribution** | Horizontal bar (sorted) | 15 analysis tags with counts (Niche & Microenvironment #1, Cell-Cell Communication #2, ...) |
| 1.4 | **Tags per Article** | Histogram | Distribution of how many tags per article (1–4), showing ~24% of articles have 2 tags |
| 1.5 | **Category × Tag Heatmap** | Heatmap | Cross-tabulation: rows = category, columns = tag, color = count (normalized by row) |
| 1.6 | **Technology Platform Bar** | Horizontal bar | Top technologies mentioned (Visium, MERFISH, Slide-seq, Xenium, Stereo-seq, etc.) |
| 1.7 | **Biological Topic Bar** | Horizontal bar | Top biological topics (Cancer, Neuroscience, Immunology, Developmental Biology, etc.) |
| 1.8 | **Annotation Confidence** | Donut chart | high / medium / low distribution |
| 1.9 | **Boolean Flags** | Stacked bar | has_new_data, has_code, is_preprint |
| 1.10 | **Year × Category Stacked Area** | Stacked area | Category composition over time |

**Data source**: `data/spatial_tracker/annotated_articles.csv` (9,147 rows, 13 columns)
**No significance needed** — these are descriptive statistics.

---

## Part 2: Classical Algorithm Matrix — Exp 001 (The Big One)

This is the centerpiece experiment: **7 models × 4 features × 3 datasets = 84 combinations**.

### Core Performance Charts

| # | Chart | Type | Subplots | Key Columns |
|---|-------|------|----------|-------------|
| 2.1 | **Overall Heatmap: Model × Feature** | Heatmap (annotated) | 3 facets (one per dataset) | `f1_macro` |
| 2.2 | **Top-5 per Dataset** | Grouped bar with significance | 3 panels | `f1_macro`, `f1_macro_std` |
| 2.3 | **Feature Effectiveness per Dataset** | Grouped bar with error bars | 3 groups (OHSUMED/PML/PGB) | Best model per feature × dataset |
| 2.4 | **Model Ranking Consistency** | Parallel coordinates | One line per model across 3 datasets | `f1_macro` rank |
| 2.5 | **Performance vs. Training Time** | Scatter plot | Color = feature, shape = dataset | `f1_macro` vs `train_time_s` (log scale) |

### Statistical Significance Protocol

For each bar chart comparing models:
1. Use **paired or unpaired t-test** (depending on whether same CV folds) between the best performer and each competitor
2. Annotate: `*` p<0.05, `**` p<0.01, `***` p<0.001, `ns` not significant
3. Error bars show ±1 std from `f1_macro_std`
4. Since we have 5-fold CV results stored as `f1_macro_std`, we can reconstruct per-fold vectors for proper paired tests

### OHSUMED Deep Dive

| # | Chart | Type | Description |
|---|-------|------|-------------|
| 2.6 | **OHSUMED Label Recovery** | Line plot | F1 vs label frequency percentile — do models perform better on frequent MeSH terms? |
| 2.7 | **OHSUMED: Per-Feature Performance** | Radar chart | 4 features across 7 models (radar axis = model) |

### Missing Value Handling

PGB rows have NA in `f1_micro` and `f1_samples` columns (multi-class, not multi-label). These should be:
- **Heatmaps**: Use `f1_macro` (available for all 84 rows)
- **Bar charts**: Only include rows with complete data for the metric shown
- **Note in caption**: "PGB is multi-class (3 labels), so micro/samples F1 are equivalent to accuracy and omitted"

**Data source**: `experiments/001_classical_matrix/results/classical_matrix.csv` (84 rows)

---

## Part 3: Deep Learning & Unsupervised — Exp 002, 003

| # | Chart | Type | Description |
|---|-------|------|-------------|
| 3.1 | **BioBERT+MLP vs. Best Classical** | Grouped bar with significance | Per dataset: BioBERT+MLP vs. best classical model (from Exp 001) |
| 3.2 | **LDA Clustering Quality** | Bar chart (NMI) | 3 datasets, colored by dataset |
| 3.3 | **Unsupervised ↔ Supervised Gap** | Paired bar | NMI vs. best supervised F1 per dataset (different scales — dual axis) |
| 3.4 | **BioBERT+MLP Training Curves** | Line (loss/epoch) | If logged during training |

### Note on OHSUMED BioBERT+MLP
OHSUMED F1-macro = 0.0013 (essentially random for 1,650 labels). This is expected and should be explicitly discussed.

**Data sources**:
- `experiments/002_biobert_mlp/results/biobert_mlp.csv` (3 rows)
- `experiments/003_lda_cluster/results/lda_cluster.csv` (6 rows — note: 2 duplicate rows per dataset, likely from 2 random seeds)

---

## Part 4: Multi-label Strategy — Exp 004

| # | Chart | Type | Description |
|---|-------|------|-------------|
| 4.1 | **BR vs. CC vs. LP** | Grouped bar with significance | PML only (OHSUMED F1 < 0.01, add as small inset) |
| 4.2 | **Strategy × Time Cost** | Bar + line combo | F1-macro (bar) + train_time_s (line overlay) |
| 4.3 | **OHSUMED Strategy Comparison** | Zoomed bar | OHSUMED results (all near 0, but differences exist) |

**Data source**: `experiments/004_multilabel_strategy/results/multilabel_strategy.csv` (6 rows)

---

## Part 5: Graph Models — Exp 005

| # | Chart | Type | Description |
|---|-------|------|-------------|
| 5.1 | **Node2Vec + 6 Classifiers** | Bar chart | k-NN, SVM, LR, RF, AdaBoost, XGBoost on Node2Vec embeddings |
| 5.2 | **Graph Method Comparison** | Bar chart with significance | GCN vs. GraphSAGE vs. Node2Vec+best classifier |
| 5.3 | **GCN Performance Breakdown** | Confusion matrix | PGB 3-class confusion (if available) |

### Key Message
GCN (0.4125) >> Node2Vec (0.3324) ≈ GraphSAGE (0.3324). Graph convolution captures structure better than random-walk embeddings on this dataset.

**Data source**: `experiments/005_graph_models/results/graph_models.csv` (8 rows)

---

## Part 6: ST Benchmark — Exp 006

| # | Chart | Type | Description |
|---|-------|------|-------------|
| 6.1 | **Three Methods Comparison** | Bar chart with significance stars | TF-IDF+SVM (0.6365) vs. BioBERT+LR (0.8068) vs. **BioBERT+MLP (0.8444)** |
| 6.2 | **Accuracy vs. F1-macro** | Dot plot | Dual metric view per method |
| 6.3 | **Training Time vs. Performance** | Scatter | F1-macro vs. train_time_s, labeled by method |

### Significance Testing
- BioBERT+MLP vs BioBERT+LR: paired t-test on 5-fold F1 values
- Both BioBERT methods vs TF-IDF+SVM: clearly significant (no std overlap)

**Data source**: `experiments/006_st_benchmark/results/st_benchmark.csv` (3 rows)

---

## Part 7: Transfer Learning — Exp 007

| # | Chart | Type | Description |
|---|-------|------|-------------|
| 7.1 | **Fine-tuning Gain Overview** | Bar chart with significance | B1 (ST→ST LR, 0.8157) vs. C1 (PML→ST MLP, **0.9143**) vs. C2 (OHSUMED→ST MLP, 0.8503) |
| 7.2 | **Zero-shot Results** | Bar (low scale) | A1–A5: all near 0, with annotation "expected — label space mismatch" |
| 7.3 | **Graph Methods on ST** | Bar | D1 (GCN, 0.7716) vs. D2 (GraphSAGE, 0.7603) vs. B1 baseline |
| 7.4 | **Pre-training Source Comparison** | Bar | PML (0.9143) vs. OHSUMED (0.8503) as pre-training source |
| 7.5 | **Full Experiment Waterfall** | Waterfall chart | Progression from zero-shot → baseline → fine-tuning → best result |

### Key Story
PML pre-training + ST fine-tuning achieves **F1=0.9143**, a **+9.6% improvement** over direct training (0.8345). This is the single most important result of the project.

**Data source**: `experiments/007_transfer_learning/results/transfer_learning.csv` (11 rows)

---

## Part 8: UMAP Embedding Visualization (Highlight Feature)

### Which Embeddings Can Be Visualized

| Embedding | Dataset | Dim | Status | Cache Available? | Notes |
|-----------|---------|-----|--------|------------------|-------|
| **BioBERT** | PML | 768 | Can compute locally ✅ | Model cached at `~/.cache/huggingface/` | 10K docs, ~1–2 min compute |
| **BioBERT** | ST | 768 | Can compute locally ✅ | Model cached | 9,147 docs |
| **BioBERT** | OHSUMED | 768 | Can compute locally ✅ | Model cached | 10K docs |
| **BioBERT** | PGB | 768 | Can compute locally ✅ | Model cached | 5K docs |
| **TF-IDF** | All | 5,000 | Cached ✅ | `.npz` files exist | Need PCA first (5K → 50) then UMAP |
| **LDA** | All | 15 | Cached ✅ | `.npz` files exist | Already low-dim, direct UMAP |
| **Node2Vec** | PGB | 128 | Needs PGB graph | Requires `build_graph=True` | PGB loader needed |

### Proposed UMAP Charts

| # | Chart | Description | Data | Computation |
|---|-------|-------------|------|-------------|
| 8.1 | **PML BioBERT UMAP** | 10K docs, colored by 16 MeSH categories | BioBERT(768) → UMAP(2D) | ~2 min local |
| 8.2 | **ST BioBERT UMAP** | 9,147 docs, colored by 6 categories | BioBERT(768) → UMAP(2D) | ~2 min local |
| 8.3 | **OHSUMED BioBERT UMAP (subsample)** | 10K docs, colored by top-10 MeSH terms | BioBERT(768) → UMAP(2D) | ~2 min local |
| 8.4 | **PGB Node2Vec UMAP** | 5K nodes, colored by 3 node types | Node2Vec(128) → UMAP(2D) | Needs PGB graph loaded |
| 8.5 | **Fine-tuning Effect — Side by Side** | ST BioBERT BEFORE vs AFTER fine-tuning | Two UMAP panels | Requires fine-tuned model |
| 8.6 | **TF-IDF → BioBERT Comparison** | Same dataset (PML), two feature spaces | 2-panel UMAP | TF-IDF → PCA(50) → UMAP |
| 8.7 | **Cross-Dataset Embedding Alignment** | BioBERT UMAP of all 4 datasets combined | Single UMAP, colored by dataset | Combined embedding |

### Fine-tuning Effect Visualization (8.5)

This is a **high-impact visualization** concept:
1. Take the ST BioBERT embeddings **before** fine-tuning (raw BioBERT)
2. Take the ST BioBERT embeddings **after** fine-tuning (from the Exp 007 C1 model)
3. UMAP both to 2D, side-by-side
4. **Show**: After fine-tuning, same-category documents cluster more tightly
5. **Metric**: Silhouette score before vs. after fine-tuning

**Implementation**: Requires running BioBERT on ST before and after fine-tuning, which means we need a fine-tuned model checkpoint. If not saved, we can use the BioBERT+MLP model from Exp 006 as the "fine-tuned" version.

### UMAP Configuration
- `n_neighbors=30` (balance local/global)
- `min_dist=0.3` (moderate spread)
- `metric='cosine'` (appropriate for high-dim text embeddings)
- Random state fixed for reproducibility
- Legend outside plot to avoid occlusion

---

## Part 9: Creative / Innovative Charts (Your Choice)

| # | Chart | Type | Description | Innovativeness |
|---|-------|------|-------------|----------------|
| 9.1 | **Cost-Benefit Pareto Frontier** | Scatter + Pareto curve | F1-macro vs. training time across ALL experiments, with Pareto-optimal frontier. Shows BioBERT+LR is near-optimal (high F1, low time) | ⭐⭐⭐ High |
| 9.2 | **Label Complexity vs. Performance** | Scatter + regression | X-axis: log(n_labels), Y-axis: best F1 per (dataset, feature). Clear inverse trend — the single most important factor | ⭐⭐⭐ High |
| 9.3 | **Feature × Model Synergy Matrix** | Heatmap grid | 4×7 grid showing which feature-model combos beat dataset average (z-score normalized) | ⭐⭐⭐ High |
| 9.4 | **Category Co-occurrence Network** | Network graph | Nodes = 15 analysis tags, edges = co-occurrence strength, node size = frequency | ⭐⭐ Medium |
| 9.5 | **Model Robustness** | Box plot | Distribution of F1 across features per model — which models are most robust to feature choice? | ⭐⭐ Medium |
| 9.6 | **Cross-Dataset Rank Correlation** | Heatmap | Spearman rank correlation of model performance across dataset pairs | ⭐⭐ Medium |
| 9.7 | **Technology Adoption Timeline** | Bubble chart | X=year, Y=technology, size=count, showing Visium dominance and MERFISH/Xenium rise | ⭐⭐ Medium |
| 9.8 | **Overall Summary Dashboard** | Composite | Single figure with: (a) best F1 per dataset bar, (b) feature ranking, (c) time cost, (d) transfer gain | ⭐ High |

### Recommended Top Picks

1. **Cost-Benefit Pareto Frontier (9.1)** — Shows BioBERT+LR as the "sweet spot" (high F1, low time), while BioBERT+MLP gives best F1 at higher cost. This is the kind of insight practitioners actually need.

2. **Label Complexity vs. Performance (9.2)** — The log-linear inverse relationship between number of labels and achievable F1 is a fundamental finding. OHSUMED (1,650 labels) caps at F1≈0.17 regardless of model sophistication.

3. **Feature × Model Synergy Matrix (9.3)** — Reveals which feature-model combinations are >1σ above average. For example, AdaBoost uniquely benefits from TF-IDF (synergy) while Logistic Regression works well with BioBERT.

4. **Category Co-occurrence Network (9.4)** — Visualizes that "Niche & Microenvironment" and "Cell-Cell Communication" are the most central tags, while "3D Reconstruction" and "Spatial Data Simulation" are peripheral.

---

## Summary Table: All Figures

| Section | # Figures | Significance? | Data Source |
|---------|-----------|---------------|-------------|
| Part 1: Annotation Overview | 10 | No | `annotated_articles.csv` |
| Part 2: Classical Matrix | 7 | Yes (2.2, 2.3, 2.4) | `classical_matrix.csv` |
| Part 3: DL & Unsupervised | 4 | Yes (3.1) | `biobert_mlp.csv`, `lda_cluster.csv` |
| Part 4: Multi-label Strategy | 3 | Yes (4.1) | `multilabel_strategy.csv` |
| Part 5: Graph Models | 3 | Yes (5.2) | `graph_models.csv` |
| Part 6: ST Benchmark | 3 | Yes (6.1) | `st_benchmark.csv` |
| Part 7: Transfer Learning | 5 | Yes (7.1) | `transfer_learning.csv` |
| Part 8: UMAP Embeddings | 7 | No (visual) | Computed on the fly |
| Part 9: Creative Charts | 4–8 | No (except 9.5) | Combined CSVs |
| **Total** | **~46–52** | **~8 with stars** | — |

---

## Implementation Roadmap

### Phase 1: Low-hanging fruit (annotation stats + Exp 006, 007)
- Charts 1.1–1.10, 6.1–6.3, 7.1–7.5

### Phase 2: Core experiment (Exp 001)
- Charts 2.1–2.7 (the most work — 84-row heatmap + significance tests)

### Phase 3: Supporting experiments
- Charts 3.1–3.4, 4.1–4.3, 5.1–5.3

### Phase 4: UMAP embeddings
- Charts 8.1–8.7 (compute BioBERT embeddings, run UMAP)

### Phase 5: Creative charts
- Charts 9.1–9.8 (pick top 4 from recommendation)

### Technical Stack
- **Python**: `matplotlib` + `seaborn` (publication quality)
- **Statistical tests**: `scipy.stats` (ttest_rel / ttest_ind)
- **UMAP**: `umap-learn` package
- **Color scheme**: `viridis` or `colorblind` friendly palette
- **Format**: All figures saved as both PDF (for LaTeX) and PNG (for preview)
- **Output dir**: `report/figures/`

---

## Appendix: Why We Can't Use `f1_samples` for PGB

PGB is a **multi-class** (not multi-label) dataset with 3 classes. For multi-class:
- `f1_macro`: ✅ Available, meaningful (unweighted average per class)
- `f1_micro`: ✅ Available, equals accuracy
- `f1_samples`: ❌ Not defined (requires multi-label with per-sample label sets)

The CSV shows empty `f1_samples` for PGB rows. This is correct behavior — all such charts should use `f1_macro` for cross-dataset consistency.
