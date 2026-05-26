# PubMed Spatial Tracker

面向生物医学文献的多策略多标签分类研究——聚焦空间转录组学领域。

## 项目目标

通过**多数据集 × 多算法 × 多文本表示**的系统性比较，探索生物医学文献自动分类的最佳策略，并最终应用于空间转录组学领域。

## 当前进度

| 阶段 | 状态 | 简述 |
|---|---|---|
| Phase 0: 数据基础设施 | ✅ 已完成 | 4 数据集加载器 + 4 种文本表示 + 7+ 种算法 + 评估框架 |
| Exp 001: PubMed 查询分析 | ✅ 已完成 | 7 种查询变体比较，选定最终检索式 → 9,148 篇 |
| PubMed 数据抓取 | ✅ 已完成 | 9,148 篇空间转录组学文献已爬取 |
| Step 2a: 标签体系设计 | ✅ 已完成 | 6 类别 × 15 分析标签 × 19 技术 × 17 生物领域 |
| Step 2b: LLM 批量标注 | ✅ 已完成 | 9,148 篇全部用 DeepSeek 标注完成 |
| E1.1 特征对比 | ✅ 已完成 | BioBERT > TF-IDF > LDA（BioBERT 提升 3.3×） |
| E1.3 多标签策略 | ✅ 已完成 | BR = LP > CC |
| E1.2 算法全矩阵 | 🔄 集群运行中 | 12h 作业 |
| Step 3: 迁移微调 | ⬜ 未开始 | — |

## 数据集

| 数据集 | 规模 | 标签空间 | 说明 |
|---|---|---|---|
| [OHSUMED](data/ohsumed/) | ~294K 篇 | 14,466 个 MeSH 词 | TREC-9 Filtering Track 基准（1987-1991），全标注 |
| [PubMed-MultiLabel](data/PubMed-MultiLabel/) | 10K/50K 篇 | 15 个 MeSH 顶级类别 | Kaggle 现代多标签数据集，全标注 |
| [PGB](data/pgb/) | ~30M 篇 | MeSH 层级 + 图结构 | 异构图基准（5 节点 / 7 边类型），全标注 |
| Spatial Tracker | **9,148 篇**（已爬取+标注） | 6 类别 + 15 分析标签 + 19 技术 | 自建空间转录组学文献库，LLM 批量标注 |

## 初步实验结果

### 特征对比（E1.1）

固定 LR，比较三种文本表示：

| 数据集 | TF-IDF | LDA | **BioBERT** |
|--------|--------|-----|-------------|
| OHSUMED (45 标签) | 0.0958 | 0.0832 | **0.3135** |
| PML (16 标签) | 0.5580 | 0.5264 | **0.6665** |
| PGB (3 类) | 0.3324 | — | 0.3324 |

> **BioBERT 显著优于 TF-IDF 和 LDA**，OHSUMED 上提升 3.3×，但速度慢 100-150×。

### 多标签策略（E1.3）

| 数据集 | BR | CC | LP |
|--------|----|----|----|
| OHSUMED (1,650 标签) | 0.0062 | 0.0077 | 0.0062 |
| PML (16 标签) | **0.5580** | ❌ | **0.5580** |

> **BR = LP**，标签空间太大时所有策略失效。

## 算法

7+ 种算法覆盖贝叶斯学习、基于实例的学习、回归、集成学习（Bagging/Boosting）、深度学习。

## 项目结构

```
src/
├── config.py              # 实验配置
├── pipeline.py            # 实验调度
├── annotate/              # LLM 批量标注
├── datasets/              # 数据加载器
├── features/              # 文本表示
├── models/                # 算法实现
├── evaluation/            # 评估指标 & 日志
└── search/                # PubMed 检索
experiments/
├── 001_query_analysis/    # 查询变体比较
├── 002_feature_compare/   # 特征对比 ✅
├── 003_algorithm_matrix/  # 算法全矩阵 🔄
└── 004_multilabel_strategy/ # 多标签策略 ✅
data/
└── spatial_tracker/       # 9,148 篇已标注
```

## 环境

```bash
conda activate pubmed-tracker
pip install -r requirements.txt
```
