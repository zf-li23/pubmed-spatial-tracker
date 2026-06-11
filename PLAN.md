# PLAN.md — PubMed Spatial Tracker 彻底重构计划

> 创建: 2026-05-20 | 最后更新: 2026-06-05
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
| 🧪 **Exp 001: 经典算法矩阵** | ✅ **84/84 完成** | 7 模型 × 4 特征 × 3 数据集 = 84 组全部完成 |
| 🧪 **Exp 002: BioBERT+MLP 微调** | ✅ **已完成** | OHSUMED(F1=0.0013), PML(F1=0.6411), PGB(F1=0.3601) |
| 🧪 **Exp 003: LDA+聚类** | ✅ **已完成** | OHSUMED NMI=0.44, PML NMI=0.10, PGB NMI=0.005 |
| 🧪 **Exp 004: 多标签策略** | ✅ **已完成** | BR/CC/LP 对比，CC on PML F1=0.5796 🏆 |
| 🧪 **Exp 005: 图模型** | ✅ **8/9 完成** | GCN(0.4125🏆) >> Node2Vec(0.3324) ≈ GraphSAGE(0.3324) |
| 🏷️ **Step 2续: ST 基准测试** | ✅ **已完成** | BioBERT+MLP(0.8444🏆) > BioBERT+LR(0.8068) > TF-IDF+SVM(0.6365) |
| 🔀 **Exp 007: 迁移微调探索** | ✅ **11/13 完成** | PML→ST MLP 微调 F1=**0.9143** 🏆 |

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

## 算法全景（12 种）

按课程模块组织，覆盖 7 种经典算法 + 2 种扩展算法 + 3 种图模型：

| 类别 | 算法 | 子任务适用 | 数据集适用 |
|---|---|---|---|
| 经典算法（7 种） | NaiveBayes / k-NN / SVM / LogisticReg / RandomForest / AdaBoost / XGBoost | 类别分类 | 全部 |
| 深度学习 | BioBERT + MLP 微调 | 类别分类 | 全部 |
| 无监督学习 | LDA + KMeans 聚类 | 文献子领域发现 | 全部 |
| 图模型 | GCN / GraphSAGE | 节点分类 | PGB / ST(k-NN 图) |
| 图嵌入 | Node2Vec + 经典分类器 | 节点分类 | PGB |

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
│ Step 1: 多数据集算法筛选（三个全标注数据集）                            │
│                                                                      │
│  OHSUMED ──→ TF-IDF/BioBERT/LDA ──→ 7种经典算法 ───→ 最优方法 Top-3   │
│  (14K标签)    + Meta Features        (NB/k-NN/SVM/LR/RF/Ada/XGB)     │
│  PubMed-ML ─→ TF-IDF/BioBERT/LDA ──→ 7种经典算法 ───→ 最优方法 Top-3  │
│  (15标签)      + Meta Features                                       │
│                                                                      │
│  PGB ───────→ TF-IDF/BioBERT/LDA ──→ 7种经典算法 ───→ 最优方法 Top-3  │
│  (图+MeSH层级)  + Meta + Node2Vec     + node2vec/GCN/GraphSAGE       │
│                                                                      │
│  → 产出：算法×数据集热力图、特征有效性排序、图结构边际收益量化            │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Step 2: 目标数据集构建与应用                                           │
│                                                                      │
│  PubMed检索 ──→ 空间转录组学文献库 ──→ DeepSeek API 批量标注            │
│  (查询实验 001)   (9,148篇已爬取)        (6维标签体系)                 │
│                                              │                       │
│                                              ▼                       │
│  Step 1 最优方法 ──→ 在 ST 上训练/测试 ──→ vs BioBERT+MLP 基线         │
│  (Top-3 × 3来源)        (LLM标注版)          (对比F1/速度/可扩展性)    │
└──────────────────────────────────┬───────────────────────────────────┘
                                   │
                                   ▼
┌──────────────────────────────────────────────────────────────────────┐
│ Step 3: 迁移微调探索                                                  │
│                                                                      │
│  宽泛预训练         空间转录组微调       最终测试                       │
│  ──────────→        ──────────→        ──────────→                   │
│  OHSUMED/PGB      Spatial Tracker     Spatial Tracker                │
│  (BioBERT/XGB/     (增量训练)          (对比微调前后F1)                │
│   GCN/GraphSAGE)                                                     │
│                                                                      │
│  → 产出："宽泛预训练+领域微调"范式的增益量化                            │
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

### Step 1 实验（全部完成 ✅）

| 实验 | 内容 | 组数 | 状态 | 最佳结果 |
|---|---|---|---|---|
| **001** | 经典算法矩阵：7 模型 × 4 特征 × 3 数据集 | **84** | ✅ 全部完成 | PML+BioBERT+LR **0.6710** |
| **002** | BioBERT+MLP 端到端微调 × 3 数据集 | 3 | ✅ 完成 | PML **0.6411** |
| **003** | LDA+KMeans 无监督聚类 × 3 数据集 | 3 | ✅ 完成 | OHSUMED NMI=**0.44** |
| **004** | 多标签策略 BR/CC/LP × 2 数据集 | 6 | ✅ 完成 | PML+CC **0.5796** |
| **005** | 图模型 Node2Vec×7 + GCN + GraphSAGE × PGB | 9 | ✅ 8/9 完成 | GCN **0.4125** |

