# PLAN.md — PubMed Spatial Tracker 彻底重构计划

> 创建: 2026-05-20 | 最后更新: 2026-06-04
>
> 基于以下材料的综合分析：
> - OHSUMED（TREC-9 Filtering Track 基准，~294K 篇，14,466 个 MeSH 标签）
> - PubMed-MultiLabel（Kaggle 数据集，10K/50K 篇，15 个 MeSH 顶级类别标签）
> - PGB（PubMed Graph Benchmark，~30M 篇，5 节点类型 + MeSH 层级结构）
> - Biomed-Enriched（两阶段大语言模型标注管线论文，2506.20331v1）
> - 课程 proposal（机器学习概论大作业框架）

---

## 项目进度总览

| 阶段 | 状态 | 完成内容 |
|---|---|---|
| 0️⃣ **Phase 0: 数据基础设施** | ✅ **已完成** | 4 数据集加载器、5 种文本表示、Node2Vec、Meta 特征、评估框架 |
| 🔬 **Exp 000: PubMed 查询分析** | ✅ **已完成** | 7 种查询变体比较，选定最终检索式（9,148 篇） |
| 📡 **PubMed 数据抓取** | ✅ **已完成** | `data/spatial_tracker/articles.csv`（9,148 篇） |
| 🏷️ **Step 2a: LLM 标签体系设计** | ✅ **已完成** | 6 类别 × 15 分析标签 × 19 技术 × 17 生物领域 |
| 🏷️ **Step 2b: LLM 批量标注** | ✅ **已完成** | 9,148 篇全部标注完成（DeepSeek-v4-flash） |
| 📊 **Step 2续: 标注统计分析** | ✅ **已完成** | 标签分布、类别统计、置信度报告 → `report/annotation_stats.md` |
| 📝 **Step 2续: 人工抽检设计** | ✅ **已完成** | 200 篇分层抽样 + Cohen's κ 模板 → `report/review_template.csv` |
| 🧪 **Exp 001: 经典算法矩阵** | ✅ **82/84 完成** | 🔄 Job 228590 补跑最后 2 组（ohsumed+biobert+ada+xgb） |
| 🧪 **Exp 002: BioBERT+MLP 微调** | ✅ **已完成** | OHSUMED(F1=0.0013), PML(F1=0.6411), PGB(F1=0.3601) |
| 🧪 **Exp 003: LDA+聚类** | ✅ **已完成** | OHSUMED NMI=0.44, PML NMI=0.10, PGB NMI=0.005 |
| 🧪 **Exp 004: 多标签策略** | ✅ **已完成** | BR/CC/LP 对比，CC on PML F1=0.5796 🏆 |
| 🧪 **Exp 005: 图模型** | ✅ **8/9 完成** | GCN(0.4125🏆) >> Node2Vec(0.3324) ≈ GraphSAGE(0.3324) |
| 🧪 **Exp 006: ST 基准测试** | ✅ **已完成** | BioBERT+MLP(0.8444🏆) > BioBERT+LR(0.8068) > TF-IDF+SVM(0.6365) |
| 🔀 **Step 3: 迁移微调探索** | ⬜ **未开始** | 3 种算法的微调实验 |

---

## 核心理念

**从"脚本拼凑的科研工具"彻底转向"以系统化实验驱动的方法选择"。**

不再满足于仅有一套适用于空间转录组的管线，而是将**多数据集 × 多算法 × 多表示**的系统比较作为核心产出，从中选出最优方法，再与当前 BioBERT 基线对比，并探索迁移学习/微调策略。

---

## 四大数据集全景

| 数据集 | 规模 | 标签类型 | 标签数 | 特点 | 角色 |
|---|---|---|---|---|---|
| **OHSUMED** | ~294K 篇 | MeSH 词多标签 | 14,466 | 经典基准（1987-1991），大规模，含 MeSH 词 | 传统方法的可复现验证平台 |
| **PubMed-MultiLabel** | 10K（原始）/ 50K（处理后） | MeSH 顶级类别多标签 | 15 个 | 现代数据集，标签稀疏但精确（A-Z 大类） | 粗粒度类别分类的快速实验平台 |
| **PGB** | ~3M/分片 × 10 | MeSH 标签 + 节点类别 | 3 类（节点分类）/ 21 SR 任务 | **异构图结构**（5 节点 / 7 边类型）+ **MeSH 层级树** | 图表示学习方法验证 + MeSH 层级利用 |
| **Spatial Tracker** | 9,148 篇（已爬取） | 6 类别 + 15 分析标签 + 19 技术（LLM 标注中） | 6+15+19 | **目标领域**，已从 PubMed 全量爬取 | 最终应用场景 + LLM 批量标注验证 |

### 数据集信息维度对比

```
                   OHSUMED    PubMed-MultiLabel    PGB         Spatial Tracker
标题+摘要           ✓          ✓                    ✓            ✓
MeSH 词             ✓          ✓                    ✓（含层级）  ✓
引用网络            ✗          ✗                    ✓            ✗
作者信息            ✗          ✗                    ✓            ✗
期刊/发表类型       ✓          ✗                    ✓            ✓
图表征              ✗          ✗                    ✓            ✗
空间转录组专用标签  ✗          ✗                    ✗            ✓
标注状态            全量标注    全量标注              全量标注      LLM 批量标注（完成）
```

### 关键洞察

1. **OHSUMED** 标签空间极稀疏（14,466 个 MeSH 词，幂律分布），最适合测试**多标签分类**的扩展能力
2. **PubMed-MultiLabel** 仅 15 个粗粒度标签，但数据干净、规模适中，适合**快速算法筛选**
3. **PGB** 的独特价值在于**图结构和 MeSH 层级**——这两种信息在其他数据集中不存在，可以用来探索图神经网络和图嵌入方法
4. **PGB 中有空间转录组学相关文献**（100K 样本中约 2.3%），可用于构建 PGB→Spatial Tracker 的**迁移学习基线**

---

## 算法全景（12 种，不含大语言模型）

