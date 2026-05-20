# PubMed Spatial Tracker

面向生物医学文献的多策略多标签分类研究——聚焦空间转录组学领域。

## 项目目标

通过**多数据集 × 多算法 × 多文本表示**的系统性比较，探索生物医学文献自动分类的最佳策略，并最终应用于空间转录组学领域。

## 数据集

| 数据集 | 规模 | 标签空间 | 说明 |
|---|---|---|---|
| [OHSUMED](data/ohsumed/) | ~294K 篇 | 14,466 个 MeSH 词 | TREC-9 Filtering Track 基准（1987-1991），全标注 |
| [PubMed-MultiLabel](data/PubMed-MultiLabel/) | 10K/50K 篇 | 15 个 MeSH 顶级类别 | Kaggle 现代多标签数据集，全标注 |
| [PGB](data/pgb/) | ~30M 篇 | MeSH 层级 + 图结构 | 异构图基准（5 节点 / 7 边类型），全标注 |
| Spatial Tracker | ~数千篇（待构建） | 5 类 + 45 标签（待定义） | 自建空间转录组学文献库，LLM 批量标注 |

## 实验设计（三步渐进）

详见 [PLAN.md](PLAN.md)。

1. **Step 1** — 在三个全标注数据集上对比 12 种算法 × 4 种文本表示，筛选最优方法
2. **Step 2** — 构建空间转录组学数据集 + DeepSeek 批量标注，应用最优方法 vs BioBERT 基线
3. **Step 3** — 探索"宽泛预训练 + 领域微调"的迁移学习范式

## 算法

12 种算法覆盖贝叶斯学习、基于实例的学习、回归、集成学习（Bagging/Boosting）、深度学习、无监督学习、图表示学习。

## 项目结构

```
benchmark/
├── config.py              # 实验配置
├── datasets/              # 数据加载器
├── features/              # 文本表示（TF-IDF / BioBERT / LDA）
├── models/                # 算法实现
├── evaluation/            # 评估指标 & 日志
└── pipeline.py            # 实验调度
```

## 环境

```bash
conda activate zf-li23
pip install -r requirements.txt
```
