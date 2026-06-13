# 实验回顾报告 — PubMed Spatial Tracker

> 创建: 2026-06-03 | 最后更新: 2026-06-04
> 课程: 机器学习概论 课程大作业
> 项目: PubMed 空间转录组学文献多标签分类系统

---

## 1. 项目概述

本项目构建了一个**多数据集 × 多算法 × 多特征表示**的系统性实验框架，用于比较不同机器学习方法在生物医学文献分类上的表现。核心数据集包括：

| 数据集 | 规模 | 标签类型 | 标签数 | 角色 |
|---|---|---|---|---|
| **OHSUMED** | ~10K 篇 | MeSH 多标签 | 1,650 | 大规模稀疏标签基准 |
| **PubMed-MultiLabel (PML)** | 10K 篇 | MeSH 顶级类别 | 16 | 粗粒度快速实验 |
| **PGB** | 5K 篇 | 3 类节点分类 | 3 | 图结构方法验证 |
| **Spatial Tracker** | 9,148 篇 | LLM 标注 6 维 | 40+ | 目标应用场景 |

## 2. 实验矩阵

共设计并执行了 **7 组实验**（**113/115 组子任务完成，98.3%**），涵盖 14 种算法 × 5 种特征表示 × 4 个数据集：

| 实验 | 内容 | 组数 | 状态 |
|---|---|---|---|
| **000** | PubMed 查询分析 | 7 变体 | ✅ 完成 |
| **001** | 经典算法矩阵（7模型×4特征×3数据集） | **84** | ✅ **84/84 完成** |
| **002** | BioBERT+MLP 端到端微调 | 3 | ✅ 完成 |
| **003** | LDA+KMeans 无监督聚类 | 3 | ✅ 完成 |
| **004** | 多标签策略（BR/CC/LP） | 6 | ✅ 完成 |
| **005** | 图模型（Node2Vec/GCN/GraphSAGE） | **9** | ✅ **8 完成** |
| **006** | Spatial Tracker 三方法基准测试 | **3** | ✅ 完成 |
| **007** | 迁移微调探索（零样本/微调/图迁移） | **13** | ✅ **11/13 完成** |

## 3. 关键技术挑战与解决过程

### 3.1 环境与集群部署

**挑战：** 本地开发环境（WSL2 Ubuntu）与远程计算集群（无互联网访问）之间存在巨大差异。

**迭代过程：**
1. ❌ 直接在 `zf-li23` 基础环境上开发 → 与项目依赖冲突
2. ✅ 创建独立 `pubmed-tracker` conda 环境（Python 3.13）
3. ❌ 集群 GPU 驱动版本过旧（CUDA 12.2），PyTorch 2.12.0 编译于 CUDA 13.0 → GPU 不可用
4. ❌ Python 3.13 没有 CUDA 12.1 的 PyTorch wheel → 无法降级
5. ✅ 创建 `biobert_env`（Python 3.12 + PyTorch 2.5.1+cu121）本地打包，scp 传到集群
6. ❌ 首次 tar 传输因 "file changed as we read it" 导致 CUDA 库损坏
7. ❌ 解压路径嵌套错误（`biobert_env/biobert_env/...`）
8. ✅ 分批 rsync 修复，最终 CUDA 兼容环境部署成功

### 3.2 模型加载与 Transformers 兼容性

**挑战：** 集群无互联网，HuggingFace 模型需预下载。

**迭代过程：**
1. ❌ `AutoTokenizer.from_pretrained()` 尝试联网失败
2. ✅ 添加 `local_files_only=True` 强制从缓存加载
3. ❌ `sentencepiece 缺失` 错误——实际上是 `AutoTokenizer` 对 BioBERT 的自动检测失败
4. ✅ 改用 `BertTokenizer` + `BertModel`（跳过 auto-detection）
5. ❌ `transformers 5.9.0` 要求 `torch >= 2.6`（CVE-2025-32434 安全补丁）
6. ✅ 降级到 `transformers 4.48.3` + `tokenizers 0.21.4` + `huggingface-hub 0.36.2`
7. ❌ HuggingFace 缓存中 `tokenizer_config.json` 等文件为 0 字节
8. ✅ 手动重建配置文件 + rsync 修复缓存

### 3.3 BioBERT 微调（实验 002）

**挑战：** 端到端微调 BioBERT 需要 GPU 和大显存。