按课程模块和新增维度组织：

| 课程模块 | 算法 | 子任务适用 | 数据集适用 |
|---|---|---|---|
| 贝叶斯学习 | Naive Bayes | 类别分类 | 全部 |
| 基于实例的学习 | k-NN | 类别分类 | 全部 |
| 回归学习 | Logistic Regression | 类别分类 | 全部 |
| 最大间隔方法 | SVM (RBF kernel) | 类别、标签分类 | 全部 |
| 集成学习（Bagging） | Random Forest | 类别、标签分类 | 全部 |
| 集成学习（Boosting） | AdaBoost | 类别、标签分类 | 全部 |
| 集成学习（Boosting） | XGBoost | 类别、标签分类 | 全部 |
| 深度学习 | BioBERT + MLP 微调 | 类别分类 | 全部 |
| 无监督学习 | LDA + 聚类可视化 | 文献子领域发现 | 全部 |
| **图嵌入（新增）** | **node2vec** | **节点分类** | **PGB** |
| **图神经网络（新增）** | **GCN** | **节点分类** | **PGB** |
| **图神经网络（新增）** | **GraphSAGE** | **节点分类** | **PGB** |

> **图方法的引入理由**：PGB 论文明确指出 PubMed 文献可以建模为异构图（Paper, Author, MeSH Term, Venue, Publication Type），而传统的 GNN 和异质 GNN 在该数据集上表现不佳——这正是一个值得探索的开放问题。我们从简单的同构图方法（node2vec, GCN, GraphSAGE）入手。DeepSeek 等生成式模型不用于分类测试，而是作为批量标注工具使用。

---

## 文本表示方案

采用 4 种互补的文本表示方法，从不同粒度捕捉文献语义：

| 表示方法 | 维度 | 适用算法 | 设计理由 |
|---|---|---|---|
| TF-IDF (1-2 gram, max=5,000) | 5,000 | NB, k-NN, SVM, LR, RF, Ada, XGB | **词级稀疏基线**：可解释强，衡量传统词袋方法的上限 |
| BioBERT embedding (mean pooling) | 768 | SVM, RF, XGB, GCN* | **上下文语义**：预训练生物医学语言模型，捕捉医学术语关系 |
| LDA 主题分布 (K=15) | 15 | NB, k-NN, SVM | **文档级主题**：无监督发现隐式主题结构 |
| 元特征（年份、文本长度、MeSH 数等） | 3–5 | 拼接至以上向量 | **非文本信号**：OHSUMED(3d)/PML(3d)/PGB(3d)/ST(5d)，z-score 归一化 |
| Node2Vec 图嵌入（仅 PGB） | 128 | k-NN, SVM, GCN, GraphSAGE | **引用图结构**：有偏随机游走捕捉文献引用网络拓扑 |

> 多种表示对比可揭示：**语义深度**（TF-IDF→BioBERT）、**结构粒度**（词级→文档级→图级）和**信息类型**（文本→非文本→结构）对分类性能的贡献。

---

## 实验阶段设计：三步渐进

```
┌──────────────────────────────────────────────────────────────────────┐
│ Step 1: 多数据集算法筛选（三个全标注数据集）                          │
│                                                                      │
│  OHSUMED ──→ TF-IDF/BioBERT/LDA ──→ 10种课程算法 ──→ 最优方法 Top-3 │
│  (14K标签)    + Meta Features        (NB/k-NN/SVM/LR/RF/            │
│                                      Ada/XGB/LGB/BioBERT/LDA)       │
│  PubMed-ML ─→ TF-IDF/BioBERT/LDA ──→ 10种课程算法 ──→ 最优方法 Top-3 │
│  (15标签)      + Meta Features                                       │
│                                                                      │
│  PGB ───────→ TF-IDF/BioBERT/LDA ──→ 10种课程算法 ──→ 最优方法 Top-3 │
│  (图+MeSH层级)  + Meta + Node2Vec     + node2vec/GCN/GraphSAGE       │
│                                                                      │
│  → 产出：算法×数据集热力图、特征有效性排序、图结构边际收益量化         │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Step 2: 目标数据集构建与应用                                          │
│                                                                      │
│  PubMed检索 ──→ 空间转录组学文献库 ──→ DeepSeek API 批量标注          │
│  (查询实验 001)   (9,148篇已爬取)        (6维标签体系)               │
│                                              │                       │
│                                              ▼                       │
│  Step 1 最优方法 ──→ 在 ST 上训练/测试 ──→ vs BioBERT+MLP 基线       │
│  (Top-3 × 3来源)        (LLM标注版)          (对比F1/速度/可扩展性)   │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Step 3: 迁移微调探索                                                  │
│                                                                      │
│  宽泛预训练         空间转录组微调       最终测试                      │
│  ──────────→        ──────────→        ──────────→                   │
│  OHSUMED/PGB      Spatial Tracker     Spatial Tracker                │
│  (BioBERT/XGB/     (增量训练)          (对比微调前后F1)              │
│   GCN/GraphSAGE)                                                     │
│                                                                      │
│  → 产出："宽泛预训练+领域微调"范式的增益量化                         │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 已完成工作详情

### Phase 0: 数据基础设施（2026-05-20 完成）

统一的 `BiomedDataset` 接口和完整的 `src/` 模块化结构。

**数据集加载器**：全部实现统一接口 `BiomedDataset`（`texts()`, `labels()`, `pmids()`, `metadata()`）

| 加载器 | 文件 | 支持 |
|---|---|---|
| `OHSUMEDLoader` | `src/datasets/ohsumed.py` | TREC 格式解析，稀疏 MeSH 多标签（过滤低频词） |
| `PubMedMultiLabelLoader` | `src/datasets/pubmed_multilabel.py` | CSV 读取，原始 15 类 / Processed 版本 |
| `PGBLoader` | `src/datasets/pgb.py` | JSONL 读取，可选图构建（邻接表） |
| `SpatialTrackerLoader` | `src/datasets/spatial_tracker.py` | 读取 `articles.csv` / `annotated_articles.csv` |

**文本表示**：4 种互补的文本表示方法

| 表示 | 维度 | 文件 |
|---|---|---|
| TF-IDF (1-2 gram) | 5,000 | `src/features/tfidf.py` |
| BioBERT embedding (mean pooling) | 768 | `src/features/biobert.py`（`dmis-lab/biobert-v1.1`） |
| LDA 主题分布 | 15 | `src/features/lda_features.py` |
| 元特征 | ~10 | `src/features/metadata.py` |

**模型实现**：共 12 种算法

| 模块 | 文件 | 算法 |
|---|---|---|
| 经典机器学习 | `src/models/classical.py` | Naive Bayes, k-NN, SVM (RBF), Logistic Regression |
| 集成学习 | `src/models/ensemble.py` | Random Forest, AdaBoost, XGBoost |
| 深度学习 | `src/models/deep.py` | BioBERT + MLP 微调 |
| 无监督学习 | `src/models/unsupervised.py` | LDA + 聚类 |

**评估框架**：`src/evaluation/metrics.py` + `src/evaluation/report.py`
- 多分类（Accuracy, Macro/Weighted F1, Cohen's κ）
- 多标签（Jaccard 相似度, Hamming Loss, Per-label F1）
- 二分类（AUC-ROC, PR-AUC, F1）
- CSV 实验日志

**实验流水线**：`src/pipeline.py`——`run_experiment()`，带交叉验证和日志记录

### 实验 000: PubMed 查询分析（2026-05-21 完成）

`experiments/001_query_analysis/` 比较了 7 种查询变体：

```
MeSH Major Topic → 9,933 篇    |   MeSH All        → 98,948 篇
text spatial     → 7,412 篇    |   text resolved   → 545 篇
text both        → 7,638 篇    |   Overlap: MeSH & text = 32 篇 (0.18%)
```

最终选定检索式：
```
("Spatial Transcriptomics"[MeSH Major Topic]
 OR "spatial transcriptom*"[Title/Abstract]
 OR "spatially resolved transcriptom*"[Title/Abstract])
