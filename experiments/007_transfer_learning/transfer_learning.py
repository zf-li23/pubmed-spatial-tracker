#!/usr/bin/env python3
"""Exp 007: Transfer Learning — 量化源域预训练→目标域微调的增益。

对应 PLAN.md Step 3，与 Exp 006 (ST 三方法基准) 紧密衔接。

数据划分（固定随机种子 42）:
  Spatial Tracker (9,148 篇)
    ├── 训练集 (80%): 7,318 篇
    ├── 验证集 (10%):   915 篇
    └── 测试集 (10%):   915 篇  ← 所有实验共用此测试集

实验分组:
  A (Zero-shot):  源域训练 → 直接测试 ST 测试集 (无 ST 数据参与训练)
  B (Baseline):   ST 训练 → ST 测试 (Exp 006 的对齐基线)
  C (Fine-tune):  源域预训练 → ST 微调 → ST 测试 (迁移增益)
  D (Graph):      k-NN 相似图 + GCN/GraphSAGE 在 ST 上的直接训练与 PGB→ST 迁移
"""

import argparse, csv, json, os, sys, time, warnings
from pathlib import Path

import numpy as np
from sklearn.metrics import f1_score, accuracy_score

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
warnings.filterwarnings("ignore")

HERE = Path(__file__).resolve().parent
REPO = HERE.parent.parent
sys.path.insert(0, str(REPO))

from experiments._common import load_dataset, get_cached_features, CACHE_DIR
from src.models.classical import MODELS as CLS_MODELS
from src.models.ensemble import MODELS as ENS_MODELS

# 源数据集参数 — 必须与 Exp 001 完全一致，否则缓存不命中 + 数据量暴增
SOURCE_DS = {
    "ohsumed": {"min_df": 10, "max_samples": 10000},
    "pml":     {},
    "pgb":     {"build_graph": False, "max_samples": 5000},
    "st":      {},
}
# 传递给 get_cached_features 的 ds_kwargs（与数据集加载参数相同）
def _ds_cache_kw(name):
    """返回数据集对应的缓存键 kwargs（需与 Exp 001 完全一致）。"""
    return dict(SOURCE_DS.get(name, {}))


# ═══════════════════════════════════════════════════════════════
# k-NN 相似图构建（基于 BioBERT 嵌入的余弦相似度）
# ═══════════════════════════════════════════════════════════════

def build_knn_graph(X, k=15, metric="cosine"):
    """从特征矩阵 X 构建 k-NN 相似图。

    返回 adjacency list（list of lists），每个元素是该节点的邻居索引列表。
    使用双向边（若 j 是 i 的 k-NN，则 i 也是 j 的 k-NN），确保图对称。
    """
    from sklearn.neighbors import NearestNeighbors

    n = X.shape[0]
    nn = NearestNeighbors(n_neighbors=min(k + 1, n), metric=metric)
    nn.fit(X)
    distances, indices = nn.kneighbors(X)

    adj = [set() for _ in range(n)]
    for i in range(n):
        for j in indices[i]:
            if i != j:
                adj[i].add(j)
                adj[j].add(i)
    # 保证每个节点至少有 1 个邻居
    adj = [sorted(s) if s else [j for j in range(n) if j != i][:1]
           for i, s in enumerate(adj)]
    return adj


def build_normalized_adj_torch(adj, n, device):
    """从 adjacency list 构建归一化的稀疏邻接矩阵 (PyTorch COO)。

    使用 GCN 论文中的对称归一化：A_norm = D^{-1/2} A D^{-1/2}
    """
    import torch
    from scipy import sparse as sp

    row, col, data = [], [], []
    for i, nbrs in enumerate(adj):
        deg_i = len(nbrs) if nbrs else 1
        for j in nbrs:
            row.append(i); col.append(j)
            deg_j = len(adj[j]) if adj[j] else 1
            data.append(1.0 / (deg_i * deg_j) ** 0.5)

    A = sp.csr_matrix((data, (row, col)), shape=(n, n))
    A = A + sp.eye(n)  # 自环
    A = A.tocoo()

    indices = torch.LongTensor([A.row, A.col])
    values = torch.FloatTensor(A.data)
    return torch.sparse_coo_tensor(indices, values, (n, n)).to(device)


