# 003: 算法全矩阵 — 7 模型 × TF-IDF/BioBERT × 3 数据集

## 目的

固定文本表示（TF-IDF; BioBERT 仅在 PML 上运行），对 7 种分类算法进行排序。

## 方法

| 维度 | 取值 |
|------|------|
| 特征 | TF-IDF (5K dim), BioBERT (仅 PML) |
| 模型 | NB, k-NN, SVM (RBF), LR, RF, AdaBoost, XGBoost |
| 数据集 | OHSUMED (2K 篇), PML (10K 篇), PGB (2K 篇) |
| 评估 | 3 折 CV, macro F1 |

## 结果

待集群作业完成后补充。

## 如何复现

```bash
conda activate pubmed-tracker
python experiments/003_algorithm_matrix/algorithm_matrix.py
```

结果输出到 `results/algorithm_matrix.csv`。
