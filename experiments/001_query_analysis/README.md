# 001: PubMed 检索式分析

## 目的

为空间转录组学文献数据集设计 PubMed 检索式，通过实验比较不同检索字段的覆盖度和重叠情况，选出最优方案。

## 方法

对比以下检索维度：

| 字段 | 说明 |
|---|---|
| `[MeSH Major Topic]` | 2026年新引入的 MeSH 词，标记以空转为主要论题的文章 |
| `[Mesh]` | 所有提及空转的文章（含次要提及） |
| `[Title/Abstract]` 文本词 | 补捉未索引或索引前的新旧文章 |

### 测试的变体

1. 各字段单独命中数
2. 组合变体（加 `hasabstract`、去 Letter/Editorial、限制年份、限制语言）
3. 主字段（MeSH Major）与文本词的重叠比例
4. 最终检索式的年份分布

### 最终选定检索式

```
("Spatial Transcriptomics"[MeSH Major Topic]
 OR ("spatial transcriptom*"[Title/Abstract]
      OR "spatially resolved transcriptom*"[Title/Abstract]))
AND hasabstract[text]
```

**选择理由：**
- MeSH Major（9,933篇）与文本词（7,638篇）**重叠仅 0.2%**，两者几乎完全互补
- 并集 17,539 篇中去掉无摘要的 1,344 篇后得 **16,195 篇**
- 保留 Review（1,122篇），它们是有用的分类目标
- Letter/Editorial 仅 62 篇，不值得额外过滤

## 如何复现

```bash
cd experiments/001_query_analysis
bash run.sh
```

依赖：`biopython`、`pandas`（均在 `requirements.txt` 中）

## 输出

| 文件 | 内容 |
|---|---|
| `results/query_counts.csv` | 各检索字段单独命中数 |
| `results/combined_counts.csv` | 组合变体命中数 |
| `results/overlap.json` | MeSH Major 与文本词的重叠分析 |
| `results/year_distribution.csv` | 最终检索式命中文的年份分布 |

## 结论

选定 `MeSH Major Topic + text words + hasabstract` 为最终检索式，覆盖约 16,000 篇空间转录组学文献，兼顾全面性与精准度。