# ═══════════════════════════════════════════════════════════════
# Data split — 固定划分，保证所有实验在同一个测试集上比较
# ═══════════════════════════════════════════════════════════════

def fixed_split(ds, train_ratio=0.8, val_ratio=0.1, seed=42):
    """返回 (train_idx, val_idx, test_idx) 的固定划分。"""
    rng = np.random.RandomState(seed)
    n = len(ds)
    perm = rng.permutation(n)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)
    return perm[:n_train], perm[n_train:n_train + n_val], perm[n_train + n_val:]


# ═══════════════════════════════════════════════════════════════
# 实验 A: Zero-shot 迁移
# ═══════════════════════════════════════════════════════════════

def run_zero_shot_lr(src_ds, src_feat, st_ds, st_test_idx, label_map_fn=None):
    """Zero-shot: 源域 BioBERT 嵌入 + LR → 直接预测 ST 测试集。"""
    from sklearn.linear_model import LogisticRegression

    kws = dict(SOURCE_DS.get(src_ds.name, {}))
    X_src, y_src_raw = get_cached_features(src_ds, src_feat, kws)
    y_src = y_src_raw.argmax(axis=1) if y_src_raw.ndim > 1 else y_src_raw

    # 提取 ST 测试集特征
    X_st, _ = get_cached_features(st_ds, src_feat, _ds_cache_kw("st"))
    X_te = X_st[st_test_idx]

    t0 = time.time()
    clf = LogisticRegression(max_iter=1000, random_state=42)
    clf.fit(X_src, y_src)
    elapsed = time.time() - t0

    # ST 测试集标签
    y_st = st_ds.labels().argmax(axis=1)
    y_te = y_st[st_test_idx]
    y_pred = clf.predict(X_te)

    return {
        "f1_macro": round(f1_score(y_te, y_pred, average="macro"), 4),
        "accuracy": round(accuracy_score(y_te, y_pred), 4),
        "train_time_s": round(elapsed, 2),
    }


def run_zero_shot_xgb(src_ds, src_feat, st_ds, st_test_idx):
    """Zero-shot: 源域 BioBERT 嵌入 + XGBoost → 直接预测 ST 测试集。"""
    from xgboost import XGBClassifier

    kws = dict(SOURCE_DS.get(src_ds.name, {}))
    X_src, y_src_raw = get_cached_features(src_ds, src_feat, kws)
    y_src = y_src_raw.argmax(axis=1) if y_src_raw.ndim > 1 else y_src_raw

    X_st, _ = get_cached_features(st_ds, src_feat, _ds_cache_kw("st"))
    X_te = X_st[st_test_idx]

    t0 = time.time()
    clf = XGBClassifier(n_estimators=200, random_state=42, verbosity=0)
    clf.fit(X_src, y_src)
    elapsed = time.time() - t0

    y_st = st_ds.labels().argmax(axis=1)
    y_te = y_st[st_test_idx]
    y_pred = clf.predict(X_te)

    return {
        "f1_macro": round(f1_score(y_te, y_pred, average="macro"), 4),
        "accuracy": round(accuracy_score(y_te, y_pred), 4),
        "train_time_s": round(elapsed, 2),
    }


# ═══════════════════════════════════════════════════════════════
# 实验 B: 直接训练基线
# ═══════════════════════════════════════════════════════════════

def run_baseline_lr(st_ds, train_idx, test_idx):
    """B1: BioBERT + LR (冻结嵌入) 在 ST 上训练测试。"""
    from sklearn.linear_model import LogisticRegression

    X, y_raw = get_cached_features(st_ds, "biobert", _ds_cache_kw("st"))
    y = y_raw.argmax(axis=1)
    X_tr, X_te = X[train_idx], X[test_idx]
    y_tr, y_te = y[train_idx], y[test_idx]

    t0 = time.time()
    clf = LogisticRegression(max_iter=1000, random_state=42)
    clf.fit(X_tr, y_tr)
    elapsed = time.time() - t0

    y_pred = clf.predict(X_te)
    return {
        "f1_macro": round(f1_score(y_te, y_pred, average="macro"), 4),
        "accuracy": round(accuracy_score(y_te, y_pred), 4),
        "train_time_s": round(elapsed, 2),
    }


