# PLAN.md — PubMed Spatial Tracker 重构计划

> 创建: 2026-05-16 | 状态: 执行中

---

## 目标

将项目从"脚本拼凑的科研工具"提升为"以机器学习为核心的结构化文献管理系统"。
核心原则：**让代码结构反映它声称要做的事，让标签系统同时服务于人类可读和机器可学习。**

---

## 阶段 0：安全基线（5 分钟）

| 步骤 | 操作 |
|---|---|
| 0.1 | 备份数据库 `cp spatial_literature.db spatial_literature_backup_YYYYMMDD.db` |
| 0.2 | 每次修改数据库 Schema 前再单独备份 |

---

## 阶段 1：消除代码债务（低风险，改完即见效）

| 步骤 | 内容 | 影响范围 |
|---|---|---|
| 1.1 | 抽取公共函数到 `web_app/shared.py`：`load_tags()`, `guess_novel_name()`, `_is_good_novel_candidate()`, `GENERIC_NAME_STOPWORDS`, `_clean_candidate_name()`, `_uniq_keep_order()`, `enforce_category_tag_policy()` | migrate_naive.py, ml_pipeline.py |
| 1.2 | 删除临时脚本：`patch_app.py`, `patch_app_jsx.py`, `make_gen.py` | 无 |
| 1.3 | 修复 `main.py` 的 `EXCEL_OUTPUT_FILE` 未定义变量 | main.py |
| 1.4 | 硬编码邮箱/路径迁移到 `.env` + `python-dotenv` | main.py, ml_report.py, app.py |
| 1.5 | `logging` 模块替换 `print()` | 全局 |

---

## 阶段 2：数据库 Schema 升级（核心，需谨慎）

### 2.1 表结构变更

```sql
-- 原表
CREATE TABLE literature (
    pmid TEXT,                    -- 无主键
    ...
    uncertainty_score TEXT,        -- 应为 REAL
    ...
);

-- 新表
CREATE TABLE literature (
    pmid TEXT PRIMARY KEY,         -- 主键
    ...
    uncertainty_score REAL,         -- 正确类型
    is_discarded INTEGER DEFAULT 0, -- 独立二分类信号，从 tags 中剥离
    ...
);
```

### 2.2 新增 article_tags 表（标签可查询化）

```sql
CREATE TABLE article_tags (
    pmid TEXT NOT NULL,
    tag TEXT NOT NULL,
    tag_group TEXT NOT NULL,  -- domain / technology / analysis / metaCategory
    PRIMARY KEY (pmid, tag),
    FOREIGN KEY (pmid) REFERENCES literature(pmid)
);
```

### 2.3 tags 列迁移策略

| 字段 | 迁移前 | 迁移后 |
|---|---|---|
| `is_discarded` | 不存在 | 从 tags 中检测 "Discarded" → 写入 `is_discarded=1` |
| `tags` | 含 "Discarded" | 移除 "Discarded"（已移至 is_discarded） |
| `article_tags` | 不存在 | 将每篇文献的 tags 拆分写入 |

### 2.4 WAL 模式

```sql
PRAGMA journal_mode=WAL;
```

---

## 阶段 3：标签系统重构（影响最大，收益最大）

### 3.1 tags.json 重新设计

```json
{
  "domain": [
    "Neuroscience", "Development", "Cancer", "Reproduction",
    "Pathology", "Immunology", "Zoology", "Cardiology",
    "Lung", "Bone Tissues", "Plant"
  ],
  "technology": [
    "Visium", "MERFISH", "Slide-seq", "Stereo-seq", "Xenium",
    "CosMx", "GeoMx", "DBiT-seq", "seqFISH", "ISS",
    "FISH", "FFPE", "RNAscope", "ISH"
  ],
  "analysis": [
    "Clustering", "Deconvolution", "Imputation",
    "Cell Communication", "Spatial Trajectory",
    "Multimodal integration", "Domain Identification",
    "Gene Expression Prediction", "Segmentation",
    "Differential Expression", "Diffusion",
    "Dimensionality Reduction", "RNA Co-localization",
    "Denoising", "Application", "Benchmark",
    "Foundation", "Pipeline", "Visualization", "huSA"
  ],
  "method_note": []
}
```

