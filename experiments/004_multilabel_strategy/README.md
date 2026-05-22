# 004: 多标签策略对比 — BR / CC / LP

## 目的

比较三种多标签转换策略在多标签文献分类上的效果。

## 方法

| 维度 | 取值 |
|------|------|
| 模型 | Logistic Regression |
| 特征 | TF-IDF (5K dim) |
| 策略 | Binary Relevance (BR), Classifier Chain (CC), Label Powerset (LP) |
| 数据集 | OHSUMED (10K 篇, 1,650 标签), PML (10K 篇, 16 标签) |
| 评估 | 3 折 CV, macro F1 |

## 结果

| Dataset | BR | CC | LP |
|---------|----|----|----|
| OHSUMED (1,650 标签) | 0.0062 | 0.0077 | 0.0062 |
| PML (16 标签) | **0.5580** | ❌ | **0.5580** |

### 分析

- **OHSUMED** 上所有策略表现接近随机（F1 ≈ 0.006），原因是标签空间过大（1,650 标签）且标签稀疏——这是多标签分类的极端困难场景
- **PML** 上 BR 和 LP 完全一致（0.5580），说明在 16 标签的粗粒度分类中，标签组合的幂集没有额外收益
- **CC** 在 PML 上失败（超时/内存），说明链式依赖在大标签空间下计算开销过大

## 如何复现

```bash
conda activate pubmed-tracker
python experiments/004_multilabel_strategy/multilabel_strategy.py
```

结果输出到 `results/multilabel_strategy.csv`。