def run_baseline_xgb(st_ds, train_idx, test_idx):
    """B3: XGBoost on BioBERT 嵌入在 ST 上训练测试。"""
    from xgboost import XGBClassifier

    X, y_raw = get_cached_features(st_ds, "biobert", _ds_cache_kw("st"))
    y = y_raw.argmax(axis=1)
    X_tr, X_te = X[train_idx], X[test_idx]
    y_tr, y_te = y[train_idx], y[test_idx]

    t0 = time.time()
    clf = XGBClassifier(n_estimators=200, random_state=42, verbosity=0)
    clf.fit(X_tr, y_tr)
    elapsed = time.time() - t0

    y_pred = clf.predict(X_te)
    return {
        "f1_macro": round(f1_score(y_te, y_pred, average="macro"), 4),
        "accuracy": round(accuracy_score(y_te, y_pred), 4),
        "train_time_s": round(elapsed, 2),
    }


def run_baseline_mlp(st_ds, train_idx, test_idx):
    """B2: BioBERT + MLP 端到端微调 (需要 GPU)。"""
    from src.models.deep import BioBERTFineTuner

    texts = st_ds.texts()
    y = st_ds.labels().argmax(axis=1)
    texts_tr = [texts[i] for i in train_idx]
    texts_te = [texts[i] for i in test_idx]
    y_tr, y_te = y[train_idx], y[test_idx]

    t0 = time.time()
    tuner = BioBERTFineTuner(n_labels=6, epochs=3, batch_size=16,
                             multilabel=False)
    tuner.fit(texts_tr, y_tr)
    elapsed = time.time() - t0

    y_pred = tuner.predict(texts_te)
    return {
        "f1_macro": round(f1_score(y_te, y_pred, average="macro"), 4),
        "accuracy": round(accuracy_score(y_te, y_pred), 4),
        "train_time_s": round(elapsed, 2),
    }


# ═══════════════════════════════════════════════════════════════
# 实验 C: 预训练 → 微调
# ═══════════════════════════════════════════════════════════════

def run_finetune_mlp(src_ds, st_ds, train_idx, test_idx):
    """C1/C2: 源域预训练 BioBERT+MLP → ST 微调 → ST 测试。

    策略：保存源域预训练的 BERT 权重，替换分类头（源域 n_labels → 6），
          在 ST 训练集上微调整个模型。
    """
    import torch
    from src.models.deep import BioBERTFineTuner, BioBERTMLP

    # ── 确定源域标签数 ──
    y_src_raw = src_ds.labels()
    src_n_labels = y_src_raw.shape[1] if y_src_raw.ndim > 1 else len(
        set(np.argmax(y_src_raw, axis=1) if y_src_raw.ndim > 1 else y_src_raw))

    # ── 阶段 1: 源域预训练 ──
    print(f"    [pre-train] {src_ds.name} ({src_n_labels} labels)...")
    texts_src = src_ds.texts()

    # 将标签转为 1D 类索引（argmax 在稀疏矩阵上可能返回 2D）
    if y_src_raw.ndim > 1:
        y_src = np.ravel(np.asarray(y_src_raw.argmax(axis=1)))
    else:
        y_src = y_src_raw.copy()

    # 对超大源域采样加速
    if len(texts_src) > 5000 and src_n_labels > 100:
        rng = np.random.RandomState(42)
        idx = rng.choice(len(texts_src), 5000, replace=False)
        texts_src = [texts_src[i] for i in idx]
        y_src = y_src[idx]

    t0 = time.time()
    src_tuner = BioBERTFineTuner(n_labels=src_n_labels, epochs=2, batch_size=16,
                                 multilabel=False)
    src_tuner.fit(texts_src, y_src)
    pretrain_time = time.time() - t0
    print(f"      done in {pretrain_time:.1f}s")

    # ── 保存预训练 BERT 权重 ──
    state = src_tuner.model.state_dict()
    bert_keys = {k for k in state if k.startswith("bert.")}
    bert_state = {k: state[k] for k in bert_keys}
    # 丢弃旧的分类头

    # ── 阶段 2: ST 微调 ──
    print(f"    [fine-tune] on ST ({6} labels)...")
    texts_st = st_ds.texts()
    y_st = st_ds.labels().argmax(axis=1)
    texts_tr = [texts_st[i] for i in train_idx]
    texts_te = [texts_st[i] for i in test_idx]
    y_tr, y_te = y_st[train_idx], y_st[test_idx]

    ft_tuner = BioBERTFineTuner(n_labels=6, epochs=3, batch_size=16,
                                multilabel=False)
    # 加载预训练的 BERT 权重
    ft_tuner.model.bert.load_state_dict(
        {k.replace("bert.", ""): v for k, v in bert_state.items()})
    # 分类头保持随机初始化（6 labels）

    ft_t0 = time.time()
    ft_tuner.fit(texts_tr, y_tr)
    ft_time = time.time() - ft_t0

    y_pred = ft_tuner.predict(texts_te)
    elapsed = time.time() - t0

    return {
        "f1_macro": round(f1_score(y_te, y_pred, average="macro"), 4),
        "accuracy": round(accuracy_score(y_te, y_pred), 4),
        "train_time_s": round(elapsed, 2),
        "pretrain_time_s": round(pretrain_time, 2),
        "finetune_time_s": round(ft_time, 2),
    }


