# 002: 特征对比 — SVM × TF-IDF / BioBERT / LDA

## 目的

固定模型（Logistic Regression），比较三种文本表示方法在不同数据集上的分类性能。

## 方法

| 维度 | 取值 |
|------|------|
| 模型 | Logistic Regression（OvR 多标签） |
| 特征 | TF-IDF (5K dim), LDA (15 topics), BioBERT (768-dim) |
| 数据集 | OHSUMED (3K 篇, 45 标签), PML (10K 篇, 16 标签), PGB (5K 篇, 3 类) |
| 评估 | 3 折 CV, macro F1 |

## 结果

| Dataset | n_labels | n_samples | TF-IDF | LDA | BioBERT |
|---------|----------|-----------|--------|-----|---------|
| OHSUMED | 45 | 3,000 | 0.0958 | 0.0832 | ⏳ |
| PML | 16 | 10,000 | **0.5580** | 0.5264 | ⏳ |
| PGB | 3 | 5,000 | 0.3324 | — | ⏳ |

### 初步结论

- TF-IDF 在所有数据集上一致优于 LDA，**PML 上差距最明显**（0.558 vs 0.526）
- OHSUMED 的 macro F1 普遍偏低（<0.1），标签空间高度稀疏（45 标签 × 多标签分类）
- PGB 的 TF-IDF 结果（0.3324）作为单-label 3 类分类参考
- BioBERT 结果待集群补充

## 如何复现

```bash
conda activate pubmed-tracker
python experiments/002_feature_compare/feature_compare.py
```

结果输出到 `results/feature_compare.csv`。
