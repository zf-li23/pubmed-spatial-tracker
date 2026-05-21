# 集群部署说明 — PubMed Spatial Tracker

## 集群拓扑

```
Internet
    │
    ▼
bio-download (101.6.122.79)    ← 跳板机，有网，用户 bio
    │ 192.168.1.1
    ▼
a-cluster (192.168.1.2)        ← 计算集群，无网络，用户 yangxr002
  ├── Home: /Share/home/yangxr002/
  │   └── zf-li23/             ← 你的工作目录
  └── Data: /data3/yangxr002/
```

## SSH 快捷方式（已配置在 `~/.bash_aliases`）

```bash
lab            # ssh a-cluster (登录到 home)
lab-work       # ssh a-cluster-work (直接到工作目录)
lab-push FILE  # 通过跳板机推送文件到集群工作目录
lab-pull FILE  # 从集群拉文件到本地
```

## 环境迁移步骤

### 1. 本地：创建独立 conda 环境

```bash
# 从 requirements.txt 创建新环境（不再与 zf-li23 混用）
conda create -n pubmed-tracker python=3.13 -y
conda activate pubmed-tracker
pip install -r requirements.txt
```

### 2. 本地：打包环境 + 缓存

```bash
# 确认路径
conda info --envs  # 找到 pubmed-tracker 的路径
# 通常为 ~/miniconda3/envs/pubmed-tracker/

# 打包 BioBERT 缓存
tar czf biobert_cache.tar.gz \
  -C ~/.cache/huggingface/hub \
  models--dmis-lab--biobert-base-cased-v1.1/
```

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