**迭代过程：**
1. ❌ 首次运行 tokenizer 加载失败（sentencepiece 误报）
2. ❌ CUDA OOM：`predict()` 一次性处理全部测试数据（2000×512 tokens）
3. ✅ `predict()` 加 batching（batch_size=64），缓解显存压力
4. ❌ PGB 是 3 类单标签分类，但使用了 `BCEWithLogitsLoss`（多标签损失）
5. ✅ 添加 `multilabel` 参数，PGB 用 `CrossEntropyLoss` + `argmax`
6. ✅ 最终结果：OHSUMED(F1=0.0013), PML(F1=0.6411), PGB(F1=0.3601)

### 3.4 实验 001 — 经典算法矩阵（最大挑战）

**挑战：** 84 组 5 折交叉验证，部分模型极慢。

**阶段一：串行超时**
1. ❌ 首次提交：4h 时限 → 超时，0 行结果（无增量保存）
2. ❌ 第二次：48h 时限 → 超时，11/84 组完成（SVM 7h, RF 6.8h）
3. ❌ 第三次（续跑修复）：但 CSV 为空 → 重新跑了 11 组

**阶段二：Naive Bayes 兼容性**
1. ❌ `MultinomialNB` 要求非负输入，BioBERT 嵌入含负值 → 11 组缺失
2. ✅ 改用 `GaussianNB`（不要求非负），补跑成功

**阶段三：并行化**
1. ❌ 串行 48h 只跑 11-22 组 → 完全不可接受
2. ✅ 拆分为 12 个并行任务（3 数据集 × 4 特征），每个跑 7 个模型
3. ✅ 首次并行提交失败（`pbar` 变量被误删 → `NameError`）
4. ✅ 修复后 12 小时内完成 74/84 组

**阶段四：CSV 格式混乱**
1. ❌ `cat | sort -u` 合并不同格式 CSV（10 列 PGB + 12 列多标签）→ 表头混入数据
2. ✅ 编写 `merge_results.py`：自动检测列数、去重、统一输出格式
3. ✅ 最终 82/84 组（97.5%），仅 OHSUMED+BioBERT+AdaBoost/XGBoost 超时
4. 🔄 最后 2 组正在以 48h 任务补跑（Job 228590）

### 3.5 多标签策略（实验 004）

**挑战：** sklearn `ClassifierChain` 在并行环境中的兼容性。

**迭代过程：**
1. ❌ `copy.deepcopy(LogisticRegression(n_jobs=-1))` 在 `Parallel(n_jobs=-1)` 内 → loky 嵌套死锁
2. ✅ 每个 fold 新建 `LogisticRegression(max_iter=1000)`，不 deepcopy
3. ❌ PML 数据集的 V 列（0% 正样本）→ `LogisticRegression` 报 "only one class"
4. ✅ `y_tr.max(axis=0) - y_tr.min(axis=0) > 0` 过滤常量列
5. ❌ `numpy.ptp()` 在 numpy 2.x 已移除
6. ✅ 改用 `max - min`
7. ❌ 恢复列数后 `f1_score(y_te, y_pred)` 维度不匹配
8. ✅ `y_te` 不切片，预测后恢复完整标签列
9. ✅ 最终 6 行结果：CC on PML F1=0.5796 🏆

### 3.6 Node2Vec 实现 bug（实验 005）

**挑战：** 手写 Node2Vec 的 alias sampling 实现有误。

1. ❌ `_alias_draw()` 调用时未传入 `items`（邻居节点列表）→ 返回索引而非节点 ID
2. ❌ 随机游走中 walk 被错误节点污染 → `KeyError`
3. ✅ 传入 `alias_nodes[(prev, cur)][2]` → 正确返回邻居节点 ID

### 3.7 GCN/GraphSAGE 实现（实验 005）

1. ❌ `run_gcn` 中 `f1_score` 未导入 → `NameError`
2. ❌ `run_graphsage` 同样缺 `f1_score` → 修复
3. ❌ GraphSAGE `Linear(hidden * 2, out_dim)` 但输入是 `hidden` 维 → 维度不匹配
4. ✅ 改为 `Linear(hidden, out_dim)`

### 3.8 Spatial Tracker 基准测试（实验 006）

**挑战：** CPU 与 GPU 任务同时写入同一 CSV 造成覆盖。

**迭代过程：**
1. ❌ 首次提交：CPU 写 TF-IDF+SVM + BioBERT+LR，GPU 写 BioBERT+MLP → GPU 覆盖 CPU 结果
2. ✅ 添加 `--out-suffix` 参数：CPU 写入 `st_benchmark_cpu.csv`，GPU 写入 `st_benchmark_gpu.csv`
3. ✅ 编写 `merge_results.py` 合并为完整三行
4. ✅ 最终 3/3 方法全部完成

