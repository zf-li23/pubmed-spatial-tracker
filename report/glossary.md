# PubMed Spatial Tracker — 完整术语与模型词典

> 覆盖项目中出现的全部模型、算法、数据集、特征、指标和技术术语。
> 按类别组织，便于汇报时快速查阅。

---

## 一、数据集

### OHSUMED
- **全称**: OHSUMED (Oregon Health Sciences University MEDLINE)
- **来源**: TREC-9 Filtering Track，包含 1987–1991 年间 MEDLINE 数据库的 294K 篇文献摘要
- **标签**: 14,466 个 MeSH 词（经低频过滤后保留 1,650 个高频词）
- **特点**: 极稀疏多标签，幂律分布（少数词覆盖大部分文献），经典信息检索基准
- **项目角色**: 大规模稀疏标签基准，测试算法在极多标签下的扩展能力

### PubMed-MultiLabel (PML)
- **来源**: Kaggle 数据集
- **规模**: 10K 篇（原始）/ 50K 篇（处理后），项目使用 10K 版
- **标签**: 15 个 MeSH 顶级类别（如 Neoplasms, Nervous System Diseases, Cardiovascular Diseases...）+ 1 个 Other = 16 类
- **特点**: 粗粒度、标签稠密、数据干净
- **项目角色**: 粗粒度快速实验平台，算法筛选的主要战场

### PGB (PubMed Graph Benchmark)
- **来源**: Lee & Ho, arXiv:2305.02691, 2023
- **规模**: ~30M 篇论文的异构引用图，项目采样 5K 篇
- **标签**: 3 类节点分类任务
- **特点**: 天然异构图结构（5 类节点 / 7 种边类型）+ MeSH 层级树
- **项目角色**: 图表示学习方法的验证平台

### Spatial Tracker (ST)
- **全称**: 自建空间转录组学文献数据集
- **来源**: PubMed 检索爬取，项目自建
- **规模**: 9,148 篇（2016–2026，含摘要+英文）
- **标签**: 6 类（Research / Technology / Review / Protocol / Data Resource / Benchmark）+ 15 分析标签 + 19 技术平台 + 17 生物学领域，全部由 LLM 标注
- **项目角色**: 最终目标应用场景

---

## 二、文本表示方法（5 种）

### TF-IDF (Term Frequency-Inverse Document Frequency)
- **原理**: 词袋模型，用词频 × 逆文档频率衡量词语重要性
- **配置**: 1–2 gram，max_features=5,000
- **维度**: 5,000
- **优点**: 可解释性强，经典基线
- **缺点**: 无法捕捉语义相似性（"心脏"和"心肌"被视为不同词）

### BioBERT Embedding
- **全称**: Biomedical Bidirectional Encoder Representations from Transformers
- **模型**: `dmis-lab/biobert-base-cased-v1.1`（在 PubMed 摘要+PMC 全文上预训练）
- **配置**: Mean Pooling（取所有 Token 输出向量的平均值）
- **维度**: 768
- **优点**: 捕捉医学术语的上下文语义关系
- **项目中的角色**: **最优特征**，在 PML 上配合 LR 达到 0.6710

### LDA (Latent Dirichlet Allocation)
- **原理**: 概率主题模型，假设每个文档是多个主题的混合，每个主题是词的分布
- **配置**: K=15 个主题
- **维度**: 15
- **优点**: 维度低、可解释（每个主题可用 Top 词概括）
- **缺点**: 与分类任务可能不匹配（PGB 上 NMI≈0）

### Meta Features（元特征）
- **组成**: 出版年份、文本长度、单词数、MeSH 词数等非文本特征
- **维度**: 3–5（依数据集而异）
- **配置**: z-score 归一化
- **作用**: 作为非文本信号的补充特征

