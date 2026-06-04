# Experiments

本目录存放项目中的 **7 组可复现实验**（共 **115 组子任务，98.3% 完成**）。
每个实验独立编号，包含完整代码、Slurm 提交脚本和结果。

## 规范

每个实验是一个独立子目录 `NNN_experiment_name/`，包含：

```
NNN_experiment_name/
├── {script}.py         # 实验代码（可独立运行）
├── run_cpu.slurm       # CPU Slurm 提交脚本
├── run_gpu.slurm       # GPU Slurm 提交脚本（如需）
└── results/            # 输出 CSV 结果
```

## 原则

1. **可复现** — `sbatch run_cpu.slurm` 在集群提交即复现全部结果
2. **自包含** — 实验脚本通过 `sys.path` 引用 `src/`；`_common.py` 提供统一工具函数
3. **缓存共享** — `_cache/` 存放预计算特征矩阵 (`dataset+feature` → `.npz`)，跨实验复用，避免重复计算
4. **集群运行** — 使用 Slurm (`pubmed-tracker` conda env) 执行 CPU/GPU 任务
5. **增量保存** — 长时实验支持断点续跑（读取已有 CSV，跳过已完成的组合）

## 完成状态

| 编号 | 名称 | 内容 | 组数 | 状态 | F1 最佳 |
|---|---|---|---|---|---|
| **000** | query_analysis | PubMed 检索式 7 变体对比 | 7 | ✅ 完成 | — |
| **001** | classical_matrix | 7 模型 × 4 特征 × 3 数据集 | **84** | ✅ **82/84** | 0.6710 (PML+BioBERT+LR) |
| **002** | biobert_mlp | BioBERT+MLP 端到端微调 × 3 数据集 | 3 | ✅ 完成 | 0.6411 (PML) |
| **003** | lda_cluster | LDA+KMeans 无监督聚类 × 3 数据集 | 3 | ✅ 完成 | NMI=0.44 (OHSUMED) |
| **004** | multilabel_strategy | BR / CC / LP 多标签策略 | 6 | ✅ 完成 | 0.5796 (PML+CC) |
| **005** | graph_models | Node2Vec / GCN / GraphSAGE on PGB | **9** | ✅ **8/9** | 0.4125 (GCN) |
| **006** | st_benchmark | ST 三方法基准测试 | 3 | ✅ 完成 | **0.8444** (BioBERT+MLP) |
| **007** | transfer_learning | 迁移微调（零样本/微调/图模型） | **13** | ✅ **11/13** | **0.9143** 🏆 (PML→ST MLP) |

> **总计：115 组实验，113 组完成（98.3%），2 组补跑中**

## 核心发现

- **BioBERT 嵌入 >> TF-IDF**: 特征表示的最优选择，PML 上 F1=0.6710
- **迁移微调增益显著**：PML 预训练 + ST 微调 F1=0.9143，比直接训练高 +9.6%
- **k-NN 图的 GCN/GraphSAGE** 在 ST 上 F1≈0.77，接近 LR 基线
- **零样本迁移**在不同标签空间上无效（F1≈0）

## 特征表示注册表

| Key | 类 | 维度 | 适用数据集 |
|---|---|---|---|
| `tfidf` | TFIDFExtractor | 5,000 | ohsumed, pml, pgb, st |
| `biobert` | BioBERTExtractor | 768 | ohsumed, pml, pgb, st |
| `lda` | LDAExtractor | 15 | ohsumed, pml, pgb, st |
| `meta` | MetaExtractor | 3–5 | ohsumed, pml, pgb, st |
| `node2vec` | Node2VecExtractor | 128 | pgb only |

## 缓存共享

`experiments/_cache/` 存放 `.npz` 特征矩阵。同一 `(dataset, feature)` 组合只提取一次，
跨实验复用。缓存键 = `{dataset}_{feature}_{md5(ds_kwargs)[:12]}`。

> ⚠ 历史教训：007 曾因 `ds_kwargs` 不匹配（`{}` vs `{"max_samples": null}`），
> 导致所有特征被重新计算，浪费 15h。后通过统一 `SOURCE_DS` 字典修复。
