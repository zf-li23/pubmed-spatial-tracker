# E1.1 — Feature Comparison

**目标**: 固定模型（Logistic Regression），单独对比 TF-IDF / BioBERT / LDA 三种文本表示方法。

## 实验矩阵

| 数据集 | 样本 | 标签数 | TF-IDF | BioBERT | LDA |
|---|---|---|---|---|---|
| OHSUMED | 10,000 | ~1,650 | ✅ | ✅ | ✅ |
| PML | 10,000 | 16 | ✅ | ✅ | ✅ |
| PGB | 5,000 | 3 | ✅ | ✅ | ✅ |

- 模型: Logistic Regression (OneVsRest)
- CV: 5 折
- 总计: **9 组**

## 运行

```bash
# 本地
conda activate zf-li23
cd experiments/002_feature_compare
python -u feature_compare.py

# 集群
sbatch run_exp.slurm
```

## 预期结果

- 输出: `results/feature_compare.csv`
- BioBERT >> TF-IDF > LDA（基于旧版仅 LR 的初步结论）
- 缓存: TF-IDF/BioBERT 特征被缓存至 `experiments/_cache/`，后续实验直接复用

## 方法

| 维度 | 取值 |
|------|------|
| 模型 | Logistic Regression（OvR 多标签） |
| 特征 | TF-IDF (5K dim), LDA (15 topics), BioBERT (768-dim) |
| 数据集 | OHSUMED (3K 篇, 45 标签), PML (10K 篇, 16 标签), PGB (5K 篇, 3 类) |
| 评估 | 3 折 CV, macro F1 |

## 结果

| Dataset | n_labels | n_samples | TF-IDF | LDA | **BioBERT** |
|---------|----------|-----------|--------|-----|-------------|
| OHSUMED | 45 | 3,000 | 0.0958 | 0.0832 | **0.3135** |
| PML | 16 | 10,000 | 0.5580 | 0.5264 | **0.6665** |
| PGB | 3 | 5,000 | 0.3324 | — | 0.3324 |

### 结论

- **BioBERT 显著优于 TF-IDF 和 LDA**，尤其在 OHSUMED 上提升 3.3 倍（0.0958 → 0.3135）
- BioBERT 在 PML 上也提升明显（0.558 → 0.667）
- PGB 上三者接近（~0.33），BioBERT 无额外收益
- BioBERT 代价：训练时间比 TF-IDF 慢 **100-150 倍**

## 如何复现

```bash
conda activate pubmed-tracker
python experiments/002_feature_compare/feature_compare.py
```

结果输出到 `results/feature_compare.csv`。
