# PubMed Spatial Tracker

PubMed Spatial Tracker 是一个面向空间转录组相关文献的检索、标注、归档与主动学习系统。

系统目标：
- 高质量维护空间组学文献库
- 支持“规则初始化 + 人工修正 + 主动学习”闭环
- 支持 PDF 本地归档与外链追踪
- 支持可复现的手工补充 PMID 记录

## 1. 技术栈

- Backend: FastAPI + SQLite(SQLAlchemy)
- Frontend: React + Vite + Tailwind CSS
- ML: scikit-learn（默认）+ sentence-transformers（可选增强）
- Data: pandas + biopython(Entrez)

## 2. 项目结构与文件职责

```text
PubMed_Spatial_Tracker/
├── main.py
├── run_pipeline.py
├── migrate_naive.py
├── requirements.txt
├── Makefile
├── spatial_literature.db
├── tags.json
├── PDF_Archive/
└── web_app/
    ├── app.py
    ├── ml_pipeline.py
    ├── ml_report.py
    └── frontend/
        ├── package.json
        ├── vite.config.js
        └── src/
            ├── App.jsx
            └── components/
                ├── AnnotationForm.jsx
                └── TagManager.jsx
```

关键文件说明：

- `main.py`
  - 从 PubMed 拉取文献并增量写入主库
  - 使用 `migrate_naive.py` 给新文献打初始类别/标签

- `run_pipeline.py`
  - 触发离线/批处理重训流程
  - 用人工确认样本更新模型并刷新自动推断

- `migrate_naive.py`
  - 规则系统（关键词 -> 类别/标签）
  - 用于冷启动和兜底分类

- `web_app/app.py`
  - FastAPI 后端入口
  - 负责 API、数据库读写、PDF 路由、标签管理

- `web_app/ml_pipeline.py`
  - 主动学习和预测逻辑
  - 提供拟合与推断能力

- `web_app/frontend/src/App.jsx`
  - 主界面（列表、筛选、分页、导入、触发重训）

- `web_app/frontend/src/components/AnnotationForm.jsx`
  - 单篇文献标注面板
  - 处理分类/标签提交、PDF 上传、URL 抓取、仅存链接

- `tags.json`
  - 标签字典配置，驱动前端标签组与规则系统

- `spatial_literature.db`
  - 主数据库文件（建议定期备份）

## 3. 环境准备

推荐版本：
- Python 3.10+
- Node.js 20.19+（Vite 8 需要）

安装依赖：

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
- 未安装 `sentence-transformers` 时，系统自动回退到 TF-IDF 向量，不影响主动学习流程可用性。
- 该默认配置适合无 NVIDIA 显卡的 CPU 环境。
- 模型下载已默认走 `HF_ENDPOINT=https://hf-mirror.com`，适合常见国内网络环境。

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
- 与现有库合并（避免重复）
- 生成 naive 初始标签

### 5.2 重训与推断

```bash
python run_pipeline.py
```

行为：
- 使用 `is_manually_confirmed=1` 样本训练
- 更新未确认样本的自动预测和不确定性分数

### 5.3 人工标注工作流

在 Web 界面中可执行：
- 分类与标签提交
- Discarded 负样本标记
- 本地 PDF 上传归档
- URL 抓取 PDF
- 仅保存 URL 外链
- 导入 PMID 列表（TXT 每行一个 PMID）

### 5.4 分类器复杂逻辑（ML 与 Naive 已对齐）

以下是你之前定义的“类别-标签约束”规则，当前已在两条链路中统一：

- ML 预测链路：`web_app/ml_pipeline.py`
- Naive 冷启动链路：`migrate_naive.py`（通过 `enforce_category_tag_policy(...)`）

规则清单：

- Review
  - 标签仅允许来自 `metaCategory` 或 `domain`
  - 最终保留 1 个标签（兜底可回退到 `General`）

- Technology
  - 优先从 `technology` 标签组选择
  - 若无命中，尝试从标题提取新技术名（例如 `XXX:` 前缀）
  - 仍无命中时回退到技术组默认标签

- Database
  - 优先提取标题中的新命名实体作为数据库名
  - 无法提取时保留少量已有候选标签

- Data Analysis
  - 以 `analysis` 标签组为主（限制上限）
  - 可附加标题里提取出的新方法名

- Research
  - 至少包含 1 个 `domain` 标签
  - 可附加 `technology` 标签

- Discarded 逻辑
  - 在 ML 中作为独立二分类信号，不与普通标签共享同一判别空间
  - 在人工流程中作为特殊标签反馈进入训练集

- 提交时标签清洗
  - 前端提交时会过滤一组高频流程词标签（如聚类、去卷积、缺失值插补、细胞通讯），降低训练噪声

## 6. 手工导入 PMID 的可复现机制

当前机制：
- 通过 `/api/pmids/upload` 导入的 PMID 会写入数据库表 `manual_imported_pmids`
- 不再依赖项目根目录的文本文件

