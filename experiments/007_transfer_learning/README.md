# Exp 007: 迁移微调探索 (Transfer Learning)

> 对应 PLAN.md Step 3
> 目标：量化"源域预训练 + 目标域微调"的增益

---

## 实验设计

### 数据划分约定

```
Spatial Tracker (9,148 篇)
  ├── 训练集 (80%):  7,318 篇
  ├── 验证集 (10%):    915 篇
  └── 测试集 (10%):    915 篇  ← 固定此测试集评估所有实验
```

### 实验 A: Zero-shot 迁移（源域训练 → ST 直接测试）

在源域训练分类器，不做任何 ST 适配，直接在 ST 测试集上评估。

| 编号 | 源域 | 特征 | 分类器 | 预期 |
|---|---|---|---|---|
| A1 | OHSUMED (1,650 标签) | BioBERT 嵌入 (768d) | Logistic Regression | ~0.30-0.40 |
| A2 | PML (16 标签) | BioBERT 嵌入 (768d) | Logistic Regression | ~0.50-0.60 |
| A3 | OHSUMED | BioBERT 嵌入 | XGBoost | ~0.25-0.35 |
| A4 | PML | BioBERT 嵌入 | XGBoost | ~0.45-0.55 |
| A5 | PGB (3 类) | BioBERT 嵌入 | Logistic Regression | ~0.30-0.40 |

### 实验 B: 直接训练基线（ST 训练 → ST 测试）

在 ST 上标准训练，作为微调增益的参照基线。

| 编号 | 方法 | 预期 (参照 Exp 006) |
|---|---|---|
| B1 | BioBERT + LR (冻结嵌入) | F1 ≈ 0.8068 |
| B2 | BioBERT + MLP (端到端) | F1 ≈ 0.8444 |
| B3 | XGBoost on BioBERT 嵌入 | ~0.75-0.80 |

### 实验 C: 预训练 → 微调 → 测试

先在大规模源域上预训练，再在 ST 上微调，与 B 组对比增益。

| 编号 | 预训练域 | 算法 | 微调方式 | 预期增益 |
|---|---|---|---|---|
| C1 | PML | BioBERT+MLP | 替换分类头，全模型微调 | +1~3% |
| C2 | OHSUMED | BioBERT+MLP | 同上 | +0~2% |
| C3 | PML | XGBoost | warm start (`xgb_model`) | +1~2% |
| C4 | OHSUMED | XGBoost | warm start | +0~1% |

### 共计：13 组实验

---

## 实现方案

### BioBERT+MLP 迁移（C1, C2）

关键挑战：源域和目标域的标签数量不同。

```
预训练阶段:
  tuner = BioBERTFineTuner(n_labels=源域标签数, epochs=3)
  tuner.fit(source_texts, source_labels)
  torch.save(tuner.model.state_dict(), "pretrained.pth")

微调阶段:
  tuner = BioBERTFineTuner(n_labels=6, epochs=3)
  # 加载 BERT 权重，随机初始化分类头
  state = torch.load("pretrained.pth")
  # 保留 BERT 权重，丢弃旧的 classifier 权重
  tuner.model.bert.load_state_dict(
      {k.replace('bert.', ''): v 
       for k, v in state.items() if k.startswith('bert.')})
  tuner.fit(target_train_texts, target_train_labels)
  y_pred = tuner.predict(target_test_texts)
```

### XGBoost warm start（C3, C4）

```python
# 预训练
src_model = XGBClassifier(n_estimators=200)
src_model.fit(X_src, y_src)
src_model.save_model("xgb_pretrained.json")

# 微调
tgt_model = XGBClassifier(n_estimators=100)
tgt_model.fit(X_tgt, y_tgt, xgb_model="xgb_pretrained.json")
```

### GCN/GraphSAGE 迁移

PGB 的图结构无法直接迁移到 ST。替代方案：
- 构建 ST 文章的 k-NN 相似度图（基于 BioBERT 嵌入的余弦相似度）
- 在 k-NN 图上训练 GCN → 与 PGB 训练的 GCN 对比
- 此方案**不在 Step 3** 主计划中，作为探索性扩展

---

## 预期产出

1. **迁移增益热力图**：13 组实验的 F1 对比矩阵
2. **零样本 vs 微调 vs 直接训练**的系统比较
3. **源域规模 vs 迁移增益**关系分析
4. 哪些算法/表示适合迁移学习的结论

## 文件结构

```
experiments/007_transfer_learning/
├── README.md                 # 本计划
├── transfer_learning.py      # 主实验脚本
├── run_cpu.slurm             # CPU 提交脚本
├── run_gpu.slurm             # GPU 提交脚本（BioBERT+MLP）
└── results/                  # 输出目录
```