### Node2Vec Embedding
- **原理**: 图嵌入方法，在引用图上做有偏随机游走，用 Word2Vec 的 Skip-Gram 学习节点向量
- **超参数**: p=1（BFS 权重）, q=2（DFS 权重）, walk_length=30, num_walks=200, dimensions=128
- **维度**: 128
- **适用**: 仅 PGB（有引用图结构）
- **项目表现**: 各分类器在 Node2Vec 上性能持平（F1≈0.3324），未超越 TF-IDF

---

## 三、分类模型（14 种）

### 3.1 经典机器学习（7 种）

#### Naive Bayes（朴素贝叶斯）
- **类别**: 贝叶斯学习 / 生成式模型
- **原理**: 基于贝叶斯定理，假设特征条件独立。项目用 GaussianNB（不要求非负输入）
- **优点**: 训练极快，适合高维数据
- **缺点**: 特征独立性假设在文本数据上通常不成立
- **项目表现**: PML 上 0.6203，OHSUMED 上 0.0685，PGB 上 0.3611

#### k-NN (k-Nearest Neighbors)
- **类别**: 基于实例的学习 / 惰性学习
- **原理**: 找到与待分类样本最近的 k 个训练样本，以多数投票决定类别
- **超参数**: k=5, 距离度量=欧氏距离
- **优点**: 无需训练，简单直观
- **缺点**: 对特征缩放敏感，预测慢（需计算全部样本距离）
- **项目表现**: 中等偏下，略好于 Naive Bayes

#### SVM (Support Vector Machine)
- **类别**: 基于实例的学习 / 最大间隔分类器
- **原理**: 寻找最大化类别间隔的超平面，RBF 核可将数据映射到高维空间
- **配置**: RBF 核（径向基函数），C=1.0, gamma='scale'
- **优点**: 在高维空间表现好，理论基础扎实
- **缺点**: 训练 O(n²~n³)，**极慢**（OHSUMED 上 28,806s ≈ 8h）
- **项目表现**: PML 上亚军 0.6603，PGB 上亚军 0.3775

#### Logistic Regression（逻辑回归）
- **类别**: 回归学习 / 广义线性模型
- **原理**: 用 Sigmoid 函数将线性回归输出映射到 [0,1] 做概率分类
- **配置**: L2 正则化, max_iter=1000, multi_class='multinomial'
- **优点**: 训练快，概率校准好，在稠密标签上极强
- **项目表现**: **PML 冠军 0.6710**，性价比最优选择

#### Random Forest（随机森林）
- **类别**: 集成学习（Bagging）/ 决策树集成
- **原理**: 构建多棵决策树，每棵树在随机采样的数据和特征上训练，投票决定最终结果
- **配置**: n_estimators=100, max_depth=None
- **优点**: 抗过拟合，能处理非线性关系，自带特征重要性
- **缺点**: OHSUMED 上训练慢（2,771s），模型大

#### AdaBoost (Adaptive Boosting)
- **类别**: 集成学习（Boosting）
- **原理**: 序列训练弱分类器，每轮提高前一轮误分类样本的权重，加权投票
- **配置**: SAMME 算法, n_estimators=50
- **优点**: **在稀疏标签空间极强**
- **项目表现**: OHSUMED 冠军 **0.1687** 🏆，PGB 冠军 **0.4215** 🏆

#### XGBoost (eXtreme Gradient Boosting)
- **类别**: 集成学习（Boosting）/ 梯度提升决策树
- **原理**: 在 AdaBoost 基础上引入正则化项和二阶梯度优化，GPU 加速
- **配置**: n_estimators=100, max_depth=6, learning_rate=0.3
- **优点**: 比赛级性能，支持 GPU，原生处理缺失值
- **缺点**: 无法跨不同标签空间做 warm start 迁移
- **项目表现**: 整体与 AdaBoost 接近

### 3.2 深度学习（1 种）