# ═══════════════════════════════════════════════════════════════
# 实验 D: k-NN 相似图 + GCN/GraphSAGE
# ═══════════════════════════════════════════════════════════════

def _run_gcn_on_split(X, adj, y_labels, train_idx, test_idx,
                       hidden_dim=64, epochs=200, lr=0.01,
                       device=None):
    """内部函数：在给定划分上训练 GCN 并返回 F1 / Acc。"""
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    n = X.shape[0]
    n_classes = len(set(y_labels))
    in_dim = X.shape[1]

    A_torch = build_normalized_adj_torch(adj, n, device)
    X_t = torch.FloatTensor(X).to(device)
    y_t = torch.LongTensor(y_labels).to(device)

    class _GCN(nn.Module):
        def __init__(self, d_in, d_hid, d_out):
            super().__init__()
            self.conv1 = nn.Linear(d_in, d_hid)
            self.conv2 = nn.Linear(d_hid, d_out)
        def forward(self, x, a):
            x = F.relu(self.conv1(torch.spmm(a, x)))
            return self.conv2(torch.spmm(a, x))

    model = _GCN(in_dim, hidden_dim, n_classes).to(device)
    opt = optim.Adam(model.parameters(), lr=lr)

    for ep in range(epochs):
        model.train()
        opt.zero_grad()
        out = model(X_t, A_torch)
        loss = F.cross_entropy(out[train_idx], y_t[train_idx])
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        logits = model(X_t, A_torch)
        pred = logits[test_idx].argmax(dim=1).cpu().numpy()
    true = y_labels[test_idx]
    return {
        "f1_macro": float(f1_score(true, pred, average="macro", zero_division=0)),
        "accuracy": float(accuracy_score(true, pred)),
    }


def _run_graphsage_on_split(X, adj, y_labels, train_idx, test_idx,
                             hidden_dim=64, epochs=200, lr=0.01,
                             device=None):
    """内部函数：在给定划分上训练 GraphSAGE 并返回 F1 / Acc。

    使用稀疏矩阵运算优化的 mean aggregator，避免 Python 循环。
    """
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    import torch.optim as optim

    if device is None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    n = X.shape[0]
    n_classes = len(set(y_labels))
    in_dim = X.shape[1]

    A_torch = build_normalized_adj_torch(adj, n, device)
    X_t = torch.FloatTensor(X).to(device)
    y_t = torch.LongTensor(y_labels).to(device)

    class _GraphSAGE(nn.Module):
        """2-layer GraphSAGE 使用 sparse spmm 加速聚合。"""
        def __init__(self, d_in, d_hid, d_out):
            super().__init__()
            self.w_self = nn.Linear(d_in, d_hid)
            self.w_neigh = nn.Linear(d_in, d_hid)
            self.out = nn.Linear(d_hid, d_out)

        def forward(self, x, a):
            # Mean aggregation via spmm: a @ x gives deg-weighted sum
            deg = torch.sparse.sum(a, dim=1).to_dense().unsqueeze(1)  # (n,1)
            deg[deg == 0] = 1
            x_neigh = torch.spmm(a, x) / deg
            h = F.relu(self.w_self(x) + self.w_neigh(x_neigh))
            return self.out(h)

    model = _GraphSAGE(in_dim, hidden_dim, n_classes).to(device)
    opt = optim.Adam(model.parameters(), lr=lr)

    for ep in range(epochs):
        model.train()
        opt.zero_grad()
        out = model(X_t, A_torch)
        loss = F.cross_entropy(out[train_idx], y_t[train_idx])
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        logits = model(X_t, A_torch)
        pred = logits[test_idx].argmax(dim=1).cpu().numpy()
    true = y_labels[test_idx]
    return {
        "f1_macro": float(f1_score(true, pred, average="macro", zero_division=0)),
        "accuracy": float(accuracy_score(true, pred)),
    }


