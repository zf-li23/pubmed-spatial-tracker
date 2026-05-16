# AGENTS.md — PubMed Spatial Tracker

> 本文档为 AI 助手提供项目上下文。最后更新: 2026-05-14。

---

## 项目概述

PubMed Spatial Tracker 是一个面向空间转录组学文献的半自动标注与主动学习系统。核心理念：**Human-in-the-loop** — 规则引擎冷启动 → 人工修正 → 模型学习 → 迭代预测。

## 技术栈

| 层 | 技术 |
|---|---|
| 后端 | Python 3.10+, FastAPI, Uvicorn, SQLAlchemy |
| 存储 | SQLite (`spatial_literature.db`) |
| 前端 | React 19, Vite 8, Tailwind CSS 3 |
| ML | scikit-learn (SVC + TF-IDF), 可选 sentence-transformers |
| 数据获取 | BioPython (Entrez/PubMed API) |
| 部署 | Makefile 脚本, GitHub Pages (静态只读模式) |

## 真实项目状态审计 (2026-05-14)

以下评价基于代码实际执行路径和数据库内容，不依据文档声称。

### 数据规模

- **7,029 篇文献**，其中 481 篇已人工确认，6,548 篇未确认
- 类别分布：Research (3,827) > Data Analysis (1,635) > Review (1,266) > Technology (265) > Database (34) > Discard (2)
- PDF 归档率：**0 篇**（整个 PDF_Archive 目录未在数据库中有对应记录）
- 手动导入 PMID：4 条

### 架构优点

1. **产品逻辑闭环完整**：PubMed 抓取 → 规则初分类 → Web 人工标注 → 模型重训 → 预测反馈，链条畅通
2. **已从 Excel 迁移到 SQLite**：底层持久化使用了 SQLAlchemy + SQLite，比纯 Excel 方案稳定
3. **tags.json 集中管理**：标签本体字典化配置，前端 TagManager 支持增删改，规则引擎和 ML 链路共享同一份标签定义
4. **分类器约束规则在两条链路对齐**：`migrate_naive.py` 的 `enforce_category_tag_policy()` 和 `ml_pipeline.py` 的预测后处理逻辑一致
5. **前端交互设计较好**：分页、筛选、标注面板、PDF 拖拽上传、标签管理中心，功能齐全
6. **GitHub Pages 静态模式**：`VITE_STATIC_ONLY` 支持纯前端静态部署

### 问题清单（按严重性排序）

#### 🔴 严重 — 数据安全与并发

- **`save_df()` 以 `if_exists='replace'` 全量覆盖表**。每次保存执行 DROP + CREATE + INSERT。在 uvicorn 多 worker 或用户快速连续提交时，后一次保存会覆盖前一次提交的数据。`df_lock` (`threading.Lock`) 只保护单进程内，多 worker 场景完全无效。
- **`literature` 表无主键约束**。`pmid` 列没有 `PRIMARY KEY`，可能出现重复 PMID 行。

#### 🟠 中等 — 工程质量

- **代码重复**：`guess_novel_name()`, `_is_good_novel_candidate()`, `GENERIC_NAME_STOPWORDS` 在 `migrate_naive.py` 和 `ml_pipeline.py` 中完全重复
- **临时脚本未清理**：`patch_app.py`, `patch_app_jsx.py`, `make_gen.py` 是一次性迁移脚本，残留于源码树
- **日志全用 `print()`**：无结构化日志，无日志级别，无文件输出
- **`main.py` 引用未定义变量**：`save_to_file()` 中用 `EXCEL_OUTPUT_FILE` 但只定义了 `DB_OUTPUT_FILE`
- **硬编码路径**：`ml_report.py` 写死另一台机器的路径 `/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/`
- **硬编码邮箱**：`main.py` 写死 `EMAIL = "zf-li23@mails.tsinghua.edu.cn"`
- **`uncertainty_score` 列类型为 TEXT**：存储数值但用了字符串类型，排序可能出错

#### 🟡 轻微 — ML 算法局限性

- "主动学习"实际是**批量被动重训**：用已确认数据训练 → 预测全部未确认数据 → 按不确定性排序。缺少真正的 Query Strategy（如 entropy sampling, margin sampling 迭代选择最有信息量的样本逐个标注）
- 分类器用 TF-IDF + SVC，对语义理解有限，实际准确率需要 `ml_report.py` 运行才能评估
- Discarded 样本处理方式粗糙：作为特殊 tag 附加到 tags 字符串中，而非独立二分类信号

#### 🔵 遗漏

- **零测试**：没有单元测试、集成测试
- **无认证/授权**：任何可访问 8000 端口的人都能修改数据
- **无可观测性**：无健康检查端点，无 metrics
- **PDF 功能整体未激活**：代码路径完整但前端的 PDF 上传功能标注写了但数据库无记录

### 数据库 Schema（实际）

