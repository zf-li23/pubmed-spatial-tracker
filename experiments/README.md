# Experiments

本目录存放项目中的**可复现实验**。每个实验独立编号，包含完整代码、说明和结果。

## 规范

每个实验是一个独立子目录 `NNN_experiment_name/`，包含：

```
NNN_experiment_name/
├── README.md          # 实验目的、方法、结论
├── run.sh             # 一键运行脚本（bash ./run.sh 即复现）
├── {script}.py        # 实验代码
└── results/           # 输出结果存放处
```

## 原则

1. **可复现** — `sbatch run_exp.slurm` 在集群提交即复现全部结果
2. **自包含** — 实验脚本可独立运行；引用 `src/` 通过 `sys.path` 引入
3. **缓存共享** — `_cache/` 存放预计算特征矩阵，跨实验复用
4. **集群运行** — 所有实验用 Slurm 在集群执行，不本地跑
5. **迭代编号** — 新实验按顺序编号，000 为前期探索，001+ 为 Step 1

## 实验清单

| 编号 | 名称 | 目的 | 组数 | 状态 |
|---|---|---|---|---|
| 000 | query_analysis | PubMed 检索式设计 & 各字段对比 | 7 | ✅ 完成 |
| 001 | classical_matrix | 7 模型 × 4 特征 × 3 数据集 | 84 | 🔄 待运行 |
| 002 | biobert_mlp | BioBERT+MLP 端到端微调 | 3 | 🔄 待运行 |
| 003 | lda_cluster | LDA+KMeans 无监督聚类 | 3 | 🔄 待运行 |
| 004 | multilabel_strategy | BR / CC / LP 多标签策略 | 6 | 🔄 待运行 |
| 005 | graph_models | Node2Vec / GCN / GraphSAGE (PGB) | 3 | 🔄 待运行 |

## 特征表示注册表

| Key | 类 | 维度 | 适用数据集 |
|---|---|---|---|
| `tfidf` | TFIDFExtractor | 5,000 | ohsumed, pml, pgb, st |
| `biobert` | BioBERTExtractor | 768 | ohsumed, pml, pgb, st |
| `lda` | LDAExtractor | 15 | ohsumed, pml, pgb, st |
| `meta` | MetaExtractor | 3–5 | ohsumed, pml, pgb, st |
| `node2vec` | Node2VecExtractor | 128 | pgb only |

## 缓存

`_cache/` 存放 `.npz` 特征矩阵。同一 `(dataset, feature)` 组合只提取一次，跨实验复用。
