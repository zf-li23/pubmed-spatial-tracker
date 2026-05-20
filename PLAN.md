# PLAN.md — PubMed Spatial Tracker 彻底重构计划

> 创建: 2026-05-20 | 状态: 初稿
>
> 本文档基于对以下材料的综合分析：
> - OHSUMED（TREC-9 Filtering Track 基准，~294K 篇，14,466 个 MeSH 标签）
> - PubMed-MultiLabel（Kaggle 数据集，10K/50K 篇，15 个 MeSH 顶级类别标签）
> - PGB（PubMed Graph Benchmark，~30M 篇，5 节点类型 + MeSH 层级结构）
> - Biomed-Enriched（两阶段大语言模型标注管线论文）
> - 现有 Spatial Tracker 项目（7,029 篇空间转录组学文献）
> - 课程 proposal（机器学习概论大作业框架）

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
| **Spatial Tracker** | 7,029 篇（481 已标注） | 5 类别 + 45 语义标签 + 丢弃判别 | 5+45+1 | **目标领域**，细粒度领域标签体系 | 最终应用场景 + LLM 批量标注验证 |

### 数据集信息维度对比

```
                   OHSUMED    PubMed-MultiLabel    PGB         Spatial Tracker
标题+摘要           ✓          ✓                    ✓            ✓
MeSH 词             ✓          ✓                    ✓（含层级）  部分（可从 PubMed API 拉取）
引用网络            ✗          ✗                    ✓            ✗
作者信息            ✗          ✗                    ✓            ✗
期刊/发表类型       ✓          ✗                    ✓            ✓
图表征              ✗          ✗                    ✓            ✗
空间转录组专用标签  ✗          ✗                    ✗            ✓
```

### 关键洞察

1. **OHSUMED** 标签空间极稀疏（14,466 个 MeSH 词，幂律分布），最适合测试**多标签分类**的扩展能力
2. **PubMed-MultiLabel** 仅 15 个粗粒度标签，但数据干净、规模适中，适合**快速算法筛选**
3. **PGB** 的独特价值在于**图结构和 MeSH 层级**——这两种信息在其他数据集中不存在，可以用来探索图神经网络和图嵌入方法
4. **PGB 中有空间转录组学相关文献**（100K 样本中约 2.3%），可用于构建 PGB→Spatial Tracker 的**迁移学习基线**

---

## 算法全景（10+ 种，不含大语言模型）

按课程模块和新增维度组织：

| 课程模块 | 算法 | 子任务适用 | 数据集适用 |
|---|---|---|---|
| 贝叶斯学习 | Naive Bayes | 类别分类、丢弃判别 | OHSUMED, PubMed-ML, ST |
| 基于实例的学习 | k-NN | 类别分类 | 全部 |
| 回归学习 | Logistic Regression | 类别分类、丢弃判别 | 全部 |
| 最大间隔方法 | SVM (RBF kernel) | 类别、标签、丢弃判别 | 全部 |
| 集成学习（Bagging） | Random Forest | 类别、标签、丢弃判别 | 全部 |
| 集成学习（Boosting） | AdaBoost | 类别、标签 | 全部 |
| 集成学习（Boosting） | XGBoost | 类别、标签、丢弃判别 | 全部 |
| 集成学习（Boosting） | LightGBM | 类别、标签、丢弃判别 | 全部 |
| 深度学习 | BioBERT + MLP 微调 | 类别分类 | 全部 |
| **图嵌入（新增）** | **node2vec** | **节点分类** | **PGB** |
| **图神经网络（新增）** | **GCN** | **节点分类** | **PGB** |
| **图神经网络（新增）** | **GraphSAGE** | **节点分类** | **PGB** |
| 无监督学习 | LDA + 聚类可视化 | 文献子领域发现 | 全部 |
| 生成式模型 | DeepSeek Zero-shot（仅参考） | 类别分类 | ST（小规模验证） |

> **图方法的引入理由**：PGB 论文明确指出 PubMed 文献可以建模为异构图（Paper, Author, MeSH Term, Venue, Publication Type），而传统的 GNN 和异质 GNN 在该数据集上表现不佳——这正是一个值得探索的开放问题。我们从简单的同构图方法（node2vec, GCN, GraphSAGE）入手，后续可探索 HAN、HGT 等异质图方法。

---

## 文本表示方案

| 表示方法 | 维度 | 适用算法 | 备注 |
|---|---|---|---|
| TF-IDF (1-2 gram, max=5,000) | 5,000 | NB, k-NN, SVM, LR, RF, Ada, XGB, LGB | 稀疏基线 |
| BioBERT embedding (mean pooling) | 768 | SVM, RF, XGB, LGB, node2vec*, GCN* | 稠密语义基线 |
| LDA 主题分布 (K=15) | 15 | NB, k-NN, SVM | 隐语义 |
| 元特征（年份、期刊类型、MeSH 存在标志等） | ~10 | 拼接至以上向量 | 辅助信号 |
| **图嵌入（node2vec）** | 128-256 | PGB 节点分类 | 结构信息 |
| **MeSH 层级特征** | 可变 | PGB 节点分类 | 树结构信息 |