def run_gcn_st(st_ds, train_idx, test_idx):
    """D1: GCN on ST k-NN similarity graph (direct training)."""
    from sklearn.preprocessing import StandardScaler

    X, _ = get_cached_features(st_ds, "biobert", _ds_cache_kw("st"))
    X = StandardScaler().fit_transform(X)

    t0 = time.time()
    adj = build_knn_graph(X, k=15)
    print(f"    k-NN graph built: {sum(len(a) for a in adj)//2} edges")

    y = st_ds.labels().argmax(axis=1)
    res = _run_gcn_on_split(X, adj, y, train_idx, test_idx)
    elapsed = time.time() - t0
    res["train_time_s"] = round(elapsed, 2)
    return res


def run_graphsage_st(st_ds, train_idx, test_idx):
    """D2: GraphSAGE on ST k-NN similarity graph (direct training)."""
    from sklearn.preprocessing import StandardScaler

    X, _ = get_cached_features(st_ds, "biobert", _ds_cache_kw("st"))
    X = StandardScaler().fit_transform(X)

    t0 = time.time()
    adj = build_knn_graph(X, k=15)
    print(f"    k-NN graph built: {sum(len(a) for a in adj)//2} edges")

    y = st_ds.labels().argmax(axis=1)
    res = _run_graphsage_on_split(X, adj, y, train_idx, test_idx)
    elapsed = time.time() - t0
    res["train_time_s"] = round(elapsed, 2)
    return res



# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

EXPERIMENTS = {
    # ── A: Zero-shot (源域→ST, 标签空间不同时 F1≈0 是预期的) ──
    "A1": lambda st, tr, vl, te: run_zero_shot_lr(
        load_dataset("ohsumed", **SOURCE_DS["ohsumed"]), "biobert", st, te),
    "A2": lambda st, tr, vl, te: run_zero_shot_lr(
        load_dataset("pml", **SOURCE_DS["pml"]), "biobert", st, te),
    "A4": lambda st, tr, vl, te: run_zero_shot_xgb(
        load_dataset("pml", **SOURCE_DS["pml"]), "biobert", st, te),
    "A5": lambda st, tr, vl, te: run_zero_shot_lr(
        load_dataset("pgb", **SOURCE_DS["pgb"]), "biobert", st, te),

    # ── B: Baseline ──
    "B1": lambda st, tr, vl, te: run_baseline_lr(st, tr, te),
    "B2": lambda st, tr, vl, te: run_baseline_mlp(st, tr, te),
    "B3": lambda st, tr, vl, te: run_baseline_xgb(st, tr, te),

    # ── C: Pre-train → Fine-tune ──
    "C1": lambda st, tr, vl, te: run_finetune_mlp(
        load_dataset("pml", **SOURCE_DS["pml"]), st, tr, te),
    "C2": lambda st, tr, vl, te: run_finetune_mlp(
        load_dataset("ohsumed", **SOURCE_DS["ohsumed"]), st, tr, te),

    # ── D: Graph on ST k-NN similarity graph ──
    "D1": lambda st, tr, vl, te: run_gcn_st(st, tr, te),
    "D2": lambda st, tr, vl, te: run_graphsage_st(st, tr, te),
}

