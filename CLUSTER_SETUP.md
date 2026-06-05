# 集群部署说明 — PubMed Spatial Tracker

> 最后更新: 2026-06-05 | 用于在 a-cluster 上复现全部实验

## 集群拓扑

```
Internet
    │
    ▼
bio-download (101.6.122.79)    ← 跳板机，有网
    │ 192.168.1.1
    ▼
a-cluster (192.168.1.2)        ← 计算集群，无网络
  ├── Home: /Share/home/yangxr002/
  │   └── zf-li23/pubmed-tracker/  ← 工作目录
  └── GPU: gpu01 (4×GPU, CUDA 12.2, 44GB VRAM)
```

## SSH 快捷方式

已在本地 `~/.ssh/config` 中配置：

```bash
# 直接登录计算节点
ssh -J bio-download yangxr002@192.168.1.2

# 快速同步代码
rsync -avz -e "ssh -J bio-download" experiments/ \
  yangxr002@192.168.1.2:/Share/home/yangxr002/zf-li23/pubmed-tracker/experiments/
```

---

## 双环境说明

本项目需要两个 conda 环境（因 GPU 驱动限制）：

| 环境 | Python | PyTorch | CUDA | 用途 |
|---|---|---|---|---|
| `pubmed-tracker` | 3.13 | 2.12.0 (CPU) | — | 所有 CPU 实验 (001-007 中 A/B/D 组) |
| `biobert_env` | 3.12 | 2.5.1+cu121 | 12.2 | GPU 实验 (002, 006 MLP, 007 C1/C2) |

---

## 集群环境部署

### 1. 创建 CPU 环境

```bash
# 本地打包环境
conda create -n pubmed-tracker python=3.13 -y
conda activate pubmed-tracker
pip install -r requirements.txt

# 传输到集群
rsync -avz -e "ssh -J bio-download" \
  ~/miniconda3/envs/pubmed-tracker/ \
  yangxr002@192.168.1.2:~/miniconda3/envs/pubmed-tracker/
```

### 2. 创建 GPU 环境

因集群 GPU 驱动为 CUDA 12.2，需要 Python 3.12 + PyTorch 2.5.1：

```bash
# 本地创建
conda create -n biobert_env python=3.12 -y
conda activate biobert_env
pip install torch==2.5.1+cu121 --index-url https://download.pytorch.org/whl/cu121
pip install -r requirements.txt

# 传输（注意：分批传输避免 .so 文件损坏）
# 推荐用 rsync 而非 tar
rsync -avz --progress -e "ssh -J bio-download" \
  ~/miniconda3/envs/biobert_env/ \
  yangxr002@192.168.1.2:~/miniconda3/envs/biobert_env/
```

### 3. 传输 BioBERT 模型缓存

```bash
# 本地打包
tar czf biobert_cache.tar.gz \
  -C ~/.cache/huggingface/hub \
  models--dmis-lab--biobert-base-cased-v1.1/

# 传输到集群
scp -o ProxyJump=bio-download biobert_cache.tar.gz \
  yangxr002@192.168.1.2:~/.cache/huggingface/hub/

# 在集群上解压
ssh -J bio-download yangxr002@192.168.1.2 \
  "cd ~/.cache/huggingface/hub && tar xzf biobert_cache.tar.gz"
```

### 4. 同步项目代码

```bash
# 首次：同步全部
rsync -avz -e "ssh -J bio-download" \
  --exclude='__pycache__' --exclude='*.pyc' \
  --exclude='.git' --exclude='data/ohsumed' \
  --exclude='data/PubMed-MultiLabel' --exclude='data/pgb' \
  ~/pubmed-spatial-tracker/ \
  yangxr002@192.168.1.2:/Share/home/yangxr002/zf-li23/pubmed-tracker/

# 增量：仅同步 experiments 和 src
rsync -avz -e "ssh -J bio-download" \
  experiments/ src/ requirements.txt \
  yangxr002@192.168.1.2:/Share/home/yangxr002/zf-li23/pubmed-tracker/
```

