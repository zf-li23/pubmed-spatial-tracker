# AGENTS.md — PubMed Spatial Tracker

> 本文档为 AI 助手提供项目上下文。最后更新: 2026-05-16（重构后）

---

## 项目概述

PubMed Spatial Tracker 是一个面向空间转录组学文献的半自动标注与机器学习分类系统。
核心理念：**Human-in-the-loop** — 规则引擎冷启动 → 人工修正 → 模型学习 → 迭代预测。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.10+, FastAPI, Uvicorn, SQLAlchemy |
| 存储 | SQLite (WAL 模式, `spatial_literature.db`) |
| 前端 | React 19, Vite 8, Tailwind CSS 3 |
| ML | scikit-learn (SVC + TF-IDF), 可选 sentence-transformers |
| 数据获取 | BioPython (Entrez/PubMed API) |
| 配置 | `.env` + python-dotenv |
| 部署 | Makefile 脚本, GitHub Pages (静态只读模式) |

## 重构状态 (2026-05-16)

以下内容反映的是重构**已完成**后的实际状态。

### 已完成的重构

#### 🔴 数据安全（已修复）
- `save_df()` 已从 `if_exists='replace'` 改为逐行 `INSERT OR REPLACE`（事务包裹）
- `literature` 表已添加 `pmid TEXT PRIMARY KEY`
- `uncertainty_score` 列已改为 `REAL` 类型
- `is_discarded` 新列已独立于 tags（413 篇 Discarded 已从 tags 迁移）
- WAL 模式已启用（`PRAGMA journal_mode=WAL`）

#### 🟠 代码消重（已修复）
- `web_app/shared.py` 成为单一真相源，包含：`load_tags()`, `guess_novel_name()`, `enforce_category_tag_policy()`, 停用词表
- `migrate_naive.py` 和 `ml_pipeline.py` 均已改为 import `shared.py`
- 临时脚本 `patch_app.py`, `patch_app_jsx.py`, `make_gen.py` 已删除
- `main.py` 的 `EXCEL_OUTPUT_FILE` 未定义变量已修复
- `ml_report.py` 硬编码路径已改用 `BASE_DIR` 相对路径
- `.env` 文件和 `python-dotenv` 已引入
- `requirements.txt` 已更新

#### 🟡 ML 管线（已改进）
- `AutomatedActiveLearner` → `SpatialLiteratureClassifier`（命名诚实）
- Discarded 已从 tags 字符串中剥离为独立 `is_discarded` 列
- 分类器输出四元组：`(categories, tags, uncertainties, discard_flags)`
- 新增 `article_tags` 关联表（11,677 行），支持结构化标签查询

#### 🟢 标签系统（已重构）
- `tags.json` 已化简：保留 `domain` / `technology` / `analysis` / `method_note` 四组
- 移除 `metaCategory` 和 `uncategorized` 分组（非语义标签）
- 前端硬编码过滤 `["聚类","去卷积","缺失值插补","细胞通讯"]` 已移除
- 标签约束策略由 `shared.py` 的 `enforce_category_tag_policy()` 统一执行

### 当前数据库 Schema

```sql
CREATE TABLE literature (
    pmid TEXT PRIMARY KEY,
    doi TEXT,
    title TEXT,
    journal TEXT,
    pub_year TEXT,
    category TEXT,
    tags TEXT,
    is_manually_confirmed INTEGER,
    pdf_path TEXT,
    url TEXT,
    abstract TEXT,
    mesh_terms TEXT,
    keywords TEXT,
    is_preprint TEXT,
    is_method_note TEXT,
    citation_count INTEGER,
    notes TEXT,
    auto_predicted_category TEXT,
    auto_predicted_tags TEXT,
    naive_category TEXT,
    naive_tags TEXT,
    uncertainty_score REAL,         -- 已修正类型
    is_discarded INTEGER DEFAULT 0  -- 已从 tags 剥离
);

CREATE TABLE article_tags (
    pmid TEXT NOT NULL,
    tag TEXT NOT NULL,
    tag_group TEXT NOT NULL,
    PRIMARY KEY (pmid, tag)
);
```

### 数据规模
- 7,029 篇文献（481 已确认，6,548 未确认）
- 11,677 条标签记录 (article_tags)
- 413 篇已标 Discarded
- PDF 归档：0 篇

### 标签本体 (tags.json)

```json
{
  "domain": ["Neuroscience", "Development", "Cancer", "Reproduction", ...],
  "technology": ["Visium", "MERFISH", "Slide-seq", "Stereo-seq", "Xenium", ...],
  "analysis": ["Clustering", "Deconvolution", "Imputation", "Cell Communication", ...],
  "method_note": []
}
```

### 分类器约束策略（由 shared.py 统一执行）

| 类别 | 标签规则 |
|---|---|
| Review | 仅 1 个 domain 标签；无命中则 "General" |
| Technology | 最多 2 个 technology 标签；无命中尝试新实体提取 |
| Database | 优先新实体提取；失败则空标签 |
| Data Analysis | 最多 3 个 analysis 标签 + 可选新实体名 |
| Research | 至少 1 个 domain + 可选 technology |