AND hasabstract[text] AND english[Language] AND 2016:2026[dp]
```
→ **9,148 篇**

### PubMed 数据抓取（2026-05-21 完成）

`src/search/pubmed_search.py` 实现了稳健的 PubMed 抓取：
- **Biopython Entrez 优先**，自动回退到 urllib
- **CLI 参数**：`--retmax`, `--batch`, `--out`, `--incremental`
- **增量保存**：每隔 N 批次写入 CSV
- **重试与速率限制**：对 NCBI 礼貌
- 输出：`data/spatial_tracker/articles.csv`（9,148 行，~17 MB）

### 标签体系设计（2026-05-21 完成）

参考 Biomed-Enriched（2506.20331v1）的标注方法，设计了 6 维标签体系：

| 维度 | 取值 | 说明 |
|---|---|---|
| `category` | 6 类 | Research, Review, Technology, Data Resource, Benchmark, Protocol |
| `tags` | 15 种 | Spatial Domain Identification, Cell-Type Deconvolution, Cell-Cell Communication, Spatial Integration, 等——**专指数据分析方法** |
| `technology` | 19 种 | Visium, MERFISH, Slide-seq, Xenium, Stereo-seq, CosMx, 等 |
| `biological_topic` | 17 个 | Cancer, Neuroscience, Immunology, Developmental Biology, 等 |
| `has_new_data` / `has_code` / `is_preprint` | bool | — |
| `confidence` | 3 级 | high / medium / low |

### LLM 批量标注（2026-05-22 完成）

`src/annotate/batch_annotate.py`：
- 调用 DeepSeek API（`deepseek-v4-flash`，`https://api.deepseek.com`）
- 精细 System Prompt + User Prompt（参考 Biomed-Enriched 方法）
- JSON 输出解析与验证
- **自动断点续跑**：检测已有输出文件，跳过已标注 PMID
- 增量保存（每 10 篇），支持暂停/恢复
- 全部 **9,148 篇**标注完成

标注分布：
```
Research: 5,333  |  Technology: 1,785  |  Review: 1,308
Protocol: 551    |  Data Resource: 91  |  Benchmark: 79
Confidence: high=4,307  medium=4,439  low=401
Top tags: Niche & Microenvironment (2,987), Cell-Cell Communication (2,137),
           Spatial Domain Identification (1,766)
has_new_data: 5,236 | has_code: 1,127 | is_preprint: 2
```

### Step 1 实验（2026-05-26 更新）

| 实验 | 内容 | 组数 | 状态 |
|---|---|---|---|
| 001 | 经典算法矩阵：7 模型 × 4 特征 × 3 数据集 | 84 | 🔄 超时（4h），需分片重跑 |
| 002 | BioBERT+MLP 端到端微调 × 3 数据集 | 3 | 🔄 GPU 任务就绪（`local_files_only` 已修复） |
| 003 | LDA+KMeans 无监督聚类 × 3 数据集 | 3 | ✅ 已完成 |
| 004 | 多标签策略 BR/CC/LP × 2 数据集 | 6 | ✅ 已完成（CC 死锁修复后重跑中） |
| 005 | 图模型 Node2Vec×7 + GCN + GraphSAGE × PGB | 9 | ✅ 8/9 完成 |
| **006** | ST 基准测试 × Spatial Tracker | **3** | ✅ **全部完成** |

### Exp 006: Spatial Tracker 基准测试 ✅

在 9,148 篇 LLM 标注完成的 Spatial Tracker 数据集上，比较 3 种方法：

| 方法 | F1-macro | Accuracy | 时间 | 特点 |
|---|---|---|---|---|
| TF-IDF + SVM | 0.6365 ± 0.0123 | 0.9167 ± 0.0011 | 913s | 传统基线，无需 GPU |
| BioBERT + LR | 0.8068 ± 0.0320 | 0.9298 ± 0.0035 | **138s** ⚡ | 冻结嵌入，性价比最优 |
| **BioBERT + MLP** | **0.8444** 🏆 ± 0.0353 | **0.9380** ± 0.0124 | 1039s | 端到端微调，最高分 |