移除了 `metaCategory` 和 `uncategorized` 分组——它们不是语义标签，而是元信息，不应混在标签本体中。

### 3.2 分类器约束策略（不变，但集中到 shared.py）

| 类别 | 标签规则 |
|---|---|
| **Review** | 仅 1 个标签，来自 domain 组；无命中则 "General" |
| **Technology** | 最多 2 个标签，来自 technology 组；无命中则尝试新实体提取 |
| **Database** | 优先新实体提取（数据库名），失败则空标签（不输出泛词） |
| **Data Analysis** | 最多 3 个标签，来自 analysis 组；可附一个新实体名 |
| **Research** | 至少 1 个 domain + 可选 technology 标签 |

### 3.3 前端标签过滤逻辑移除

`AnnotationForm.jsx` 中硬编码的 `["聚类","去卷积","缺失值插补","细胞通讯"]` 过滤逻辑移除。这些是 analysis 组的正常标签，应由策略引擎决定是否使用，不由前端硬过滤。

### 3.4 Tag 存储格式

- `tags` 列保持分号分隔字符串（向后兼容）
- `article_tags` 表提供结构化查询能力
- ML 特征工程从 `article_tags` 表或解析后的 tags 列表读取

---

## 阶段 4：修复并发写入（安全修复）

### 4.1 save_df() 重写

**现状**：`df.to_sql('literature', engine, index=False, if_exists='replace')`

**改为**：逐行 UPSERT，利用 `pmid` 主键：

```python
def save_article(engine, pmid: str, updates: dict):
    """Upsert a single article row by pmid."""
    with engine.begin() as con:
        # INSERT OR REPLACE approach with primary key
        ...
```

对于注释保存、标签修改等单行操作，使用直接 SQL UPDATE；对于全量导入（main.py 新文献入库），使用事务包裹的批量 INSERT OR REPLACE。

### 4.2 移除 df_lock

逐行操作 + 事务不再需要全局锁。

---

## 阶段 5：ML 管线升级（核心）

### 5.1 Discarded 分离

- `is_discarded` 作为独立二分类目标
- `ml_pipeline.py` 增加独立的 `clf_discard`（二分类器）
- Discarded 样本不再污染多标签预测的训练集

### 5.2 分类器命名修正

`AutomatedActiveLearner` → `SpatialLiteratureClassifier`

名字诚实反映功能：这是一个空间转录组文献分类器，包含类别预测 + 多标签预测 + 丢弃判别。

### 5.3 特征工程增强

- 从 `article_tags` 表读取已有标签作为特征
- 增加 MeSH 词表特征权重
- 增加期刊特征（预印本 vs 正式期刊）

### 5.4 评估管道

- 在 `ml_report.py` 中增加 per-dimension 评估：
  - Category accuracy (已存在)
  - Per-tag precision/recall/F1
  - Discarded classification AUC
  - Confusion matrix by category

---

## 阶段 6：架构分层（长期）

### 6.1 Service 层

```
web_app/
├── app.py          # FastAPI 路由（仅参数校验 + 响应）
├── services.py     # ArticleService, TagService, PDFService
├── database.py     # get_engine(), get_article(), save_article()
├── classifier.py   # 独立分类策略（引用 shared.py）
├── shared.py       # 公共函数
├── ml_pipeline.py  # ML 模型
└── ml_report.py    # 评估报告
```

### 6.2 配置集中

- 所有可变配置从 `.env` 读取
- `config.py` 作为单一配置入口

---

## 执行优先级

| 阶段 | 优先级 | 原因 |
|---|---|---|
| 0 (备份) | **立即** | 安全前提 |
| 1 (消债) | **P0** | 零风险，消除后续工作的干扰 |
| 2 (Schema) | **P0** | 后续所有改动的基础 |
| 3 (标签) | **P1** | 核心价值，不影响已有标注 |
| 4 (并发) | **P1** | 安全隐患 |
| 5 (ML) | **P2** | 依赖阶段 2、3 完成 |

---

## 回滚方案

任何阶段出问题：`cp spatial_literature_backup_YYYYMMDD.db spatial_literature.db`
数据库是 SQLite 单文件，回滚即替换。
