# Experiments

本目录存放项目中的 **7 组可复现实验**（共 **115 组子任务，98.3% 完成**）。

## 规范

每个实验是一个独立子目录 `NNN_experiment_name/`，包含：

```
NNN_experiment_name/
├── {script}.py          # 实验代码
├── run.sh               # 本地复现（小规模子集）
├── run_exp.slurm        # Slurm 集群提交（完整复现）
└── results/             # 输出 CSV 结果
```

## 复现方式

### 本地（不计成本，验证用）

```bash
# 确保 conda 环境已激活
conda activate pubmed-tracker

# 运行单个实验的快速子集
bash experiments/001_classical_matrix/run.sh    # 1 数据集 × 1 特征 × 1 模型
bash experiments/006_st_benchmark/run.sh        # 仅 TF-IDF+SVM
bash experiments/007_transfer_learning/run.sh   # 仅 B1 基线
```

### 集群（Slurm，完整复现）

```bash
# CPU 任务
sbatch experiments/001_classical_matrix/run_exp.slurm
sbatch experiments/006_st_benchmark/run_exp.slurm
sbatch experiments/007_transfer_learning/run_exp.slurm

# GPU 任务（需要 --gres=gpu:1）
sbatch --gres=gpu:1 experiments/002_biobert_mlp/run_exp.slurm
sbatch --gres=gpu:1 experiments/006_st_benchmark/run_exp.slurm --methods biobert_mlp --out-suffix gpu
sbatch --gres=gpu:1 experiments/007_transfer_learning/run_exp.slurm --exps B2,C1,C2 --out-suffix gpu
```

## 原则

1. **本地快速** — `bash run.sh` 跑小规模子集，验证代码正确性
2. **集群完整** — `sbatch run_exp.slurm` 复现全部结果
3. **CPU/GPU 分离** — GPU 任务通过 `--gres=gpu:1` 和 `--out-suffix` 区分输出文件
4. **缓存共享** — `_cache/` 存放预计算特征矩阵，跨实验复用

## 环境说明

本项目需要两个 conda 环境（因 GPU 驱动限制）：

| 环境 | Python | PyTorch | 用途 |
|---|---|---|---|
| `pubmed-tracker` | 3.13 | CPU 版 | 所有 CPU 实验 |
| `biobert_env` | 3.12 | 2.5.1+cu121 | GPU 实验（BioBERT+MLP 微调） |

依赖见项目根目录的 `requirements.txt` 和 `environment.yml`。

## 查看结果

```bash
# 检查 Slurm 队列
squeue -u $USER

# 查看实验输出
cat experiments/NNN_name/slurm-*.out

# 查看结果 CSV
cat experiments/NNN_name/results/*.csv
```

## 已知问题

| 问题 | 原因 | 解决 |
|---|---|---|
| `conda: command not found` | SSH 非交互式 shell | 在 Slurm 脚本中用 `source \$HOME/miniconda3/etc/profile.d/conda.sh` |
| transformers 联网失败 | 集群无网络 | 设置 `local_files_only=True`，预下载模型缓存 |
| `tokenizer_config.json` 0 字节 | HF 缓存损坏 | 手动重建配置文件 |
| rsync .so 文件损坏 | 文件传输时被修改 | 分批传输，不要用 tar |
5. **增量保存** — `save_results()` 合并写入已有 CSV，支持断点续跑

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