**结论**：BioBERT+MLP 是 F1 冠军（0.8444），但 BioBERT+LR 仅差 4.7% 且快 7.5 倍，是最优性价比方案。
| **006** | ST 基准测试（TF-IDF+SVM / BioBERT+LR / BioBERT+MLP）× Spatial Tracker | **3** | ✅ **3 完成** |

**总计：108 组**（原 105 组 + 006 扩展 3 组）。001 支持 `--datasets/--features/--models` 选择性运行。

**预期产出**：
1. 算法 × 数据集 × 特征热力图（001）
2. 端到端微调 vs 冻结嵌入的对比（002 vs 001-biobert+LR）
3. 多标签策略在小/大标签空间下的扩展性（004）
4. 图结构对分类的边际收益（005 vs 001-PGB）
5. 无监督聚类的 NMI/ARI 基线（003）
4. 每数据集推荐算法

### Step 2 续：标注完成后的分析 ✅

- ✅ **统计分析** → `report/annotation_stats.md`（类别/标签/置信度/年份/标签密度分布）
- ✅ **人工抽检模板** → `report/review_template.csv`（200 篇分层抽样，填入人工标注后计算 Cohen's κ）
- ✅ **应用 Step 1 最优方法 vs BioBERT 基线** → Exp 006（TF-IDF+SVM 0.6365, BioBERT+LR 0.8068, BioBERT+MLP **0.8444** 🏆）

### Step 3: 迁移微调探索 ✅ **已规划（待运行）**

**核心问题**：在源域（OHSUMED/PML/PGB）上训练的分类器，能否通过在 Spatial Tracker 上微调获得比直接训练更高的 F1？

#### 与 Step 2 的延续性

| Step 2 产出 | Step 3 利用方式 |
|---|---|
| `annotated_articles.csv` (9,148 篇, 6 类别) | 固定 80/10/10 划分，所有 007 实验共用同一测试集 |
| Exp 006 三方法 F1 基线 (TF-IDF+SVM 0.6365, BioBERT+LR 0.8068, BioBERT+MLP 0.8444) | B 组直接训练基线（对齐 006 评估方式，但使用固定划分而非 5-fold CV） |
| OHSUMED(1,650 标签) / PML(16 标签) / PGB(3 标签) 数据集 | 作为 A 组零样本和 C 组微调的源域 |
| BioBERT 特征缓存 (`_cache/biobert_*.npz`) | 所有 A/B/C 实验共享同一缓存，无需重复提取 |

#### 实验 A: Zero-shot 迁移（5 组）

在源域训练分类器，不做任何 ST 适配，直接在 ST 测试集上评估。**检验源域知识是否可泛化到目标域。**

| 编号 | 源域 | 特征 | 分类器 | 意义 |
|---|---|---|---|---|
| **A1** | OHSUMED | BioBERT 嵌入 | LR | 大规模稀疏标签 → 6 类 |
| **A2** | PML | BioBERT 嵌入 | LR | 粗粒度标签 → 6 类 |
| **A3** | OHSUMED | BioBERT 嵌入 | XGBoost | 同上，非线性分类器 |
| **A4** | PML | BioBERT 嵌入 | XGBoost | 同上 |
| **A5** | PGB | BioBERT 嵌入 | LR | 节点分类 → 6 类 |

#### 实验 B: 直接训练基线（3 组）

在 ST 训练集上标准训练，在 ST 测试集上评估。**作为微调增益的量化基准。**

| 编号 | 方法 | 预期 (参照 Exp 006) |
|---|---|---|
| **B1** | BioBERT + LR (冻结嵌入) | F1 ≈ 0.8068 |
| **B2** | BioBERT + MLP (端到端) | F1 ≈ 0.8444 |
| **B3** | XGBoost on BioBERT 嵌入 | ~0.75-0.80 |

#### 实验 C: 预训练 → 微调 → 测试（4 组）

先在大规模源域上预训练，再在 ST 上微调。**量化迁移学习的具体增益。**

| 编号 | 预训练域 | 算法 | 微调策略 | 预期增益 |
|---|---|---|---|---|
| **C1** | PML | BioBERT+MLP | 加载 BERT 权重，替换分类头，全模型微调 | +1~3% |
| **C2** | OHSUMED | BioBERT+MLP | 同上（OHSUMED 采样 5K 篇加速） | +0~2% |
| **C3** | PML | XGBoost | warm start (`xgb_model` 参数) | +1~2% |
| **C4** | OHSUMED | XGBoost | warm start | +0~1% |

#### 共计：17 组实验（+4 图实验）

#### 实验 D: k-NN 相似图 + GCN/GraphSAGE

基于 BioBERT 嵌入的余弦相似度构建文章的 k-NN 相似图（k=15），在其上训练图模型。

| 编号 | 方法 | k-NN 图 | 训练方式 | 意义 |
|---|---|---|---|---|
| **D1** | GCN | ST | 图直接训练 | 基线：图模型在 ST 上的表现 |
| **D2** | GraphSAGE | ST | 图直接训练（spmm 加速） | 同上 |
| **D3** | GCN | ST | PGB 预训练 → 零样本 | 检验 PGB GCN 权重的跨图泛化能力 |
| **D4** | GCN | ST | PGB 预训练 → 微调 50 epochs | 量化图迁移增益 |

**图构建方法**：
```python
from sklearn.neighbors import NearestNeighbors
nn = NearestNeighbors(n_neighbors=16, metric="cosine")
nn.fit(X_biobert)
distances, indices = nn.kneighbors(X_biobert)
# 对称化双向边
```

**GCN 迁移策略 (D3/D4)**：
- **D3 (零样本)**：PGB 引用图训练 GCN → 加载权重 → ST k-NN 图预测（标签空间 3→6 不匹配，意义有限）
- **D4 (微调)**：PGB 引用图训练 GCN → 加载 conv1 权重，随机初始化 conv2(6类) → ST k-NN 图低学习率微调 50 epochs