### 标签系统规则详解

#### 分组语义

| 分组 | 语义 | 约束 | 示例 |
|---|---|---|---|
| `domain` | 生物学领域/组织/疾病 | 每篇最多 3 个 | Neuroscience, Cancer, Lung |
| `technology` | 空间组学技术平台 | 每篇最多 2 个 | Visium, MERFISH, Stereo-seq |
| `analysis` | 分析任务与方法类型 | 每篇最多 3 个 | Clustering, Deconvolution, Benchmark |
| `method_note` | 新实体名称（动态提取） | 由 `guess_novel_name()` 填充 | SpatialScope, TISSUE |

#### 数据流

```
标题+摘要
    │
    ├─→ migrate_naive.py (get_naive)     → naive_category / naive_tags
    │       │
    │       └─→ shared.enforce_category_tag_policy()
    │
    ├─→ ml_pipeline.py (SpatialLiteratureClassifier)
    │       │
    │       ├─→ category: SVC 多分类
    │       ├─→ tags: OneVsRest SVC → shared.enforce_category_tag_policy()
    │       └─→ discard: SVC 二分类
    │
    └─→ 人工标注 (AnnotationForm.jsx)
            │
            └─→ category / tags / is_discarded / is_manually_confirmed
```

#### 约束策略详解（shared.py `enforce_category_tag_policy`）

**Review（综述）**
- 输入候选标签刷选为仅 `domain` 组内标签
- 最终保留最多 1 个标签
- 若无匹配 → 兜底 `"General"`
- 设计理由：综述文献覆盖领域广，限制标签数量防止标签膨胀

**Technology（技术方法）**
- 仅从 `technology` 组选取，最多保留 2 个
- 若无匹配 → 调用 `guess_novel_name(title)` 尝试提取新技术名
- 若新实体提取也失败 → 回退为 technology 组的第一个标签（兜底）
- 设计理由：技术类文章的核心信息是用了什么平台

**Database（数据库资源）**
- 优先调用 `guess_novel_name(title)` 从标题提取数据库名
- 提取成功 → 使用该名称作为唯一标签
- 提取失败 → 返回空列表（不输出泛词）
- 设计理由：数据库名的语义价值远高于通用标签；输出泛词反而有噪声

**Data Analysis（数据分析）**
- 从 `analysis` 组选取候选标签，最多 3 个（按 ML 概率排序）
- 额外调用 `guess_novel_name(title)` 尝试提取新方法名
- 若新实体名提取成功 → 置于标签列表首位，analysis 标签截断至共 3 个
- 设计理由：优先暴露新方法名，同时保留分类任务标签作为上下文

**Research（研究论文）**
- 必须包含至少 1 个 `domain` 标签，最多 3 个
- 可选附加 `technology` 标签，最多 2 个
- 若无 domain 匹配 → 兜底第一个 domain 标签
- 设计理由：研究论文的核心语义维度是"什么领域+用什么技术"

#### Discarded 列

独立于标签系统的二分类信号：
- `is_discarded=1`：文献与空间转录组学无关，或质量不足以纳入分析
- 存储在 `literature.is_discarded` 列（INTEGER），不混入 `tags` 字符串
- ML 管线将其作为独立二分类目标训练
- 前端通过 "Discard" 按钮设置

#### article_tags 表

提供结构化标签查询能力，与 `tags` 列保持同步：
- `pmid` + `tag` 为联合主键
- `tag_group` 记录标签所属分组
- 在 `save_df()` 和 `save_article()` 时由 `_sync_article_tags()` 自动同步
- 查询示例：`SELECT pmid FROM article_tags WHERE tag='Visium'`

### 运行方式

```bash
make run          # 生产启动
make dev          # 开发模式
python main.py    # 抓取新文献
python run_pipeline.py  # 离线重训
```

### 文件职责速查

| 文件 | 职责 |
|---|---|
| `main.py` | PubMed 检索 + 文献入库 + naive 规则初分类 |
| `migrate_naive.py` | 规则引擎（引用 shared.py） |
| `run_pipeline.py` | 离线重训：备份 → naive → ML → 保存 |
| `migrate_schema.py` | Schema 迁移脚本（已执行，可重复运行无害） |
| `web_app/shared.py` | **核心**：标签加载、新实体提取、约束策略引擎 |
| `web_app/app.py` | FastAPI 后端（逐行 upsert） |
| `web_app/ml_pipeline.py` | SpatialLiteratureClassifier（三维预测） |
| `web_app/ml_report.py` | 模型性能报告（增加 discard_auc） |
| `tags.json` | 标签本体配置 |
| `.env` | 环境变量（PUBMED_EMAIL 等） |
| `spatial_literature.db` | SQLite 主库（WAL 模式） |

### 注意事项
- 数据库已开启 WAL 模式，支持并发读
- `save_df()` 使用 `INSERT OR REPLACE` + 事务，不再全局覆盖
- 修改 `tags.json` 后需重新构建前端静态快照（`tags.snapshot.json`）以同步静态模式
- `article_tags` 表需在标签重命名/删除时同步更新（当前由 `_sync_article_tags()` 处理）