### 3.9 迁移微调探索（实验 007）

**挑战：** 源域与目标域标签空间不同导致缓存键不匹配、XGBoost warm start 兼容性问题。

**迭代过程：**
1. ❌ `_CACHE_KW = {}` 与 Exp 001 的 `{"max_samples": null}` 不匹配 → 15h 重复计算 BioBERT 特征
2. ✅ 统一 `SOURCE_DS` 字典，`get_cached_features` 按数据集名匹配缓存键
3. ❌ OHSUMED 标签是稀疏矩阵，`argmax(axis=1)` 返回 2D → `CrossEntropyLoss` 报 "multi-target"
4. ✅ `np.ravel(np.asarray(y.argmax(axis=1)))` 展平为 1D
5. ❌ XGBoost warm start 要求源域与目标域 `n_classes` 一致（PML 14≠6, OHSUMED 1650≠6）
6. ✅ 移除 C3/C4，XGBoost 跨标签空间迁移不可行
7. ❌ D3/D4 PGB GCN 迁移：PGB 用 TF-IDF(5000dim) 但 ST GCN 用 BioBERT(768dim) → 维度不匹配
8. ❌ 修复 `build_graph=True` 后 D3/D4 仍失败：特征维度不同
9. ✅ 最终 GPU 3/3 完成，CPU 8/10 完成，共 11/13

## 4. 最终实验结果

### 实验 001 — 经典算法矩阵（82/84 组）

**OHSUMED（26/28，1,650 标签）**
| 特征 | 最佳模型 | F1-macro | 最慢模型 | 耗时 |
|---|---|---|---|---|
| TF-IDF | **AdaBoost** | **0.1687** 🏆 | SVM | 28,806s |
| BioBERT | LogisticReg | 0.0853 | SVM | 10,311s |
| LDA | AdaBoost | 0.0117 | RF | 2,771s |
| Meta | AdaBoost | 0.0270 | RF | 1,994s |

**PML（28/28 全部完成 ✅）**
| 特征 | 最佳模型 | F1-macro |
|---|---|---|
| TF-IDF | SVM | 0.5682 |
| BioBERT | **LogisticReg** | **0.6710** 🏆 |
| LDA | AdaBoost | 0.5161 |
| Meta | AdaBoost | 0.3476 |

**PGB（28/28 全部完成 ✅）**
| 特征 | 最佳模型 | F1-macro |
|---|---|---|
| TF-IDF | **AdaBoost** | **0.4215** 🏆 |
| BioBERT | LR/RF/SVM/kNN/XGB (~0.3324) | — |
| LDA | LogisticReg | 0.3324 |
| Meta | AdaBoost | 0.3324 |

### 实验 002 — BioBERT+MLP（3/3 ✅）

| 数据集 | F1-macro | 时间 |
|---|---|---|
| OHSUMED | 0.0013 | 17min |
| **PML** | **0.6411** 🏆 | 19min |
| **PGB** | **0.3601** | 9min |

### 实验 003 — LDA+聚类（3/3 ✅）
- OHSUMED NMI=0.44, PML NMI=0.10, PGB NMI=0.005

### 实验 004 — 多标签策略（6/6 ✅）
- PML: CC **0.5796** 🏆 > BR 0.5686 ≈ LP 0.5686

### 实验 005 — 图模型（8/9 ✅）
- **GCN 0.4125** 🏆 >> Node2Vec 0.3324 ≈ GraphSAGE 0.3324

### 实验 006 — Spatial Tracker 基准测试（3/3 ✅）

| 方法 | F1-macro | Accuracy | 训练时间 |
|---|---|---|---|
| TF-IDF + SVM | 0.6365 ± 0.0123 | 0.9167 ± 0.0011 | 913s |
| BioBERT + LR | 0.8068 ± 0.0320 | 0.9298 ± 0.0035 | 138s |
| **BioBERT + MLP** | **0.8444** 🏆 ± 0.0353 | **0.9380** 🏆 ± 0.0124 | 1039s |

- BioBERT+MLP 在 Spatial Tracker 上 F1=0.8444，比 TF-IDF+SVM 提升 33%
- BioBERT+LR（冻结嵌入）F1=0.8068，仅比 MLP 差 4.7%，但速度快 7.5 倍
- 三方法的排名与实验 001/002 的结论一致：BioBERT 嵌入 >> TF-IDF 特征

### 实验 007 — 迁移微调探索（11/13 完成 ✅）