**预期**：D1 (GCN from scratch) ~0.75-0.82；D4 若图迁移有效可比 D1 高 1-3%

#### 关键技术实现

**BioBERT+MLP 迁移（C1, C2）**：
```
预训练阶段:
  1. 创建 BioBERTFineTuner(n_labels=源域标签数)
  2. 在源域上训练 2 个 epoch（OHSUMED 采样 5K 篇加速）
  3. 保存 state_dict

微调阶段:
  1. 创建 BioBERTFineTuner(n_labels=6)  -> 随机初始化分类头
  2. 加载预训练的 BERT 权重: model.bert.load_state_dict(bert_weights)
  3. 分类头保持随机（6 类）
  4. 在 ST 上微调 3 个 epoch
```

**XGBoost warm start（C3, C4）**：
```python
# 预训练
src_clf = XGBClassifier(n_estimators=200)
src_clf.fit(X_src, y_src)
src_clf.save_model("xgb_pretrained.json")

# warm start 微调
tgt_clf = XGBClassifier(n_estimators=100)
tgt_clf.fit(X_tr, y_tr, xgb_model="xgb_pretrained.json")
```

#### 与 Step 2 的演进对比

| 维度 | Exp 006 (Step 2) | Exp 007 (Step 3) |
|---|---|---|
| 评估方式 | 5-fold CV | 固定 80/10/10 划分 |
| 评估集 | 每 fold 不同 | **同一测试集** → 实验间严格可比 |
| 方法数 | 3 | 13 |
| 新增能力 | — | 零样本 + 迁移微调 |
| GPU 需求 | BioBERT+MLP | BioBERT+MLP + C1/C2 预训练+微调 |
| 预期最佳 | BioBERT+MLP 0.8444 | C1 (PML→ST MLP) ~0.85-0.87 |

---

## 项目结构

```
src/
├── config.py              # 实验配置
├── pipeline.py            # 实验调度
├── annotate/              # LLM 批量标注
│   └── batch_annotate.py  # DeepSeek API 标注管线
├── datasets/              # 数据加载器
│   ├── base.py, ohsumed.py, pubmed_multilabel.py
│   ├── pgb.py, spatial_tracker.py
├── features/              # 文本表示
│   ├── tfidf.py, biobert.py, lda_features.py, metadata.py
├── models/                # 算法实现
│   ├── classical.py, ensemble.py, deep.py, unsupervised.py
├── evaluation/            # 评估
│   ├── metrics.py, report.py
├── search/                # PubMed 检索
│   └── pubmed_search.py
data/
├── spatial_tracker/
│   ├── articles.csv             # 9,148 篇（已抓取）
│   └── annotated_articles.csv   # 3,990 篇（标注中）
├── ohsumed/, pgb/, PubMed-MultiLabel/  # 原始数据
experiments/
├── 001_query_analysis/      # 查询变体比较
├── 006_st_benchmark/        # ST 三方法基准
└── 007_transfer_learning/   # 迁移微调探索（Step 3）
publications/               # 参考论文
```

---

## 课程大作业对接说明

### 涵盖的课程模块

| 课程模块 | 对应内容 |
|---|---|
| 贝叶斯学习 | Naive Bayes |
| 基于实例的学习 | k-NN, SVM |
| 回归学习 | Logistic Regression |
| 集成学习 | Random Forest, AdaBoost, XGBoost |
| 深度学习 | BioBERT + MLP 微调 |
| 无监督学习 | LDA + 聚类 |
| 图表示学习 | node2vec, GCN, GraphSAGE |

> **AI 辅助编程使用说明**：本项目中的 AI 辅助编程工具（GitHub Copilot）仅用于：
> 1. 项目架构设计与代码框架搭建
> 2. 代码审查与调试
> 3. 文档编写与维护
> 4. **LLM 仅作为数据标注工具**（DeepSeek API 标注空间转录组学文章标签）
>
> **核心约束**：所有核心算法（分类器、特征提取、评估指标）的实现、实验设计与分析均由人工完成。LLM 标注的数据将作为下游分类算法的训练/测试标签使用，而非替代算法实现。任何 AI 辅助生成的代码片段在最终提交前均需经人工审查和必要重写。

---

## 附录：数据格式