---

## 在集群上运行实验

### Slurm 提交（推荐）

所有实验统一使用 `run_exp.slurm` 脚本：

```bash
# CPU 任务
sbatch experiments/001_classical_matrix/run_exp.slurm
sbatch experiments/006_st_benchmark/run_exp.slurm

# GPU 任务
sbatch --gres=gpu:1 experiments/002_biobert_mlp/run_exp.slurm
sbatch --gres=gpu:1 experiments/006_st_benchmark/run_exp.slurm --methods biobert_mlp --out-suffix gpu
```

### 查看结果

```bash
# 检查实验进度
squeue -u yangxr002

# 查看输出日志
cat experiments/NNN_name/slurm_*.log

# 查看结果 CSV
cat experiments/NNN_name/results/*.csv
```

### 同步结果回本地

```bash
rsync -avz -e "ssh -J bio-download" \
  yangxr002@192.168.1.2:/Share/home/yangxr002/zf-li23/pubmed-tracker/experiments/NNN_name/results/ \
  experiments/NNN_name/results/
```

---

## 已知问题

| 问题 | 原因 | 解决 |
|---|---|---|
| `conda: command not found` | SSH 非交互式 shell | 在 Slurm 脚本中用 `source $HOME/miniconda3/etc/profile.d/conda.sh` |
| transformers 联网失败 | 集群无网络 | 设置 `local_files_only=True`，预下载模型缓存 |
| `tokenizer_config.json` 0 字节 | HF 缓存损坏 | 手动重建配置文件 |
| rsync .so 文件损坏 | 文件传输时被修改 | 分批传输，不要用 `tar` |

### 3. 传输到集群

```bash
# 创建集群工作目录
ssh -J bio-download a-cluster "mkdir -p ~/zf-li23/pubmed-tracker"

# 传输 conda 环境（~3GB，约 10 分钟）
rsync -avz -e "ssh -J bio-download" \
  ~/miniconda3/envs/pubmed-tracker/ \
  a-cluster:~/miniconda3/envs/pubmed-tracker/

# 传输项目代码
rsync -avz -e "ssh -J bio-download" \
  ~/pubmed-spatial-tracker/src/ \
  ~/pubmed-spatial-tracker/experiments/ \
  ~/pubmed-spatial-tracker/data/spatial_tracker/ \
  ~/pubmed-spatial-tracker/requirements.txt \
  a-cluster:~/zf-li23/pubmed-tracker/

# 传输 BioBERT 缓存
scp -o ProxyJump=bio-download biobert_cache.tar.gz \
  a-cluster:~/.cache/huggingface/hub/
ssh -J bio-download a-cluster "cd ~/.cache/huggingface/hub && tar xzf biobert_cache.tar.gz"
```

### 4. 在集群上运行实验

```bash
ssh -J bio-download a-cluster
cd ~/zf-li23/pubmed-tracker
PY=~/miniconda3/envs/pubmed-tracker/bin/python

# 运行实验（注意：用完整 Python 路径，不能用 conda activate）
$PY -u experiments/002_feature_compare/feature_compare.py
$PY -u experiments/003_algorithm_matrix/algorithm_matrix.py
$PY -u experiments/004_multilabel_strategy/multilabel_strategy.py
```

### 5. 同步代码更改

本地修改代码后，推送到集群：

```bash
rsync -avz -e "ssh -J bio-download" \
  ~/pubmed-spatial-tracker/src/ \
  ~/pubmed-spatial-tracker/experiments/ \
  a-cluster:~/zf-li23/pubmed-tracker/
```

### 环境迁移注意事项

- conda 环境有硬编码 shebang，**不要直接运行 pip 或脚本的 shebang**
- 始终用完整路径 `~/miniconda3/envs/pubmed-tracker/bin/python` 调用
- 如果依赖变化了 (`requirements.txt`)，需要重新传输整个环境
- 集群无网络，所有包必须通过本地 → 跳板机 → 集群传输