#### BioBERT + MLP（多层感知机）
- **类别**: 深度学习 / 迁移学习
- **结构**: BioBERT 编码器（冻结或微调）→ MLP 分类头（1–2 个隐藏层, 768→256→n_classes）
- **训练**: AdamW 优化器, learning_rate=2e-5, batch_size=16, epochs=5
- **损失函数**: 
  - 多标签（OHSUMED/PML/ST）: BCEWithLogitsLoss
  - 单标签（PGB）: CrossEntropyLoss
- **项目角色**: 
  - **Exp 002**: 端到端微调（全参数更新）
  - **Exp 006**: ST 基准测试（F1=0.8444 🏆）
  - **Exp 007**: 迁移微调（PML→ST 达到 **F1=0.9143 全场最佳** 🏆）

### 3.3 无监督学习（1 种）

#### LDA + KMeans
- **原理**: LDA 提取 15 维主题分布 → KMeans 聚类（K=实际类别数）
- **评估**: NMI（归一化互信息），衡量聚类与真实标签的匹配度
- **项目表现**: OHSUMED NMI=0.44（主题结构好），PML NMI=0.10，PGB NMI≈0

### 3.4 图模型（3 种）

#### Node2Vec + 分类器
- **原理**: 引用图上随机游走 → Word2Vec Skip-Gram → 得到 128 维节点嵌入 → 经典分类器分类
- **项目表现**: 各分类器 F1≈0.3324（基本持平），不如直接用 TF-IDF

#### GCN (Graph Convolutional Network，图卷积网络)
- **原理**: 在图上做卷积操作，每个节点聚合邻居节点的特征来更新自身表示
- **结构**: 2 层 GCN, hidden=64, ReLU, Dropout=0.5
- **项目表现**: 
  - PGB: **0.4125** 🏆（最佳图方法）
  - ST k-NN 图: 0.7716（接近 LR 基线但未超越）

#### GraphSAGE (Graph Sample and Aggregation，图采样与聚合)
- **原理**: 对每个节点的邻居进行采样和特征聚合（Mean/LSTM/Pooling），归纳式学习
- **结构**: 2 层 SAGEConv, hidden=64, Mean 聚合
- **项目表现**: 
  - PGB: 0.3324（不如 GCN）
  - ST k-NN 图: 0.7603

---

## 四、多标签策略（3 种）

### Binary Relevance (BR，二元关联)
- **原理**: 为每个标签独立训练一个二分类器，忽略标签之间的相关性
- **优点**: 简单、可并行
- **缺点**: 无法利用标签共现信息
- **项目表现**: PML F1=0.5686

### Classifier Chains (CC，分类器链)
- **原理**: 将标签按随机顺序排列成链，每个分类器的输入包括原始特征 + 前序分类器的预测
- **优点**: 能捕捉标签依赖关系
- **缺点**: 链顺序影响结果，无法并行
- **项目表现**: PML **0.5796** 🏆（最优多标签策略）

### Label Powerset (LP，标签幂集)
- **原理**: 将每个标签组合视为一个新类别，转化为多分类问题
- **优点**: 完整捕捉标签组合信息
- **缺点**: 类别爆炸（2^n），**OHSUMED 上完全不可行**
- **项目表现**: PML F1=0.5686（与 BR 持平）

---

## 五、评估指标

### F1-macro（宏平均 F1）
- **定义**: 先计算每个类别的 F1（精确率×召回率的调和平均），再取算术平均
- **范围**: [0, 1]
- **特点**: 平等对待每个类别，不受类别不平衡影响
- **项目中的角色**: **主要评价指标**

### Accuracy（准确率）
- **定义**: 正确预测数 / 总样本数
- **局限**: 在不平衡数据集上可能产生误导（如 90% 为 Research 类时猜全 Research 就有 90%）

### NMI (Normalized Mutual Information，归一化互信息)
- **定义**: 衡量聚类结果与真实标签的 mutual information，归一化到 [0, 1]
- **用途**: 评估无监督聚类（Exp 003）