- **OHSUMED**：TREC 格式（`.I .U .S .M .T .P .W .A` 字段），14,466 个 MeSH 标签
- **PubMed-MultiLabel**：CSV，15 个 MeSH 顶级类别二元标签
- **PGB**：JSONL，5 节点类型 + 7 边类型的异构图
- **Spatial Tracker**：CSV（`articles.csv`），含 pmid/title/abstract/pub_year/journal/mesh_terms/keywords
├── models/
│   ├── classical.py         # NB, k-NN, SVM, LR
│   ├── ensemble.py          # RF, AdaBoost, XGBoost
│   ├── deep.py              # BioBERT + MLP
│   ├── graph.py             # node2vec, GCN, GraphSAGE
│   └── unsupervised.py      # LDA + 聚类
├── evaluation/
│   ├── metrics.py           # 统一评估函数
│   └── report.py            # 实验报告生成
├── pipeline.py              # 完整实验流水线
└── config.py                # 实验配置
```

---

## Step 2：LLM 批量标注 + 空间转录组学应用（预计 1-2 周）

### 2.1 数据集构建

**第一步：PubMed 检索与爬取**
- 检索式（经实验 001 验证）：
  ```
  ("Spatial Transcriptomics"[MeSH Major Topic]
   OR "spatial transcriptom*"[Title/Abstract]
   OR "spatially resolved transcriptom*"[Title/Abstract])
  AND hasabstract[text] AND english[Language] AND 2016:2026[dp]
  ```
- 估计规模：约 9,148 篇（含约 1,100 篇 Review）
- 通过 Entrez API 获取标题、摘要、MeSH 词、出版年份、期刊等信息

### 2.2 核心思路

参考 **Biomed-Enriched** 的两阶段标注方法：

1. **第一阶段（LLM 标注）**：使用 **DeepSeek API**（OpenAI 兼容格式，可通过 `openai` Python 库调用，设置 `base_url="https://api.deepseek.com"`）对部分空间转录组文献进行详细标注
2. **第二阶段（模型蒸馏）**：用标注结果训练一个小型分类器（如 BioBERT 或 XLM-RoBERTa），将标注扩展到全部文献

> **DeepSeek API 兼容性**：DeepSeek 的 Chat Completions API 完全遵循 OpenAI 格式，`openai` 库可直接调用。示例：
> ```python
> from openai import OpenAI
> client = OpenAI(api_key="sk-...", base_url="https://api.deepseek.com")
> response = client.chat.completions.create(
>     model="deepseek-reasoner",  # 或 deepseek-chat
>     messages=[...]
> )
> ```
> 推荐使用 `deepseek-reasoner`（R1）进行复杂推理标注，或 `deepseek-chat`（V3/V4）进行高效批量处理。

### 标注格式

为每篇文献生成：

```json
{
  "pmid": "12345678",
  "category": "Research",
  "tags": ["Neuroscience", "Visium", "Clustering"],
  "is_discarded": false,
  "confidence": 0.92,
  "reasoning": "这篇文献介绍了使用 Visium 平台对小鼠大脑...",
  "annotator": "deepseek-reasoner-2026-05-20"
}
```

### 2.4 评估策略

- 手动标注一个适量子集（约 200-500 篇）作为 **gold standard**
- 对比 LLM 标注 vs 人工标注的一致性（Cohen's κ）
- 分析 LLM 在不同类别/标签上的准确率差异
- 用 LLM 标注训练的 ML 模型 vs 用人工标注训练的 ML 模型 → 对比下游性能

### LLM 标注的关键设计

1. **Prompt Engineering**：为每个类别（Review/Technology/Database/Data Analysis/Research）设计不同的 CoT 推理路径；DeepSeek-R1 的推理能力尤其适合此场景
2. **标签约束**：在 prompt 中嵌入 `enforce_category_tag_policy()` 的逻辑
3. **不确定度估计**：要求 LLM 输出置信度分数，低置信度样本保留给人工

---

## Step 1：跨数据集算法筛选（核心实验，预计 2-3 周）

### 1.1 实验矩阵

```
数据集 × 文本表示 × 算法 × 任务 = 实验总数

OHSUMED (1) × TF-IDF/BioBERT/LDA/Meta (4) × 10种算法 = 40  ← 多标签分类
PubMed-ML (1) × TF-IDF/BioBERT/LDA/Meta (4) × 10种算法 = 40  ← 多标签分类
PGB (1) × TF-IDF/BioBERT/node2vec/GCN/GraphSAGE (5) × 3种图方法 + 7种文本方法 = ~20
                                                                              ─────
                                                                   约 100 组实验
```

> 每组实验用 5 折交叉验证，报告均值和标准差。

### 1.2 子实验设计

| 实验编号 | 名称 | 目的 | 方法 |
|---|---|---|---|
| 实验 | 目标 | 预期结论 | 方法 |
|---|---|---|---|---|
| 001 | **经典算法矩阵** | 算法×数据集×特征热力图 | 7 模型 × 4 特征 × 3 数据集，CV=5 |
| 002 | **BioBERT+MLP 微调** | 端到端 vs 冻结嵌入 | BioBERT+MLP × 3 数据集，CV=3 |
| 003 | **LDA+聚类** | 无监督基线 NMI/ARI | LDA+KMeans × 3 数据集 |
| 004 | **多标签策略** | BR/CC/LP 扩展性 | TF-IDF+LR × 3 策略 × 2 数据集 |
| 005 | **图模型**（PGB 特有） | 图结构边际收益 | Node2Vec/GCN/GraphSAGE × PGB |

### 2.3 预期产出

1. **算法 × 数据集 的热力图**：哪个算法在哪个数据集上表现最好
2. **特征有效性排序**：BioBERT vs TF-IDF vs LDA vs 图嵌入的相对提升
3. **数据特性影响分析**：
   - 标签空间大小（14K vs 15）对算法扩展性的影响
   - 图结构信息的边际收益
   - MeSH 层级的价值量化
4. **每数据集推荐算法**

---

## Step 3：迁移学习 / 微调探索（预计 1-2 周）

这是最具有探索性质的阶段，核心问题是：

> **能否用宽泛生物医学数据预训练，再用领域数据微调，实现性能提升？**

### 3.1 迁移实验设计

```
实验 A: 宽泛预训练 → ST 测试
  训练集: OHSUMED 或 PubMed-MultiLabel（全部）
  测试集: Spatial Tracker（LLM 标注版）
  
实验 B: ST 微调 → ST 测试
  训练集: Spatial Tracker（LLM 标注版，训练部分）
  测试集: Spatial Tracker（LLM 标注版，测试部分）

实验 C: 宽泛预训练 → ST 微调 → ST 测试
  步骤 1: 在 OHSUMED 上预训练
  步骤 2: 在 Spatial Tracker 上微调
  步骤 3: 在 Spatial Tracker 测试集上评估
```

### 3.2 适用"微调"概念的算法

并非所有算法都支持微调。以下为候选：

| 算法 | 微调方式 | 可行性 |
|---|---|---|
| **BioBERT + MLP** | 加载预训练权重 → 全领域微调 → 目标领域微调 | ✅ 标准做法 |
| **SVM / Logistic Regression** | 无法增量学习 | ❌ |
| **Random Forest / XGBoost** | 可在预训练模型基础上继续训练（warm start） | ⚠️ 部分支持 |
| **GCN / GraphSAGE** | 在 PGB 上预训练 → ST 图上微调 | ✅ 图迁移学习 |
| **node2vec** | 预训练嵌入 → 在新图上重新训练或对齐 | ⚠️ 需对齐策略 |

因此 Step 3 的重点算法：
1. **BioBERT + MLP**（深度学习微调标准范式）
2. **XGBoost**（集成学习的 warm start 能力）
3. **GCN / GraphSAGE**（图迁移学习的探索）

### 3.3 跨数据集迁移（PGB → ST）

PGB 中包含约 2.3% 的空间转录组学相关文献（基于 100K 样本估算）。
可以：
1. 在 PGB 的整个图上预训练 GCN/GraphSAGE
2. 在 Spatial Tracker 的文献子图上微调
3. 比较：纯 ST 训练 vs PGB 预训练 + ST 微调

### 3.4 预期产出

- "微调增益"量化表：每种算法在微调前后的 F1 变化
- 预训练数据规模 vs 微调增益的关系曲线
- 哪些算法适合 "预训练 + 微调" 范式的系统性结论

---

## 总体时间线

```
周 1:   数据基础设施搭建
        - 三个全标注数据集的统一加载器
        - 评估框架 + 实验追踪
        