---

## 实验阶段设计

```
┌──────────────────────────────────────────────────────────────────┐
│ Phase 0: 数据基础设施                                            │
│ 统一加载器 + 标准化评估框架 + 实验追踪                            │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ Phase 1: 大规模语言模型批量标注 Spatial Tracker                    │
│ 参考 Biomed-Enriched 两阶段方法，为 7K 篇空间转录组文献自动标注     │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ Phase 2: 跨数据集算法 Benchmarking（核心实验）                     │
│ 10+ 算法 × 3 数据集 × 多种文本表示 × 多种任务                      │
│ → 回答"什么方法在什么数据上表现好？为什么？"                        │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ Phase 3: 空间转录组学应用 + BioBERT 对比                          │
│ 最优方法（来自 Phase 2）vs 现有 BioBERT 基线                       │
│ 在 LLM 标注的 Spatial Tracker 上训练和测试                          │
└──────────┬───────────────────────────────────────────────────────┘
           │
           ▼
┌──────────────────────────────────────────────────────────────────┐
│ Phase 4: 迁移学习 / 微调探索                                      │
│ 宽泛预训练 → ST 测试 → ST 微调 → ST 再测试                        │
│ 多种方法探索 "预训练+微调" 范式                                   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 阶段 0：数据基础设施（预计 1 周）

### 0.1 统一数据加载器

为四个数据集分别实现标准化的 `Dataset` 类：

```python
class BiomedDataset:
    """统一接口"""
    def __init__(self, name: str, split: str): ...
    def texts(self) -> List[str]:          # 标题+摘要
    def labels(self) -> np.ndarray:         # 多标签矩阵
    def pmids(self) -> List[str]:           # 唯一标识
    def metadata(self) -> pd.DataFrame:     # 额外元特征
```

具体要求：
- **OHSUMEDLoader**：解析 TREC 格式的 `.I .U .S .M .T .P .W .A` 字段，从 `.M` 提取 MeSH 词
- **PubMedMultiLabelLoader**：读取 CSV，处理两套标签体系（原始 15 类 / Processed 版本）
- **PGBLoader**：读取 JSONL，构建可选的图结构（邻接表），提取 MeSH 层级树编号
- **SpatialTrackerLoader**：从现有 SQLite 数据库读取，兼容 `article_tags` 表

### 0.2 标准化评估框架

统一实现以下指标（scikit-learn 封装）：

| 任务类型 | 指标 |
|---|---|
| 类别多分类（Spatial Tracker 的 5 类 / PGB 的 3 类） | Accuracy, Macro/Weighted F1, Cohen's κ |
| 多标签（OHSUMED 的 MeSH / PubMed-ML 的 15 类 / ST 的 45 标签） | Jaccard 相似度, Hamming Loss, Per-label F1 |
| 二分类（丢弃判别） | AUC-ROC, Precision-Recall AUC, F1 |
| 图节点分类（PGB） | Micro/Macro F1, NMI, ARI |

### 0.3 实验追踪

- 使用 MLflow 或简单的 CSV 日志记录每次实验的：
  - 数据集 + 文本表示 + 算法 + 超参数
  - 所有评估指标
  - 训练时间 / 推理时间

### 0.4 目录结构

```
benchmark/
├── __init__.py
├── datasets/
│   ├── base.py              # BiomedDataset 基类
│   ├── ohsumed.py           # OHSUMEDLoader
│   ├── pubmed_multilabel.py # PubMedMultiLabelLoader
│   ├── pgb.py               # PGBLoader（含图构建）
│   └── spatial_tracker.py   # SpatialTrackerLoader
├── features/
│   ├── tfidf.py             # TF-IDF 向量化
│   ├── biobert.py           # BioBERT 嵌入
│   ├── lda_features.py      # LDA 主题特征
│   ├── metadata.py          # 元特征
│   └── graph_features.py    # 图嵌入（node2vec 等）
├── models/
│   ├── classical.py         # NB, k-NN, SVM, LR
│   ├── ensemble.py          # RF, AdaBoost, XGBoost, LightGBM
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

## 阶段 1：LLM 批量标注 Spatial Tracker（预计 1-2 周）

### 核心思路

参考 **Biomed-Enriched** 的两阶段标注方法：

