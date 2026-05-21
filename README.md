# PubMed Spatial Tracker

面向生物医学文献的多策略多标签分类研究——聚焦空间转录组学领域。

## 项目目标

通过**多数据集 × 多算法 × 多文本表示**的系统性比较，探索生物医学文献自动分类的最佳策略，并最终应用于空间转录组学领域。

## 当前进度

| 阶段 | 状态 | 简述 |
|---|---|---|
| Phase 0: 数据基础设施 | ✅ 已完成 | 4 数据集加载器 + 4 种文本表示 + 7+ 种算法实现 + 评估框架 |
| Exp 001: PubMed 查询分析 | ✅ 已完成 | 比较 7 种查询变体，选定最终检索式 |
| PubMed 数据抓取 | ✅ 已完成 | 9,148 篇空间转录组学文献已爬取 |
| Step 2a: 标签体系设计 | ✅ 已完成 | 6 类别 × 15 分析标签 × 19 技术 × 17 生物领域 |
| Step 2b: LLM 批量标注 | 🔄 进行中 | 3,990/9,148 篇（43.6%）已用 DeepSeek 标注 |
| Step 1: 算法筛选 | ⬜ 未开始 | 约 100 组跨数据集实验 |
| Step 3: 迁移微调 | ⬜ 未开始 | 3 种算法的微调探索 |

## 数据集

| 数据集 | 规模 | 标签空间 | 说明 |
|---|---|---|---|
| [OHSUMED](data/ohsumed/) | ~294K 篇 | 14,466 个 MeSH 词 | TREC-9 Filtering Track 基准（1987-1991），全标注 |
| [PubMed-MultiLabel](data/PubMed-MultiLabel/) | 10K/50K 篇 | 15 个 MeSH 顶级类别 | Kaggle 现代多标签数据集，全标注 |
| [PGB](data/pgb/) | ~30M 篇 | MeSH 层级 + 图结构 | 异构图基准（5 节点 / 7 边类型），全标注 |
| Spatial Tracker | 9,148 篇（已爬取） | 6 类别 + 15 分析标签 + 19 技术 | 自建空间转录组学文献库，LLM 批量标注中 |

## 实验设计（三步渐进）

详见 [PLAN.md](PLAN.md)。

1. **Step 1** — 在三个全标注数据集上对比 12 种算法 × 4 种文本表示，筛选最优方法
2. **Step 2** — 构建空间转录组学数据集 + DeepSeek 批量标注，应用最优方法 vs BioBERT 基线
3. **Step 3** — 探索"宽泛预训练 + 领域微调"的迁移学习范式

## 算法

12 种算法覆盖贝叶斯学习、基于实例的学习、回归、集成学习（Bagging/Boosting）、深度学习、无监督学习、图表示学习。

## 项目结构

```
src/
├── config.py              # 实验配置
├── pipeline.py            # 实验调度
├── annotate/              # LLM 批量标注
│   └── batch_annotate.py  # DeepSeek API 标注管线
├── datasets/              # 数据加载器（统一 BiomedDataset 接口）
├── features/              # 文本表示（TF-IDF / BioBERT / LDA / 元特征）
├── models/                # 算法实现（经典/集成/深度/无监督）
├── evaluation/            # 评估指标 & 日志
├── search/                # PubMed 检索 & 数据构建
data/
├── spatial_tracker/
│   ├── articles.csv             # 9,148 篇已爬取
│   └── annotated_articles.csv   # 3,990 篇已标注
experiments/
├── 001_query_analysis/    # 查询变体比较（7 种）
```

## 环境

```bash
conda activate zf-li23
pip install -r requirements.txt
```

## 重要说明

本项目为机器学习课程大作业。AI 辅助编程工具（GitHub Copilot）仅用于：
1. 项目架构设计与代码框架搭建
2. 代码审查与调试
3. 文档编写
4. **LLM 仅作为数据标注工具**（DeepSeek API 标注分类标签）

所有核心算法实现、实验设计与分析均由人工完成。AI 辅助生成的任何代码在最终提交前均需经人工审查和必要重写。