### Cohen's κ（Cohen's Kappa）
- **定义**: 衡量两个标注者之间的一致性，排除随机猜测
- **用途**: 人工抽检 LLM 标注质量（已设计模板，待执行）
- **解读**: κ>0.8 几乎完全一致, 0.6–0.8 高度一致, 0.4–0.6 中等一致

### Hamming Loss（汉明损失）
- **定义**: 错误预测的标签比例（多标签中常用）
- **越低越好**: 0 表示完美预测

### Jaccard Similarity（杰卡德相似度）
- **定义**: 预测标签集与真实标签集的交集 / 并集
- **用途**: 多标签分类的样本级评估

### Per-label F1（逐标签 F1）
- **定义**: 计算每个标签独立的 F1 并汇总
- **用途**: 分析哪些标签分类好、哪些差

### Paired t-test（配对 t 检验）
- **定义**: 比较两个模型在相同 5 折上的 F1 值是否具有统计显著差异
- **输出**: p-value → *** (<0.001), ** (<0.01), * (<0.05), ns (不显著)
- **用途**: Fig2 中 Top-5 显著性分析

---

## 六、技术术语

### MeSH (Medical Subject Headings，医学主题词表)
- **定义**: 美国国家医学图书馆（NLM）维护的等级制医学词汇表，约 30K 个主题词
- **层级**: 类似树结构（如 "Cardiovascular Diseases / Heart Diseases / Myocardial Ischemia"）
- **在项目中的角色**: OHSUMED 和 PML 的标签来源，PGB 包含层级信息

### Spatial Transcriptomics（空间转录组学）
- **定义**: 在组织切片原位测量基因表达的技术，同时获得基因表达量和空间位置信息
- **本项目的目标领域**: 项目爬取的 9,148 篇文献全部来自此领域
- **主要技术平台**: Visium (10x), MERFISH, Slide-seq, Xenium, Stereo-seq, CosMx

### 5-Fold Cross Validation（5 折交叉验证）
- **原理**: 将数据分成 5 等份，轮流用 4 份训练、1 份验证，重复 5 次
- **优点**: 评估更稳定，减少单次划分的随机性
- **项目配置**: StratifiedKFold（分层采样保持类别比例）

### Transfer Learning（迁移学习）
- **定义**: 在源域（如 PML）上训练模型，再在目标域（如 ST）上微调
- **项目探索**: 3 种源域（PML/OHSUMED/PGB）× 3 种算法（MLP/GCN/GraphSAGE）
- **核心发现**: PML→ST 微调比直接训练提升 +9.6%

### Fine-tuning（微调）
- **定义**: 在预训练模型基础上，用目标域数据继续训练少量 epoch，使参数适应新任务
- **项目中的两种微调**:
  - **Exp 002**: BioBERT 全参数微调（更新全部 110M 参数）
  - **Exp 007**: 迁移微调（加载 PML 训练的 MLP 权重→在 ST 上继续训练）

### LLM Annotation（大语言模型标注）
- **定义**: 使用 DeepSeek-v4-flash 大模型自动为文献分配标签
- **方法**: 参考 Biomed-Enriched 两阶段方法（arXiv:2506.20331）
- **Prompt 设计**: 精细的 System Prompt + User Prompt，输出 JSON 格式
- **结果**: 9,148 篇全部标注完成，high+medium 置信度占 95.6%

### k-NN Graph（k 近邻图）
- **定义**: 以每篇文献为节点，用 BioBERT 嵌入的余弦相似度找到 k 个最近邻作为边
- **配置**: k=15
- **用途**: 为无图结构的 ST 数据集构建人工图，使 GCN/GraphSAGE 可用

### Mean Pooling（平均池化）
- **定义**: 对序列中所有 Token 的输出向量取平均值，作为整个序列的表示
- **用途**: 将 BioBERT 输出的变长 Token 序列压缩为固定 768 维向量
- **替代方案**: CLS Token（取 [CLS] 位置的输出）