1. **第一阶段（LLM 标注）**：使用 **DeepSeek API**（OpenAI 兼容格式，可通过 `openai` Python 库调用，设置 `base_url="https://api.deepseek.com"`）对部分空间转录组文献进行详细标注
2. **第二阶段（模型蒸馏）**：用标注结果训练一个小型分类器（如 BioBERT 或 XLM-RoBERTa），将标注扩展到全部 7,029 篇

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

### 评估策略

- 用现有的 481 篇人工标注作为 **gold standard**
- 对比 LLM 标注 vs 人工标注的一致性（Cohen's κ）
- 分析 LLM 在不同类别/标签上的准确率差异
- 用 LLM 标注的训练 ML 模型 vs 用人工标注训练的 ML 模型 → 对比下游性能

### LLM 标注的关键设计

1. **Prompt Engineering**：为每个类别（Review/Technology/Database/Data Analysis/Research）设计不同的 CoT 推理路径；DeepSeek-R1 的推理能力尤其适合此场景
2. **标签约束**：在 prompt 中嵌入 `enforce_category_tag_policy()` 的逻辑
3. **不确定度估计**：要求 LLM 输出置信度分数，低置信度样本保留给人工

---

## 阶段 2：跨数据集算法 Benchmarking（核心实验，预计 2-3 周）

### 2.1 实验矩阵

```
数据集 × 文本表示 × 算法 × 任务 = 实验总数

OHSUMED (1) × TF-IDF/BioBERT/LDA/Meta (4) × 8种ML算法 = 32  ← 多标签分类
PubMed-ML (1) × TF-IDF/BioBERT/LDA/Meta (4) × 8种ML算法 = 32  ← 多标签分类
PGB (1) × TF-IDF/BioBERT/node2vec/GCN/GraphSAGE (5) × 3种图方法 + 5种文本方法 = 15-20
                                                                              ─────
                                                                   约 80-85 组实验
```

> 每组实验用 5 折交叉验证，报告均值和标准差。

### 2.2 子实验设计

| 实验编号 | 名称 | 目的 | 方法 |
|---|---|---|---|
| E2.1 | **特征对比** | 最优文本表示 | 固定 SVM，TF-IDF/BioBERT/LDA/组合 在 3 个数据集上比较 |
| E2.2 | **算法全矩阵** | 10+ 种算法排序 | 固定 BioBERT 嵌入，所有算法在 3 个数据集上比较 Macro F1 与训练时间 |
| E2.3 | **多标签策略** | 最优转换策略 | BR/CC/LP × 基分类器，对比 Jaccard 与 Hamming Loss |
| E2.4 | **图方法**（PGB 特有） | 结构信息价值 | node2vec/GCN/GraphSAGE vs 纯文本方法，用/不用 MeSH 层级 |
| E2.5 | **MeSH 层级消融**（PGB 特有） | 层级信息收益 | 有/无 MeSH tree number 的 GCN 性能差异 |
| E2.6 | **学习曲线** | 标注饱和度 | 训练集从 50 到全量，观察 F1 收敛 |
| E2.7 | **跨数据迁移** | 泛化验证 | 在同一文本表示下，一个数据集训练 → 另一个数据集测试 |

### 2.3 预期产出

1. **算法 × 数据集 的热力图**：哪个算法在哪个数据集上表现最好
2. **特征有效性排序**：BioBERT vs TF-IDF vs LDA vs 图嵌入的相对提升
3. **数据特性影响分析**：
   - 标签空间大小（14K vs 15）对算法扩展性的影响
   - 图结构信息的边际收益
   - MeSH 层级的价值量化
4. **每数据集推荐算法**

---

## 阶段 3：空间转录组学应用 + BioBERT 对比（预计 1 周）

### 3.1 方法选择

从 Phase 2 的结果中，为每个数据集选择 top-3 算法，然后在 Spatial Tracker 上验证：

| 来源数据集 | Top-1 算法 | Top-2 算法 | Top-3 算法 |
|---|---|---|---|
| OHSUMED | ? | ? | ? |
| PubMed-ML | ? | ? | ? |
| PGB | ? | ? | ? |

### 3.2 与 BioBERT 基线对比

当前已有管线中，`ml_pipeline.py` 使用 BioBERT 嵌入 + SVM 做分类。对比实验：

```
基线: BioBERT embedding + SVM（当前实现）
对照: Phase 2 选出的最优方法
对照: BioBERT embedding + 最优分类器（如 XGBoost）
对照: TF-IDF + 最优分类器
```

评估维度：
- 分类准确率（5 类别）
- 标签 F1（45 个语义标签）
- 丢弃判别 AUC
- **推理速度**（对 PubMed API 在线分类场景很重要）
- **训练时间**（对主动学习迭代场景很重要）

---

## 阶段 4：迁移学习 / 微调探索（预计 1-2 周）

这是最具有探索性质的阶段，核心问题是：

> **能否用宽泛生物医学数据预训练，再用领域数据微调，实现性能提升？**

