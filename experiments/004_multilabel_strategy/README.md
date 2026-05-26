# E1.3 — Multi-label Strategy

**目标**: 对比 Binary Relevance (BR)、Classifier Chain (CC)、Label Powerset (LP) 三种多标签策略在不同标签空间大小下的扩展能力。

## 实验矩阵

| 数据集 | 样本 | 标签数 | 策略 |
|---|---|---|---|
| OHSUMED | 10,000 | ~1,650 | BR, CC, LP |
| PML | 10,000 | 16 | BR, CC, LP |

- 特征: TF-IDF（固定）
- 模型: Logistic Regression（固定）
- CV: 5 折
- 总计: **2 × 3 = 6 组**

## 运行

```bash
# 本地
conda activate zf-li23
cd experiments/004_multilabel_strategy
python -u multilabel_strategy.py

# 集群
sbatch run_exp.slurm
```

## 预期结果

- 输出: `results/multilabel_strategy.csv`
- 小标签空间（PML, 16 labels）: BR ≈ LP > CC
- 大标签空间（OHSUMED, ~1.6K labels）: 所有策略表现均较低，CC 极慢
- 与 E1.1/E1.2 共享 TF-IDF 缓存

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
| PML (16 标签) | **0.5580** | ❌ 超时 | **0.5580** |

### 结论

1. **标签空间大小决定一切**——OHSUMED 上 1,650 标签太稀疏，三种策略均接近随机。
2. **PML 上 BR = LP**——16 标签时结果完全一致（0.5580），LP 的幂集编码无额外收益。
3. **CC 不稳定**——PML 上超时失败，链式依赖计算量过大。
4. **实践中优先用 BR**，简单可靠。标签空间 > 100 时需先降维。

## 如何复现

```bash
conda activate pubmed-tracker
python experiments/004_multilabel_strategy/multilabel_strategy.py
```

结果输出到 `results/multilabel_strategy.csv`。
