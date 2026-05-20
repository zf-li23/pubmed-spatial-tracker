# PubMed Spatial Tracker

面向生物医学文献的多策略多标签分类研究——聚焦空间转录组学领域。

## 项目目标

通过**多数据集 × 多算法 × 多文本表示**的系统性比较，探索生物医学文献自动分类的最佳策略，并最终应用于空间转录组学领域。

## 数据集

| 数据集 | 规模 | 标签空间 | 说明 |
|---|---|---|---|
| [OHSUMED](data/ohsumed/) | ~294K 篇 | 14,466 个 MeSH 词 | TREC-9 Filtering Track 基准（1987-1991），全标注 |
| [PubMed-MultiLabel](data/PubMed-MultiLabel/) | 10K/50K 篇 | 15 个 MeSH 顶级类别 | Kaggle 现代多标签数据集，全标注 |
| [PGB](data/pgb/) | ~30M 篇 | MeSH 层级 + 图结构 | 异构图基准（5 节点 / 7 边类型），全标注 |
| Spatial Tracker | ~数千篇（待构建） | 5 类 + 45 标签（待定义） | 自建空间转录组学文献库，LLM 批量标注 |

## 实验设计（三步渐进）

详见 [PLAN.md](PLAN.md)。

1. **Step 1** — 在三个全标注数据集上对比 13 种算法 × 4 种文本表示，筛选最优方法
2. **Step 2** — 构建空间转录组学数据集 + DeepSeek 批量标注，应用最优方法 vs BioBERT 基线
3. **Step 3** — 探索"宽泛预训练 + 领域微调"的迁移学习范式

## 算法

13 种算法覆盖贝叶斯学习、基于实例的学习、回归、集成学习（Bagging/Boosting）、深度学习、无监督学习、图表示学习。

## 环境

```bash
conda activate zf-li23
```

```bash
conda activate zf-li23
python -m pip install -r requirements.txt
cd web_app/frontend && npm install
```

可选（仅在你需要 Transformer 向量增强时）：

```bash
conda activate zf-li23
python -m pip install sentence-transformers
```

说明：
- 未安装 `sentence-transformers` 时，系统自动回退到 TF-IDF 向量，不影响分类器可用性。
- 模型下载已默认走 `HF_ENDPOINT=https://hf-mirror.com`。

## 4. 启动与运行

标准启动（推荐）：

```bash
make run
```

`make run` 会执行：
1. 清理 8000 端口残留进程
2. 重新构建前端静态资源
3. 启动 FastAPI 服务

访问地址：
- `http://127.0.0.1:8000`

开发模式：

```bash
make dev
```

## 5. 数据流程

### 5.1 抓取增量文献

```bash
python main.py
```

行为：
- 从 PubMed 按检索式拉取文献元数据
- 与现有库合并（保留已人工确认行）
- 生成 naive 初始标签

### 5.2 重训与推断

```bash
python run_pipeline.py
```

行为：
- 使用 `is_manually_confirmed=1` 样本训练
- 更新未确认样本的自动预测和不确定性分数
- 自动备份数据库，成功后清除

### 5.3 人工标注工作流

在 Web 界面中可执行：
- 分类与标签提交
- Discarded 负样本标记（独立 `is_discarded` 列）
- 本地 PDF 上传归档
- URL 抓取 PDF
- 仅保存 URL 外链
- 导入 PMID 列表（TXT 每行一个 PMID）

### 5.4 标签系统规则

标签按维度分为四组：

| 分组 | 例子 | 用途 |
|---|---|---|
| `domain` | Neuroscience, Cancer, Development... | 生物领域/组织/疾病 |
| `technology` | Visium, MERFISH, Stereo-seq... | 空间组学技术平台 |
| `analysis` | Clustering, Deconvolution... | 分析任务类型 |
| `method_note` | （动态） | 标题中提取的新实体名 |

分类器约束策略（由 `web_app/shared.py` 统一执行）：

| 类别 | 标签规则 |
|---|---|
| **Review** | 仅 1 个 domain 标签；无命中则 "General" |
| **Technology** | 最多 2 个 technology 标签；无命中尝试新实体提取 |
| **Database** | 优先新实体提取（数据库名）；失败则空标签 |
| **Data Analysis** | 最多 3 个 analysis 标签 + 可选新实体名 |
| **Research** | 至少 1 个 domain + 可选 technology 标签 |

### 5.5 数据库 Schema

```sql
CREATE TABLE literature (
    pmid TEXT PRIMARY KEY,
    doi TEXT, title TEXT, journal TEXT, pub_year TEXT,
    category TEXT, tags TEXT,
    is_manually_confirmed INTEGER,
    pdf_path TEXT, url TEXT,
    abstract TEXT, mesh_terms TEXT, keywords TEXT,
    is_preprint TEXT, is_method_note TEXT,
    citation_count INTEGER, notes TEXT,
    auto_predicted_category TEXT, auto_predicted_tags TEXT,
    naive_category TEXT, naive_tags TEXT,
    uncertainty_score REAL,
    is_discarded INTEGER DEFAULT 0
);

CREATE TABLE article_tags (
    pmid TEXT NOT NULL,
    tag TEXT NOT NULL,
    tag_group TEXT NOT NULL,
    PRIMARY KEY (pmid, tag)
);
```

### 5.6 ML 分类器

`SpatialLiteratureClassifier` 执行三个子任务：
1. **Category 多分类**：Research / Review / Technology / Database / Data Analysis
2. **Tags 多标签预测**：按类别约束策略过滤
3. **Discarded 二分类**：独立判别是否为无关文献

输出四元组：`(categories, tags, uncertainties, discard_flags)`

## 6. 手工导入 PMID

当前机制：
- 通过 `/api/pmids/upload` 导入的 PMID 写入数据库表 `manual_imported_pmids`
- 不再依赖项目根目录的文本文件

`manual_imported_pmids` 表字段：
- `pmid` TEXT PRIMARY KEY
- `source` TEXT（默认 `manual_upload`）
- `imported_at` TEXT（写入时间）

## 7. API 文档

### 7.1 文献查询与标注

- `GET /api/articles`
  - 返回全部文献记录
  - 按"未确认优先 + 不确定性降序"排序
  - 返回 `List[ArticleRecord]`

- `POST /api/articles/{pmid}/annotate`
  - 提交分类与标签，标记为人工确认
  - Body: `{"category": "Research", "tags": "Neuroscience; Visium"}`

- `POST /api/articles/{pmid}/discard`
  - 标记为 Discarded（`is_discarded=1`, `is_manually_confirmed=1`）

### 7.2 模型重训

- `POST /api/ml/active_learning`
  - 基于已确认样本重新训练 `SpatialLiteratureClassifier`
  - 更新所有未确认文献的预测

### 7.3 PMID 导入

- `POST /api/pmids/upload`
  - 上传 TXT（每行一个数字 PMID）并抓取新增文献

### 7.4 PDF 与链接

- `POST /api/articles/{pmid}/pdf/upload`
  - 上传本地 PDF，归档到 `PDF_Archive/{category}/`
- `POST /api/articles/{pmid}/pdf/download`
  - 从 URL 下载 PDF
- `POST /api/articles/{pmid}/pdf/save_link`
  - 仅保存外链 URL

### 7.5 标签管理

- `GET /api/tags` — 获取 `tags.json`
- `POST /api/tags` — 更新 `tags.json`
- `PUT /api/tags/rename` — 全库重命名标签
- `DELETE /api/tags/delete` — 全库删除标签