```sql
CREATE TABLE literature (
    pmid TEXT,              -- 无主键约束
    doi TEXT,
    title TEXT,
    journal TEXT,
    pub_year TEXT,
    category TEXT,
    tags TEXT,
    is_manually_confirmed BIGINT,
    pdf_path TEXT,
    url TEXT,
    abstract TEXT,
    mesh_terms TEXT,
    keywords TEXT,
    is_preprint TEXT,
    is_method_note TEXT,
    citation_count TEXT,
    notes TEXT,
    auto_predicted_category TEXT,
    auto_predicted_tags TEXT,
    naive_category TEXT,
    naive_tags TEXT,
    uncertainty_score TEXT   -- 应为 REAL
);
```

### 运行方式

```bash
# 生产启动（构建前端 + 清理端口 + 启动后端）
make run

# 开发模式（后端热重载，前端需单独 npm run dev）
make dev

# 抓取新文献
python main.py

# 重训模型
python run_pipeline.py
```

---

## 开发计划

### 短期（1-2 周，低风险高收益）

| 优先级 | 任务 | 说明 |
|---|---|---|
| P0 | 修复 `save_df()` 并发写入丢失 | 改用 UPDATE/INSERT 逐行操作 + WAL 模式，或至少用 `df.to_sql(..., if_exists='append')` + 事务 |
| P0 | 给 `literature` 表加主键 | `pmid TEXT PRIMARY KEY`，同时将 `uncertainty_score` 改为 REAL |
| P1 | 消除代码重复 | 抽取 `migrate_naive.py` 和 `ml_pipeline.py` 的公共函数到 `web_app/utils.py` 或 `web_app/shared.py` |
| P1 | 清理临时脚本 | 删除 `patch_app.py`, `patch_app_jsx.py`, `make_gen.py`（或在确认无用后移入归档） |
| P1 | 修复 `main.py` 的 `EXCEL_OUTPUT_FILE` | 改为正确的变量名或移除 Excel 输出逻辑 |
| P1 | 屏蔽硬编码敏感信息 | 邮箱和路径迁移到 `.env` + `python-dotenv` |
| P2 | `logging` 替换 `print()` | 增加日志级别控制和文件输出 |
| P2 | 修复 `ml_report.py` 硬编码路径 | 使用相对路径或 `BASE_DIR` |

### 长期（1-3 月，结构改进）

| 优先级 | 任务 | 说明 |
|---|---|---|
| P1 | 真正的主动学习 Query Strategy | 实现 Uncertainty Sampling / Entropy Sampling 循环：每轮只标注模型最不确定的 Top-K 篇 |
| P1 | 引入 BioBERT / PubMedBERT 嵌入 | 替换 TF-IDF 做文本向量化，提升语义理解准确率 |
| P2 | 引入任务队列 | Celery + Redis 或简单的 `arq` (async-rq) 处理 PubMed 爬取和模型重训 |
| P2 | 编写测试 | 至少覆盖 `migrate_naive.py` 的分类逻辑和 API 的核心端点 |
| P2 | Docker 化 | 提供 `Dockerfile` + `docker-compose.yml`，统一 Python/Node 环境 |
| P3 | WebSocket 推送 | 模型重训进度实时推送到前端 |
| P3 | PDF 功能激活 | 排查 PDF 归档为何无数据，让整个 PDF 上传/归档/查看链路跑通 |

---

## 文件职责速查

| 文件 | 职责 |
|---|---|
| `main.py` | PubMed 检索 + 文献入库 + naive 规则初分类 |
| `migrate_naive.py` | 规则引擎：关键词匹配 + 分类器约束策略 |
| `run_pipeline.py` | 离线重训：调用 ML pipeline 更新预测 |
| `web_app/app.py` | FastAPI 后端：CRUD、PDF 路由、标签管理 API |
| `web_app/ml_pipeline.py` | ML 模型：TF-IDF/SentenceTransformer + SVC 分类 + 标签预测 |
| `web_app/ml_report.py` | 模型性能报告生成 |
| `web_app/frontend/src/App.jsx` | React 主界面：列表、筛选、分页 |
| `web_app/frontend/src/components/AnnotationForm.jsx` | 文献标注面板 |
| `web_app/frontend/src/components/TagManager.jsx` | 标签字典管理 |
| `tags.json` | 标签本体配置（domain/technology/analysis/metaCategory） |
| `spatial_literature.db` | SQLite 主库 |
| `Makefile` | 构建/启动/停止 |

---

## 注意事项

- 当前代码中引用了两个不同的路径：`/home/zf-li23/pubmed-spatial-tracker`（当前仓库）和 `/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker`（旧位置）。所有硬编码路径需统一到前者或改用相对路径。
- `run_pipeline.py` 会先备份整个数据库到 Excel 再执行重训，操作是安全的，但覆盖写入方式存在前述并发风险。
- 修改 `tags.json` 会影响规则引擎和 ML 链路的行为，因为两者都动态加载该文件。
- 前端 AnnotationForm 提交时会自动过滤 `["聚类","去卷积","缺失值插补","细胞通讯"]` 这几个标签（第 51-52 行），这是硬编码逻辑，修改时需要知道。
