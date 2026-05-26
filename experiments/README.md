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

1. **可复现** — `bash run.sh` 即复现全部结果，无需手动操作
2. **自包含** — 实验脚本可独立运行；若需要引用 `src/` 中的代码，通过 `sys.path` 或 `PYTHONPATH` 引入
3. **不提交产物** — `results/` 中的输出文件应加入 `.gitignore`（但保留 `results/.gitkeep` 使目录结构入仓）
4. **记录原始数据** — 关键中间结果（如检索 ID 列表、计数）保存为 CSV/JSON，供后续报告使用
5. **迭代编号** — 新实验按顺序编号 `NNN_`，避免冲突

## 实验清单

| 编号 | 名称 | 目的 | 状态 |
|---|---|---|---|
| 001 | query_analysis | PubMed 检索式设计 & 各字段对比 | ✅ 完成 |
| 002 | feature_compare | TF-IDF / BioBERT / LDA / Meta × 3 数据集（固定 LR） | 🔄 待运行 |
| 003 | algorithm_matrix | 7 模型 × TF-IDF / BioBERT / LDA × 3 数据集 | 🔄 待运行 |
| 004 | multilabel_strategy | BR / CC / LP 多标签策略对比 | 🔄 待运行 |
| 005 | graph_deep | Node2Vec + BioBERT-MLP（规划中） | ⬜ 规划中 |

## 特征表示注册表

| Key | 类 | 维度 | 适用数据集 |
|---|---|---|---|
| `tfidf` | TFIDFExtractor | 5,000 | 全部 4 个 |
| `biobert` | BioBERTExtractor | 768 | 全部 4 个 |
| `lda` | LDAExtractor | 15 | ohsumed, pml, pgb, st |
| `meta` | MetaExtractor | 3–5 | 全部 4 个 |
| `node2vec` | Node2VecExtractor | 128 | pgb only |

## 缓存

`_cache/` 存放预计算的特征矩阵（`.npz`）。同一 `(dataset, feature)` 组合只提取一次，跨实验复用。