`manual_imported_pmids` 表字段：
- `pmid` TEXT PRIMARY KEY
- `source` TEXT（默认 `manual_upload`）
- `imported_at` TEXT（写入时间）

用途：
- 追踪“检索式外”人工补录文献
- 保障补录来源可追溯与可复现

## 7. API 文档（详细）

### 7.1 文献查询与标注

- `GET /api/articles`
  - 功能：返回全部文献记录
  - 特点：后端按“未确认优先 + 不确定性降序”排序
  - 返回：`List[ArticleRecord]`

- `POST /api/articles/{pmid}/annotate`
  - 功能：提交分类与标签，并标记为人工确认
  - Body:
    ```json
    { "category": "Research", "tags": "Neuroscience; Visium" }
    ```

- `POST /api/articles/{pmid}/discard`
  - 功能：将文献打为 Discarded 负样本并标记为人工确认

### 7.2 PMID 导入

- `POST /api/pmids/upload`
  - 功能：上传 TXT 并抓取新增 PMID
  - 上传：`multipart/form-data`，字段 `file`
  - 说明：每行一个数字 PMID

### 7.3 PDF 与链接

- `POST /api/articles/{pmid}/pdf/upload`
  - 功能：上传本地 PDF，并写入归档路径
  - 上传：`multipart/form-data`
  - 关键字段：`file`, `category`, `tags`, `doi`, `pub_year`, `url`

- `POST /api/articles/{pmid}/pdf/url`
  - 功能：尝试从 URL 拉取 PDF 并归档
  - Body:
    ```json
    {
      "url": "https://...",
      "category": "Review",
      "tags": "Data Analysis",
      "doi": "10.xxxx/xxxx",
      "pub_year": "2024"
    }
    ```

- `POST /api/articles/{pmid}/pdf/save_link`
  - 功能：仅保存 URL 外链，不下载 PDF

- `GET /pdf?path=...`
  - 功能：读取归档 PDF 文件

### 7.4 标签体系

- `GET /api/tags`
  - 功能：读取标签字典（`tags.json`）

- `POST /api/tags`
  - 功能：整体更新标签字典

- `PUT /api/tags/rename`
  - 功能：重命名标签并批量替换数据库中的旧标签
  - Body:
    ```json
    { "old_tag": "Old", "new_tag": "New" }
    ```

- `DELETE /api/tags/delete`
  - 功能：删除标签并清理数据库中的该标签
  - Body:
    ```json
    { "tag": "ToDelete" }
    ```

### 7.5 主动学习

- `POST /api/ml/active_learning`
  - 功能：触发重训并刷新自动推断
  - 返回：状态消息（如 `success`, `need_data`, `done`）

## 8. 重要函数与对象文档

### 8.1 `web_app/app.py`

- `get_df()`
  - 从 `literature` 表读取完整 DataFrame

- `save_df(df)`
  - 将 DataFrame 回写到 `literature`（replace）
  - 会重建 `pmid` 索引
  - 注意：属于全表写回操作，改动前建议备份数据库

- `ensure_manual_import_table()`
  - 确保 `manual_imported_pmids` 表存在

- `record_manual_imported_pmids(pmids, source="manual_upload")`
  - 批量写入手工导入 PMID（`INSERT OR IGNORE`）

- `safe_filename(name)`
  - 清理归档文件名，过滤非法字符

### 8.2 `main.py`

- `fetch_pubmed(email, query, max_results)`
  - 执行 Entrez 检索与批量下载

- `parse_article(record)`
  - 从 PubMed XML 记录解析结构化字段

- `classify_article(parsed_data)`
  - 调用 `migrate_naive.get_naive` 进行规则分类

### 8.3 `web_app/ml_pipeline.py`

- `AutomatedActiveLearner.fit(train_df)`
  - 训练分类与标签模型

- `AutomatedActiveLearner.predict(pred_df)`
  - 输出类别预测、标签预测和不确定性分数

### 8.4 `migrate_naive.py`

- `get_naive(title, abstract, journal)`
  - 规则匹配后得到初始类别与标签
  - 再应用统一后处理策略，保证与 ML 的标签约束一致

- `enforce_category_tag_policy(category, tags, title="")`
  - 执行“类别 -> 合法标签域”约束
  - 用于避免 naive 与 ML 输出风格漂移

## 9. 常见故障与排查

- URL 拉取 PDF 返回 400
  - 常见原因：目标站点返回 HTML（登录页/验证码/反爬）
  - 建议：改为本地上传，或先保存外链

- `make run` 报 Node 版本错误
  - Vite 8 需要 Node 20.19+

- 标注后页面行为异常
  - 先点“刷新列表”对账数据库
  - 再看浏览器 Network 与后端日志

## 10. 维护建议

- 对 `spatial_literature.db` 做周期性备份
- 对 `tags.json` 改动走 Git 审核
- 修改字段时保持前后端字段命名一致
- 涉及批量写表逻辑时先做数据库快照
