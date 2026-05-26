# E1.2 — Algorithm Matrix

**目标**: 系统比较 7 种经典/集成算法在所有数据集和特征表示上的分类性能。

## 实验矩阵

| 数据集 | 样本 | 标签数 | 特征 | 模型 |
|---|---|---|---|---|
| OHSUMED | 10,000 | ~1,650 | TF-IDF / BioBERT | NB, kNN, SVM, LR, RF, AdaBoost, XGBoost |
| PML | 10,000 | 16 | TF-IDF / BioBERT | NB, kNN, SVM, LR, RF, AdaBoost, XGBoost |
| PGB | 5,000 | 3 | TF-IDF / BioBERT | NB, kNN, SVM, LR, RF, AdaBoost, XGBoost |

- CV: 5 折
- 策略: Binary Relevance (OneVsRest)
- 总计: **3 × 2 × 7 = 42 组**

## 运行

```bash
# 本地
conda activate zf-li23
cd experiments/003_algorithm_matrix
python -u algorithm_matrix.py

# 集群
sbatch run_exp.slurm
```

## 预期结果

- 输出: `results/algorithm_matrix.csv`
- TF-IDF 部分本地跑 < 5 分钟
- BioBERT 部分首次需提取嵌入（~15 分钟，之后走缓存）
- 与 E1.1/E1.3 共享 `experiments/_cache/` 特征缓存

## 方法

| 维度 | 取值 |
|------|------|
| 特征 | TF-IDF (5K dim), BioBERT (仅 PML) |
| 模型 | NB, k-NN, SVM (RBF), LR, RF, AdaBoost, XGBoost |
| 数据集 | OHSUMED (10K 篇), PML (10K 篇), PGB (全量) |
| 评估 | 3 折 CV, macro F1 |
| 状态 | 🔄 **集群运行中**（12h 作业） |

## 结果

待集群作业完成后补充。

## 如何复现

```bash
conda activate pubmed-tracker
python experiments/003_algorithm_matrix/algorithm_matrix.py
```

结果输出到 `results/algorithm_matrix.csv`。