### 4.1 迁移实验设计

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

### 4.2 适用"微调"概念的算法

并非所有算法都支持微调。以下为候选：

| 算法 | 微调方式 | 可行性 |
|---|---|---|
| **BioBERT + MLP** | 加载预训练权重 → 全领域微调 → 目标领域微调 | ✅ 标准做法 |
| **SVM / Logistic Regression** | 无法增量学习 | ❌ |
| **Random Forest / XGBoost / LightGBM** | 可在预训练模型基础上继续训练（warm start） | ⚠️ 部分支持 |
| **GCN / GraphSAGE** | 在 PGB 上预训练 → ST 图上微调 | ✅ 图迁移学习 |
| **node2vec** | 预训练嵌入 → 在新图上重新训练或对齐 | ⚠️ 需对齐策略 |

因此 Phase 4 的重点算法：
1. **BioBERT + MLP**（深度学习微调标准范式）
2. **XGBoost / LightGBM**（集成学习的 warm start 能力）
3. **GCN / GraphSAGE**（图迁移学习的探索）

### 4.3 跨数据集迁移（PGB → ST）

PGB 中包含约 2.3% 的空间转录组学相关文献（基于 100K 样本估算）。
可以：
1. 在 PGB 的整个图上预训练 GCN/GraphSAGE
2. 在 Spatial Tracker 的文献子图上微调
3. 比较：纯 ST 训练 vs PGB 预训练 + ST 微调

### 4.4 预期产出

- "微调增益"量化表：每种算法在微调前后的 F1 变化
- 预训练数据规模 vs 微调增益的关系曲线
- 哪些算法适合 "预训练 + 微调" 范式的系统性结论

---

## 总体时间线

```
周 1:   Phase 0 — 数据基础设施搭建
        - 四个数据集的统一加载器
        - 评估框架
        - 实验追踪

周 2-3: Phase 1 — LLM 批量标注
        - Prompt 工程
        - 两阶段标注流程
        - 质量评估（vs 人工标注）

周 4-6: Phase 2 — 跨数据集算法 Benchmarking
        - 80+ 组实验
        - 结果分析与可视化
        - 方法选择

周 7:   Phase 3 — 空间转录组应用 + BioBERT 对比
        - Top-3 方法 vs 基线
        - 速度/质量权衡分析

周 8-9: Phase 4 — 迁移学习 / 微调探索
        - 3 种算法的微调实验
        - 跨数据集迁移
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
| 基于实例的学习 | k-NN |
| 回归学习 | Logistic Regression |
| 最大间隔方法 | SVM (RBF kernel) |
| 集成学习 | Random Forest, AdaBoost, XGBoost, LightGBM |
| 深度学习 | BioBERT + MLP 微调 |
| 无监督学习 | LDA + 聚类 |
| 生成式模型 | DeepSeek 零样本（作为补充） |
| **图表示学习（课程未包含，PGB 启发新增）** | node2vec, GCN, GraphSAGE |

### 与 Proposal 的变化

| 项目 | Proposal 原计划 | 新计划 | 变更理由 |
|---|---|---|---|
| 数据集 | ST + OHSUMED（2 个） | ST + OHSUMED + PubMed-ML + PGB（4 个） | PGB 提供图结构信息，PubMed-ML 提供现代基准 |
| 算法 | 12 种 | 10+ 种（新增图方法，移除 GPT-4o 作为主体） | 图方法由 PGB 启发新增；LLM 改为标注工具而非分类器 |
| 主动学习 | 3 种策略对比 | 暂缓，移至 Phase 4 后 | 先解决基础分类问题，再考虑主动学习 |
| LLM 角色 | GPT-4o 零样本分类 | **DeepSeek API** 批量标注全数据集 | Biomed-Enriched 论文启发；DeepSeek 兼容 OpenAI 格式，可用 `deepseek-reasoner`/`deepseek-chat` 替代 |
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
| `ml_pipeline.py` | 新 `benchmark/` 下的模块化管线 |
| `ml_report.py` | 新 `evaluation/report.py` |
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

### Spatial Tracker Schema

```sql
CREATE TABLE literature (
    pmid TEXT PRIMARY KEY,
    title TEXT, abstract TEXT,
    category TEXT,           -- 5 类: Review/Technology/Database/Data Analysis/Research
    tags TEXT,               -- 分号分隔的语义标签
    is_manually_confirmed INTEGER,
    is_discarded INTEGER DEFAULT 0,
    uncertainty_score REAL,
    ...
);
CREATE TABLE article_tags (
    pmid TEXT NOT NULL,
    tag TEXT NOT NULL,
    tag_group TEXT NOT NULL,  -- domain/technology/analysis/method_note
    PRIMARY KEY (pmid, tag)
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