### UMAP (Uniform Manifold Approximation and Projection)
- **定义**: 非线性降维算法，在保持数据局部结构的同时映射到 2D/3D
- **用途**: 可视化 BioBERT 嵌入的高维空间结构
- **项目产出**: Fig5 A-F，展示 4 个数据集的嵌入分布

### Slurm (Simple Linux Utility for Resource Management)
- **定义**: 集群作业调度系统，管理计算资源的分配和作业排队
- **项目用途**: 在 a-cluster 上提交 60+ 次实验作业
- **常用命令**: `sbatch`（提交）, `squeue`（查看队列）, `scancel`（取消）

### Transformers（HuggingFace Transformers）
- **定义**: HuggingFace 的深度学习框架，提供预训练模型的加载和微调
- **项目版本**: 4.48.3（锁定版本，5.x 与 PyTorch 2.5 不兼容）
- **用途**: 加载 BioBERT 模型和分词器

### Entrez / Biopython
- **定义**: NCBI 的 E-utilities API，用于程序化检索 PubMed 等数据库
- **项目用途**: 空间转录组学文献的检索与爬取

### CV (Cross Validation，交叉验证)
- **已在 5-Fold Cross Validation 中介绍**

### Epoch
- **定义**: 完整遍历一次训练数据集
- **项目配置**: BioBERT+MLP 微调 5 epoch

### Embedding（嵌入）
- **定义**: 将离散对象（词、句子、节点）映射到连续向量空间
- **项目中的嵌入**: BioBERT（文本→768d）, Node2Vec（节点→128d）

---

## 七、项目专项术语

### 三步渐进实验策略
- **Step 1**: 在 3 个全标注数据集上系统比较所有算法→筛选 Top 方法
- **Step 2**: 构建目标 ST 数据集（检索+LLM标注）→用 Step 1 选出的方法验证
- **Step 3**: 探索迁移微调→"宽泛预训练+领域微调"范式

### 数据集梯度设计
- 四个数据集从三个维度形成"梯度"：
  - **标签粒度**: 16 (PML) → 3 (PGB) → 1,650 (OHSUMED) → 40+ (ST)
  - **信息维度**: 纯文本 → 文本+元数据 → 文本+图结构
  - **标注完备性**: 全标注 → LLM 标注

### 特征有效性排序（项目核心发现之一）
```
BioBERT (768d) >> TF-IDF (5K) > LDA (15d) > Meta (3-5d)
```
语义深度（BioBERT）比特征维度（TF-IDF 5K）更重要。

### 算法排序规律（项目核心发现之二）
- **稠密标签（PML 16 类）**: LR > SVM > RF > XGB > Ada > k-NN > NB
- **稀疏标签（OHSUMED 1,650 类）**: AdaBoost > XGB > LR > RF > SVM > k-NN > NB
- **标签密度决定了算法排序**

---

## 八、环境与工具

| 名称 | 类型 | 用途 |
|---|---|---|
| Python 3.13 | 语言 | 主开发环境（pubmed-tracker） |
| Python 3.12 | 语言 | GPU 环境（biobert_env，因 CUDA wheel 兼容性降级） |
| scikit-learn 1.8.0 | 库 | 经典机器学习算法、交叉验证、评估指标 |
| PyTorch 2.5.1+cu121 | 深度学习框架 | BioBERT+MLP 训练，GCN/GraphSAGE 实现 |
| transformers 4.48.3 | 库 | BioBERT 模型加载和分词 |
| XGBoost 3.2.0 | 库 | 梯度提升树 |
| matplotlib + scienceplots | 可视化 | 5 张复合图 + 42 个面板 |
| Flask + React | Web 框架 | Web 应用前端和后端 |
| DeepSeek-v4-flash | LLM | 9,148 篇文献批量标注 |
| a-cluster (Slurm) | 计算集群 | ~60 次实验作业提交 |

---

> 最后更新: 2026-06-11
> 涵盖: 4 数据集 · 5 特征 · 14 算法 · 3 多标签策略 · 10+ 评估指标 · 20+ 技术术语