**总计：105 组**。001 支持 `--datasets/--features/--models` 选择性运行。

### Exp 001: 经典算法矩阵（84/84 ✅）

最佳组合（各数据集 F1-macro 排序）：
| 数据集 | 🥇 冠军 | F1 | 🥈 亚军 | F1 |
|---|---|---|---|---|
| **OHSUMED**（1,650 标签） | AdaBoost+TF-IDF | **0.1687** | LogisticReg+BioBERT | 0.0853 |
| **PML**（16 标签） | LogisticReg+BioBERT | **0.6710** | SVM+BioBERT | 0.6603 |
| **PGB**（3 类） | AdaBoost+TF-IDF | **0.4215** | SVM+TF-IDF | 0.3775 |

### Exp 002: BioBERT+MLP 端到端微调（3/3 ✅）

| 数据集 | F1-macro | 训练时间 |
|---|---|---|
| OHSUMED | 0.0013 | 17min |
| PML | **0.6411** | 19min |
| PGB | **0.3601** | 9min |

### Exp 003: LDA+聚类（3/3 ✅）

| 数据集 | NMI |
|---|---|
| OHSUMED | **0.44** |
| PML | 0.10 |
| PGB | 0.005 |

### Exp 004: 多标签策略（6/6 ✅）

CC on PML F1=**0.5796** 🏆，BR 与 LP 持平 0.5686。OHSUMED（1,650 标签）上所有策略 F1<0.01。

### Exp 005: 图模型（8/9 ✅）

**GCN** 0.4125 🏆 >> Node2Vec+LR 0.3324 ≈ GraphSAGE 0.3324

---

## Step 2: 目标数据集构建与应用 ✅

### LLM 标签体系设计 ✅

6 类别（Research/Technology/Review/Protocol/Data Resource/Benchmark）+ 15 分析标签 + 19 技术平台 + 17 生物学领域。

### LLM 批量标注 ✅

9,148 篇全部使用 DeepSeek-v4-flash 标注完成。标注分布：
- Research(58.3%) > Technology(19.5%) > Review(14.3%) > Protocol(6.0%) > Data Resource(1.0%) > Benchmark(0.9%)
- 置信度：high(47.1%), medium(48.5%), low(4.4%)

### 标注统计分析 ✅ → `report/annotation_stats.md`

### ST 基准测试（Exp 006）✅

在 9,148 篇标注数据上比较 3 种方法：

| 方法 | F1-macro | Accuracy | 时间 |
|---|---|---|---|
| TF-IDF + SVM | 0.6365 ± 0.0123 | 0.9167 ± 0.0011 | 913s |
| BioBERT + LR | 0.8068 ± 0.0320 | 0.9298 ± 0.0035 | **138s** ⚡ |
| **BioBERT + MLP** | **0.8444** 🏆 ± 0.0353 | **0.9380** ± 0.0124 | 1039s |

---

## Step 3: 迁移微调探索 ✅

**核心问题**：在源域（OHSUMED/PML/PGB）上训练的分类器，能否通过在 Spatial Tracker 上微调获得比直接训练更高的 F1？

### 实验结果（Exp 007: 11/13 完成 ✅）

| 实验 | 方法 | F1-macro | 说明 |
|---|---|---|---|
| **B1** | ST→ST BioBERT+LR（基线） | 0.8157 | 80/10/10 固定划分 |
| **B2** | ST→ST BioBERT+MLP（基线） | 0.8345 | 同上 |
| B3 | ST→ST XGBoost | 0.7457 | Boosting 基线 |
| **C1** 🏆 | **PML 预训练 → ST 微调 MLP** | **0.9143** 🏆 | **+9.6% ↑** |
| C2 | OHSUMED 预训练 → ST 微调 MLP | 0.8503 | +1.9% ↑ |
| D1 | GCN on ST k-NN 图 | 0.7716 | 相似度图验证 |
| D2 | GraphSAGE on ST k-NN 图 | 0.7603 | 同上 |
| A1-A5 | 零样本迁移（标签空间不同） | ~0.0 | 预期结果 |

**核心结论**：PML 预训练 + ST 微调是最优策略（F1=**0.9143**），比直接训练提升 +9.6%。
k-NN 图的 GCN/GraphSAGE 在 ST 上达到 F1≈0.77，接近 LR 基线但未超越。


---

## 课程大作业对接

| 课程模块 | 对应内容 |
|---|---|
| 贝叶斯学习 | Naive Bayes |
| 基于实例的学习 | k-NN, SVM |
| 回归学习 | Logistic Regression |
| 集成学习 | Random Forest, AdaBoost, XGBoost |
| 深度学习 | BioBERT + MLP 微调 |
| 无监督学习 | LDA + 聚类 |
| 图表示学习 | node2vec, GCN, GraphSAGE |

> **AI 辅助编程说明**：GitHub Copilot 全程辅助代码编写，包括项目架构设计、功能实现、代码审查、调试和文档编写。
> DeepSeek API 仅作为数据标注工具（标注空间转录组学文章标签）。

---

> **完整实验回顾** → [`report/experiment_retrospective.md`](report/experiment_retrospective.md)
> **代码复现说明** → [`experiments/README.md`](experiments/README.md)
> **集群部署指南** → [`CLUSTER_SETUP.md`](CLUSTER_SETUP.md)