EXPERIMENT_INFO = {
    "A1": "Zero-shot: OHSUMED → ST (BioBERT+LR, 1650→6标签, F1≈0预期)",
    "A2": "Zero-shot: PML → ST (BioBERT+LR, 14→6标签, F1≈0预期)",
    "A4": "Zero-shot: PML → ST (BioBERT+XGBoost, 14→6标签, F1≈0预期)",
    "A5": "Zero-shot: PGB → ST (BioBERT+LR, 3→6标签, F1≈0预期)",
    "B1": "Baseline: ST → ST (BioBERT+LR)",
    "B2": "Baseline: ST → ST (BioBERT+MLP) [GPU]",
    "B3": "Baseline: ST → ST (BioBERT+XGBoost)",
    "C1": "Fine-tune: PML pre-train → ST fine-tune (BioBERT+MLP) [GPU]",
    "C2": "Fine-tune: OHSUMED pre-train → ST fine-tune (BioBERT+MLP) [GPU]",
    "D1": "Graph: GCN on ST k-NN similarity graph",
    "D2": "Graph: GraphSAGE on ST k-NN similarity graph",
}


def save_results(results, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        if not results:
            f.write("exp_id,method,source,f1_macro,accuracy,train_time_s\n")
            return
        # 合并所有结果的字段名（不同实验可能返回不同键）
        all_keys = set()
        for r in results:
            all_keys.update(r.keys())
        # 保持 exp_id, method, f1_macro, accuracy, train_time_s 在开头
        priority = ["exp_id", "method", "f1_macro", "accuracy", "train_time_s"]
        ordered = priority + sorted(k for k in all_keys if k not in priority)
        w = csv.DictWriter(f, fieldnames=ordered)
        w.writeheader()
        w.writerows(results)
    print(f"  → saved {len(results)} rows to {path}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description="007 — Transfer Learning")
    p.add_argument("--exps", type=str, default="all",
                   help="Comma-separated experiment IDs (e.g. A1,B1,C1)")
    p.add_argument("--out-suffix", type=str, default=None)
    args = p.parse_args()

    # 选择实验
    if args.exps == "all":
        exp_ids = sorted(EXPERIMENTS.keys())
    else:
        exp_ids = [e.strip() for e in args.exps.split(",")]

    # 输出文件
    OUT = HERE / "results"
    OUT.mkdir(parents=True, exist_ok=True)
    suffix = f"_{args.out_suffix}" if args.out_suffix else ""
    out_path = OUT / f"transfer_learning{suffix}.csv"

    # 加载 ST + 固定划分
    print("007 — Transfer Learning")
    print(f"  experiments: {exp_ids}")
    print()
    st_ds = load_dataset("st")
    train_idx, val_idx, test_idx = fixed_split(st_ds)
    print(f"ST: {len(st_ds)} docs → train {len(train_idx)}, "
          f"val {len(val_idx)}, test {len(test_idx)}")
    print(f"  Label distribution (test set):")
    y_st = st_ds.labels().argmax(axis=1)
    for i, name in enumerate(st_ds.label_names):
        print(f"    {name}: {(y_st[test_idx] == i).sum()}")

    results = []
    for exp_id in exp_ids:
        if exp_id not in EXPERIMENTS:
            print(f"  ⚠ Unknown experiment: {exp_id}, skipping.")
            continue

        info = EXPERIMENT_INFO[exp_id]
        print(f"\n{'='*50}")
        print(f"  {exp_id}: {info}")
        print(f"{'='*50}")
        try:
            res = EXPERIMENTS[exp_id](st_ds, train_idx, val_idx, test_idx)
            res["exp_id"] = exp_id
            res["method"] = info
            f1 = res.get("f1_macro", 0)
            acc = res.get("accuracy", 0)
            tm = res.get("train_time_s", 0)
            print(f"  f1_macro={f1:.4f}  accuracy={acc:.4f}  time={tm:.1f}s")
            if "pretrain_time_s" in res:
                print(f"    (pre-train {res['pretrain_time_s']:.1f}s + "
                      f"fine-tune {res['finetune_time_s']:.1f}s)")
            results.append(res)
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback; traceback.print_exc()

    save_results(results, out_path)
    print(f"\n✅ 007 done — {len(results)}/{len(exp_ids)} results → {out_path}")