周 2-4: Step 1 — 跨数据集算法筛选（核心）
        - 100+ 组实验
        - 特征对比 + 算法全矩阵 + 图方法 + MeSH 层级消融
        - 结果分析与可视化
        
周 5:   PubMed 检索式设计 + 空间转录组学文献爬取
        
周 6-7: Step 2 — LLM 批量标注 + 空间转录组学应用
        - DeepSeek API 标注 + 蒸馏
        - 最优方法 vs BioBERT 基线对比
        
周 8-9: Step 3 — 迁移微调探索
        - 3 种算法的微调实验
        - 跨数据集迁移（PGB → ST）
        - 最终结论

周 10:  报告撰写 + 代码整理
        - 实验报告（课程大作业）
        - README / 文档更新
        - 可复现的 benchmark 包
```

---

## 课程大作业对接

### 涵盖的课程模块

| 课程模块 | 对应内容 |
|---|---|
| 贝叶斯学习 | Naive Bayes |
| 基于实例的学习 | k-NN, SVM |
| 回归学习 | Logistic Regression |
| 集成学习 | Random Forest, AdaBoost, XGBoost |
| 深度学习 | BioBERT + MLP 微调 |
| 无监督学习 | LDA + 聚类 |
| **图表示学习（课程未包含，PGB 启发新增）** | node2vec, GCN, GraphSAGE |

### 与 Proposal 的变化

| 项目 | Proposal 原计划 | 新计划 | 变更理由 |
|---|---|---|---|
| 数据集 | ST + OHSUMED（2 个） | ST + OHSUMED + PubMed-ML + PGB（4 个） | PGB 提供图结构信息，PubMed-ML 提供现代基准 |
| 算法 | 12 种 | 13 种（新增图方法，移除生成式模型作为分类器） | 图方法由 PGB 启发新增；LLM 改为标注工具而非分类器 |
| 主动学习 | 3 种策略对比 | 暂缓 | 先解决基础分类问题，再考虑主动学习 |
| LLM 角色 | GPT-4o 零样本分类 | **DeepSeek API** 批量标注全数据集 | Biomed-Enriched 论文启发；DeepSeek 兼容 OpenAI 格式 |
| 核心产出 | 单一管线的优化 | 多数据集 × 多算法的系统性比较 | 课程作业要求全面覆盖各模块 |

---

## 技术债务处理

从旧项目中需要保留的：

| 保留 | 理由 |
|---|---|
| `web_app/shared.py` 的 `enforce_category_tag_policy()` | 领域知识编码，可迁移至新管线 |
| `tags.json` | 空间转录组学标签本体 |
| `spatial_literature.db` | 原始数据，始终可回退 |
| `AGENTS.md` 的项目上下文 | 文档资产 |

从旧项目中需要弃用的：

| 弃用 | 替代 |
|---|---|
| `migrate_naive.py` | 新管线的规则引擎模块 |
| `ml_pipeline.py` | 新 `src/models/` 下的模块化管线 |
| `ml_report.py` | 新 `src/evaluation/report.py` |
| `main.py` 的爬取逻辑 | 保留但改造为数据采集模块 |

---

## 附录：各数据集详细格式

### OHSUMED 格式

```
.I 54711                    ← 文档 ID
.U                          ← MEDLINE UI
88000001
.S                          ← 来源
Alcohol Alcohol 8801; 22(2):103-12
.M                          ← MeSH 词（多标签）
Acetaldehyde/*ME; Buffers; Catalysis; ...
.T                          ← 标题
The binding of acetaldehyde...
.P                          ← 发表类型
JOURNAL ARTICLE.
.W                          ← 摘要
Ribonuclease A was reacted...
.A                          ← 作者
Mauch TJ; Tuma DJ; Sorrell MF.
```

**标签空间**：14,466 个唯一 MeSH 词，多标签分类任务。

### PubMed-MultiLabel 格式

```
Title, abstractText, meshMajor, pmid, meshid, meshroot, A, B, C, D, E, F, G, H, I, J, K, L, M, N, V, Z
```

- 10,032 篇（原始）/ 50,000 篇（Processed，缺少 K, V 列）
- **15 个二元标签**：MeSH 顶级类别（A=解剖学, B=生物体, C=疾病, D=化学品, ...）
- 标签分布极不均匀：B(93.4%) > E(78.0%) > G(66.7%)，V(0.0%) 无正样本

### PGB 格式（JSONL）

```json
{
  "pmid": "17785526",
  "title": "...",
  "abstract": "...",
  "authors": [{"first": "...", "last": "..."}],
  "year": 2007,
  "venue": "Genes & development",
  "publication_type": ["Journal Article", "Review"],
  "chemicals": ["...", "..."],
  "mesh": [
    {"term": "Animals", "is_major": false, "tree_num": "B01.050"},
    {"term": "DNA-Binding Proteins", "is_major": false, "tree_num": "D12.776.260"}
  ],
  "outbound_citations": ["12756183", "11146626", ...],
  "inbound_citations": [...],
  "has_outbound_citations": true,
  "has_inbound_citations": true
}
```

**5 节点类型**：Paper, Author, MeSH Term, Venue, Publication Type
**7 边类型**：P-P（引用）, P-A（作者）, A-A（合著）, P-M（MeSH）, P-V（期刊）, P-T（发表类型）, M-M（MeSH 层级）
**3 评估任务**：节点分类（3 类糖尿病文献）、节点聚类、系统综述筛查（21 个 SR 任务）

### Spatial Tracker Schema（待构建）

```sql
-- 待设计：爬取后存储标题+摘要+MeSH+元信息
-- LLM 标注后增加 category / tags / is_discarded 等字段
CREATE TABLE literature (
    pmid TEXT PRIMARY KEY,
    title TEXT,
    abstract TEXT,
    mesh_terms TEXT,         -- JSON 数组或分号分隔
    pub_year INTEGER,
    journal TEXT,
    -- 以下由 LLM 标注填充
    category TEXT,           -- 5 类: Review/Technology/Database/Data Analysis/Research
    tags TEXT,               -- 分号分隔的语义标签
    is_discarded INTEGER DEFAULT 0,
    llm_confidence REAL,
    is_manually_confirmed INTEGER DEFAULT 0
);
```

---

## 下一步行动

1. ✅ 阅读并分析所有参考材料（已完成）
2. ⬜ **等待你审核本计划** → 修改细节
3. ⬜ 确认后开始 Phase 0 编码
4. ⬜ 同时准备 LLM 标注的 Prompt（Phase 1）
  ],
  "analysis": [
    "Clustering", "Deconvolution", "Imputation",
    "Cell Communication", "Spatial Trajectory",
    "Multimodal integration", "Domain Identification",
    "Gene Expression Prediction", "Segmentation",
    "Differential Expression", "Diffusion",
    "Dimensionality Reduction", "RNA Co-localization",
    "Denoising", "Application", "Benchmark",
    "Foundation", "Pipeline", "Visualization", "huSA"
  ],
  "method_note": []
}
```

移除了 `metaCategory` 和 `uncategorized` 分组——它们不是语义标签，而是元信息，不应混在标签本体中。

### 3.2 分类器约束策略（不变，但集中到 shared.py）

| 类别 | 标签规则 |
|---|---|
| **Review** | 仅 1 个标签，来自 domain 组；无命中则 "General" |
| **Technology** | 最多 2 个标签，来自 technology 组；无命中则尝试新实体提取 |
| **Database** | 优先新实体提取（数据库名），失败则空标签（不输出泛词） |
| **Data Analysis** | 最多 3 个标签，来自 analysis 组；可附一个新实体名 |
| **Research** | 至少 1 个 domain + 可选 technology 标签 |

### 3.3 前端标签过滤逻辑移除

`AnnotationForm.jsx` 中硬编码的 `["聚类","去卷积","缺失值插补","细胞通讯"]` 过滤逻辑移除。这些是 analysis 组的正常标签，应由策略引擎决定是否使用，不由前端硬过滤。

### 3.4 Tag 存储格式

- `tags` 列保持分号分隔字符串（向后兼容）
- `article_tags` 表提供结构化查询能力
- ML 特征工程从 `article_tags` 表或解析后的 tags 列表读取

---

## 阶段 4：修复并发写入（安全修复）

### 4.1 save_df() 重写

**现状**：`df.to_sql('literature', engine, index=False, if_exists='replace')`

**改为**：逐行 UPSERT，利用 `pmid` 主键：

```python
def save_article(engine, pmid: str, updates: dict):
    """Upsert a single article row by pmid."""
    with engine.begin() as con:
        # INSERT OR REPLACE approach with primary key
        ...
```

对于注释保存、标签修改等单行操作，使用直接 SQL UPDATE；对于全量导入（main.py 新文献入库），使用事务包裹的批量 INSERT OR REPLACE。

### 4.2 移除 df_lock

逐行操作 + 事务不再需要全局锁。

---

## 阶段 5：ML 管线升级（核心）

### 5.1 Discarded 分离

- `is_discarded` 作为独立二分类目标
- `ml_pipeline.py` 增加独立的 `clf_discard`（二分类器）
- Discarded 样本不再污染多标签预测的训练集

### 5.2 分类器命名修正

`AutomatedActiveLearner` → `SpatialLiteratureClassifier`

名字诚实反映功能：这是一个空间转录组文献分类器，包含类别预测 + 多标签预测 + 丢弃判别。

### 5.3 特征工程增强

- 从 `article_tags` 表读取已有标签作为特征
- 增加 MeSH 词表特征权重
- 增加期刊特征（预印本 vs 正式期刊）

### 5.4 评估管道

- 在 `ml_report.py` 中增加 per-dimension 评估：
  - Category accuracy (已存在)
  - Per-tag precision/recall/F1
  - Discarded classification AUC
  - Confusion matrix by category

---

## 阶段 6：架构分层（长期）

### 6.1 Service 层

```
web_app/
├── app.py          # FastAPI 路由（仅参数校验 + 响应）
├── services.py     # ArticleService, TagService, PDFService
├── database.py     # get_engine(), get_article(), save_article()
├── classifier.py   # 独立分类策略（引用 shared.py）
├── shared.py       # 公共函数
├── ml_pipeline.py  # ML 模型
└── ml_report.py    # 评估报告
```

### 6.2 配置集中

- 所有可变配置从 `.env` 读取
- `config.py` 作为单一配置入口

---

## 执行优先级

| 阶段 | 优先级 | 原因 |
|---|---|---|
| 0 (备份) | **立即** | 安全前提 |
| 1 (消债) | **P0** | 零风险，消除后续工作的干扰 |
| 2 (Schema) | **P0** | 后续所有改动的基础 |
| 3 (标签) | **P1** | 核心价值，不影响已有标注 |
| 4 (并发) | **P1** | 安全隐患 |
| 5 (ML) | **P2** | 依赖阶段 2、3 完成 |

---

## 回滚方案

任何阶段出问题：`cp spatial_literature_backup_YYYYMMDD.db spatial_literature.db`
数据库是 SQLite 单文件，回滚即替换。