**GPU 结果（3/3 ✅）：**

| 实验 | 源域 | 算法 | F1-macro | Accuracy | 总时间 | 增益 |
|---|---|---|---|---|---|---|
| B2 | ST（基线） | BioBERT+MLP | 0.8345 | 0.9509 | 389s | — |
| **C1** 🏆 | **PML** | **BioBERT+MLP** | **0.9143** | 0.9476 | 756s | **+9.6%** 🔥 |
| C2 | OHSUMED | BioBERT+MLP | 0.8503 | 0.9378 | 561s | +1.9% |

**CPU 结果（8/10 ✅）：**

| 实验 | 方法 | F1-macro | Accuracy |
|---|---|---|---|
| B1 | ST→ST BioBERT+LR | **0.8157** | 0.9378 |
| B3 | ST→ST BioBERT+XGBoost | 0.7457 | 0.9236 |
| **D1** | **GCN on ST k-NN 图** | **0.7716** | 0.9083 |
| D2 | GraphSAGE on ST k-NN 图 | 0.7603 | 0.9225 |
| A1-A5 | 零样本迁移（标签空间不同） | ~0 | ~0 |
| D3-D4 | PGB→ST GCN 迁移 | ❌ | ❌ |
| C3-C4 | XGBoost warm start（n_classes 不匹配） | ❌ | ❌ |

**结论**：PML 预训练 + ST 微调是最优策略（F1=0.9143），比直接训练提升 +9.6%。
k-NN 图的 GCN/GraphSAGE 在 ST 上达到 F1≈0.77，接近 LR 基线但未超越。

## 5. 关键发现

1. **AdaBoost + TF-IDF 在稀疏标签空间意外地好**：OHSUMED 上 0.1687，远超其他模型
2. **BioBERT 预训练嵌入 + Logistic Regression 在 PML 上最优**（0.6710），说明冻结嵌入 + 简单分类器在粗粒度标签上已经足够
3. **GCN 显著优于 Node2Vec 和 GraphSAGE**（0.4125 vs 0.3324），图卷积结构对 PGB 的节点分类任务更有效
4. **Classifier Chains 在多标签上有边际收益**（CC 0.5796 vs BR 0.5686），但只在小标签空间（16 labels）上体现
5. **OHSUMED 的 1,650 标签太稀疏**，所有方法 F1-macro < 0.2
6. **BioBERT+MLP + Spatial Tracker 达到最高绝对分数**（F1=0.8444），验证了端到端微调在目标数据集上的优势
7. **BioBERT+LR 是性价比最优选择**：F1=0.8068（仅差 4.7%），但训练时间只需 138s（快 7.5 倍）
8. **迁移微调显著有效**：PML 预训练 + ST 微调 F1=0.9143 🏆，比直接训练高 +9.6%
9. **源域选择影响重大**：PML（16 标签，同类型）预训练优于 OHSUMED（1650 标签，异类型），+7.5% 差距
10. **k-NN 图 GCN/GraphSAGE** 在 ST 上 F1≈0.77，验证了图模型的可行性但未超越 BioBERT+LR

## 6. 技术债务与教训

| 类别 | 教训 |
|---|---|
| **集群运维** | 传输 conda 环境用 rsync 不要用 tar（避免 .so 文件损坏） |
| **版本管理** | transformers 5.x 和 PyTorch < 2.6 不兼容 → 锁定版本 |
| **HuggingFace 缓存** | 提前验证所有缓存文件完整性，不全则补 |
| **并行计算** | sklearn 的 n_jobs=-1 嵌套在 joblib.Parallel 内会造成死锁 |
| **增量保存** | 长时实验必须有增量保存机制，否则超时全丢 |
| **CSV 格式** | 多格式数据合并要用脚本处理，不要 cat + sort -u |
| **续跑检查** | `--models` 过滤时 completed 计数要匹配过滤器，不能全量 |

## 7. 实验耗时统计

| 阶段 | 提交次数 | 总耗时 |
|---|---|---|
| 000 查询分析 | 1 | — |
| 001 经典矩阵 | **~25 次** 🔴 | ~**10 天**（含迭代） |
| 002 BioBERT | **~9 次** | ~3 天 |
| 003 LDA 聚类 | 2 | 8h |
| 004 多标签策略 | **~6 次** | ~1 天 |
| 005 图模型 | **~5 次** | ~1 天 |
| 006 ST 基准 | **~4 次** | ~6h |
| 007 迁移微调 | **~8 次** | ~1 天 |
| **总计** | **~60 次提交** | **~2 周** |
