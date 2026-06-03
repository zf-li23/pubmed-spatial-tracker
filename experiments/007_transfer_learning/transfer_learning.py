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

    X_src, y_src_raw = get_cached_features(src_ds, src_feat)
    y_src = y_src_raw.argmax(axis=1) if y_src_raw.ndim > 1 else y_src_raw

    # 提取 ST 测试集特征
    X_st, _ = get_cached_features(st_ds, src_feat)
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

    X_src, y_src_raw = get_cached_features(src_ds, src_feat)
    y_src = y_src_raw.argmax(axis=1) if y_src_raw.ndim > 1 else y_src_raw

    X_st, _ = get_cached_features(st_ds, src_feat)
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

    X, y_raw = get_cached_features(st_ds, "biobert")
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

    X, y_raw = get_cached_features(st_ds, "biobert")
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
    src_n_labels = y_src_raw.shape[1] if y_src_raw.ndim > 1 else len(set(y_src_raw.argmax(axis=1) if y_src_raw.ndim > 1 else y_src_raw))

    # ── 阶段 1: 源域预训练 ──
    print(f"    [pre-train] {src_ds.name} ({src_n_labels} labels)...")
    texts_src = src_ds.texts()
    y_src = y_src_raw.argmax(axis=1) if y_src_raw.ndim > 1 else y_src_raw

    # 对 OHSUMED 采样加速（1650 标签太慢）
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


def run_finetune_xgb(src_ds, st_ds, train_idx, test_idx, n_estimators_src=200,
                     n_estimators_tgt=100):
    """C3/C4: 源域 XGBoost → warm start on ST。

    策略：源域训练 → 保存模型 → 在 ST 上继续训练 (warm start)。
    """
    import tempfile
    from xgboost import XGBClassifier

    # ── 源域特征 ──
    X_src, y_src_raw = get_cached_features(src_ds, "biobert")
    y_src = y_src_raw.argmax(axis=1) if y_src_raw.ndim > 1 else y_src_raw

    # ── 阶段 1: 源域预训练 ──
    t0 = time.time()
    src_clf = XGBClassifier(n_estimators=n_estimators_src, random_state=42,
                            verbosity=0)
    src_clf.fit(X_src, y_src)
    pretrain_time = time.time() - t0

    # 保存到临时文件
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
    src_clf.save_model(tmp.name)

    # ── 阶段 2: ST warm start ──
    X_st, y_st_raw = get_cached_features(st_ds, "biobert")
    y_st = y_st_raw.argmax(axis=1)
    X_tr, X_te = X_st[train_idx], X_st[test_idx]
    y_tr, y_te = y_st[train_idx], y_st[test_idx]

    ft_t0 = time.time()
    tgt_clf = XGBClassifier(n_estimators=n_estimators_tgt, random_state=42,
                            verbosity=0)
    tgt_clf.fit(X_tr, y_tr, xgb_model=tmp.name)
    ft_time = time.time() - ft_t0

    y_pred = tgt_clf.predict(X_te)
    elapsed = time.time() - t0

    os.unlink(tmp.name)

    return {
        "f1_macro": round(f1_score(y_te, y_pred, average="macro"), 4),
        "accuracy": round(accuracy_score(y_te, y_pred), 4),
        "train_time_s": round(elapsed, 2),
        "pretrain_time_s": round(pretrain_time, 2),
        "finetune_time_s": round(ft_time, 2),
    }


# ═══════════════════════════════════════════════════════════════
# 主流程
# ═══════════════════════════════════════════════════════════════

EXPERIMENTS = {
    # ── A: Zero-shot ──
    "A1": lambda st, tr, vl, te: run_zero_shot_lr(
        load_dataset("ohsumed"), "biobert", st, te),
    "A2": lambda st, tr, vl, te: run_zero_shot_lr(
        load_dataset("pml"), "biobert", st, te),
    "A3": lambda st, tr, vl, te: run_zero_shot_xgb(
        load_dataset("ohsumed"), "biobert", st, te),
    "A4": lambda st, tr, vl, te: run_zero_shot_xgb(
        load_dataset("pml"), "biobert", st, te),
    "A5": lambda st, tr, vl, te: run_zero_shot_lr(
        load_dataset("pgb", build_graph=True), "biobert", st, te),

    # ── B: Baseline ──
    "B1": lambda st, tr, vl, te: run_baseline_lr(st, tr, te),
    "B2": lambda st, tr, vl, te: run_baseline_mlp(st, tr, te),
    "B3": lambda st, tr, vl, te: run_baseline_xgb(st, tr, te),

    # ── C: Pre-train → Fine-tune ──
    "C1": lambda st, tr, vl, te: run_finetune_mlp(
        load_dataset("pml"), st, tr, te),
    "C2": lambda st, tr, vl, te: run_finetune_mlp(
        load_dataset("ohsumed"), st, tr, te),
    "C3": lambda st, tr, vl, te: run_finetune_xgb(
        load_dataset("pml"), st, tr, te),
    "C4": lambda st, tr, vl, te: run_finetune_xgb(
        load_dataset("ohsumed"), st, tr, te),
}

EXPERIMENT_INFO = {
    "A1": "Zero-shot: OHSUMED → ST (BioBERT+LR)",
    "A2": "Zero-shot: PML → ST (BioBERT+LR)",
    "A3": "Zero-shot: OHSUMED → ST (BioBERT+XGBoost)",
    "A4": "Zero-shot: PML → ST (BioBERT+XGBoost)",
    "A5": "Zero-shot: PGB → ST (BioBERT+LR)",
    "B1": "Baseline: ST → ST (BioBERT+LR)",
    "B2": "Baseline: ST → ST (BioBERT+MLP) [GPU]",
    "B3": "Baseline: ST → ST (BioBERT+XGBoost)",
    "C1": "Fine-tune: PML pre-train → ST fine-tune (BioBERT+MLP) [GPU]",
    "C2": "Fine-tune: OHSUMED pre-train → ST fine-tune (BioBERT+MLP) [GPU]",
    "C3": "Fine-tune: PML pre-train → ST warm start (XGBoost)",
    "C4": "Fine-tune: OHSUMED pre-train → ST warm start (XGBoost)",
}


def save_results(results, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        if not results:
            f.write("exp_id,method,source,f1_macro,accuracy,train_time_s\n")
            return
        keys = results[0].keys()
        w = csv.DictWriter(f, fieldnames=keys)
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
