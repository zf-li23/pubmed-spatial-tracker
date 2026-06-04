# PubMed Spatial Tracker

> **机器学习概论 课程大作业** — 面向生物医学文献的多策略多标签分类研究
> 聚焦空间转录组学（Spatial Transcriptomics）领域

## 项目目标

通过 **7 组实验 × 115 组子任务（98.3% 完成）** 的系统性比较，构建一个**多数据集 × 多算法 × 多文本表示**的实验框架，量化不同方法在生物医学文献分类上的表现，并应用于空间转录组学文献的自动标注与分类。

**核心发现**：PML 预训练 + ST 微调的 BioBERT+MLP 达到 **F1=0.9143** 🏆，比直接训练提升 +9.6%。

---

## 数据集

| 数据集 | 规模 | 标签数 | 角色 | 来源 |
|---|---|---|---|---|
| **OHSUMED** | ~10K 篇（采样） | 1,650 MeSH 标签 | 大规模稀疏标签基准 | TREC-9 Filtering Track |
| **PubMed-MultiLabel (PML)** | 10K 篇 | 16 类别 | 粗粒度快速实验 | Kaggle |
| **PGB** | 5K 篇（采样） | 3 类节点分类 | 图结构方法验证 | PubMed Graph Benchmark |
| **Spatial Tracker (ST)** | **9,148 篇** | **6 类别** | **目标应用** | 自建（PubMed 检索+LLM 标注） |

**Spatial Tracker 标签体系**：6 类别（Research/Technology/Review/Protocol/Data Resource/Benchmark）+ 15 分析标签 + 19 技术平台 + 17 生物学领域。9,148 篇全部由 DeepSeek-v4-flash 批量标注完成。

---

## 实验结果总览

### Exp 001: 经典算法矩阵（82/84 完成 ✅）

7 模型 × 4 特征 × 3 数据集 = 84 组，5 折交叉验证。

**最佳组合**：
| 数据集 | 特征 | 最佳模型 | F1-macro |
|---|---|---|---|
| OHSUMED | TF-IDF | AdaBoost | **0.1687** |
| PML | BioBERT | LogisticReg | **0.6710** 🏆 |
| PGB | TF-IDF | AdaBoost | **0.4215** |

### Exp 002: BioBERT+MLP 端到端微调（3/3 ✅）

| 数据集 | F1-macro | 时间 |
|---|---|---|
| OHSUMED | 0.0013 | 17min |
| PML | **0.6411** | 19min |
| PGB | **0.3601** | 9min |

### Exp 003: LDA+无监督聚类（3/3 ✅）

| 数据集 | NMI |
|---|---|
| OHSUMED | **0.44** |
| PML | 0.10 |
| PGB | 0.005 |

### Exp 004: 多标签策略（6/6 ✅）

CC on PML 最优：**F1=0.5796** 🏆，BR 与 LP 持平 0.5686。

### Exp 005: 图模型（8/9 ✅）

| 方法 | F1-macro |
|---|---|
| **GCN** | **0.4125** 🏆 |
| Node2Vec | ~0.3324 |
| GraphSAGE | ~0.3324 |

### Exp 006: ST 基准测试（3/3 ✅）

| 方法 | F1-macro | Accuracy |
|---|---|---|
| TF-IDF + SVM | 0.6365 | 0.9167 |
| BioBERT + LR | 0.8068 | 0.9298 |
| **BioBERT + MLP** | **0.8444** 🏆 | **0.9434** |

### Exp 007: 迁移微调（11/13 完成 ✅）

| 预训练域 | 算法 | 直接训练 | 微调后 | 增益 |
|---|---|---|---|---|
| PML (16 标签) | BioBERT+MLP | 0.8345 | **0.9143** 🏆 | **+9.6%** 🔥 |
| OHSUMED (1,650 标签) | BioBERT+MLP | 0.8345 | 0.8503 | +1.9% |
| ST (k-NN 图) | GCN | — | 0.7716 | — |
| ST (k-NN 图) | GraphSAGE | — | 0.7603 | — |

---

## 方法总览

**文本表示（5 种）**：TF-IDF / BioBERT 嵌入(768d) / LDA(15 topics) / Meta 特征 / Node2Vec(128d)

**分类算法（14 种）**：NaiveBayes / k-NN / SVM / LogisticReg / RandomForest / AdaBoost / XGBoost / LightGBM / BioBERT+MLP / LDA+KMeans / Node2Vec / GCN / GraphSAGE

---

## 项目结构

```
src/                    # 核心代码
├── datasets/           # 4 数据集加载器（统一 BiomedDataset 接口）
├── features/           # 5 种文本表示提取器
├── models/             # 14 种算法实现
├── annotate/           # DeepSeek API 批量标注管
├── evaluation/         # 评估指标
├── search/             # PubMed 检索
├── config.py           # 实验配置
└── pipeline.py         # 实验调度

experiments/            # 7 组可复现实验
├── 000_query_analysis/ # PubMed 检索式设计
├── 001_classical_matrix/ # 7×4×3=84 组经典算法矩阵
├── 002_biobert_mlp/    # BioBERT+MLP 端到端微调
├── 003_lda_cluster/    # LDA+KMeans 无监督聚类
├── 004_multilabel_strategy/ # BR/CC/LP 多标签策略
├── 005_graph_models/   # Node2Vec/GCN/GraphSAGE 图模型
├── 006_st_benchmark/   # ST 三方法基准测试
└── 007_transfer_learning/ # 迁移微调探索

data/
└── spatial_tracker/    # 9,148 篇已标注文献

report/                 # 分析报告
├── experiment_retrospective.md  # 完整实验回顾
├── annotation_stats.md          # 标注统计分析
├── review_template.csv          # 人工抽检模板
└── proposal.tex                 # 课程 proposal
```

---

## 环境

```bash
conda create -n pubmed-tracker python=3.13
conda activate pubmed-tracker
pip install -r requirements.txt

# GPU 环境（BioBERT+MLP 微调）
conda create -n biobert_env python=3.12
pip install torch==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt
```

更多细节见 [`PLAN.md`](PLAN.md)（完整计划）和 [`report/experiment_retrospective.md`](report/experiment_retrospective.md)（实验回顾）。
