# PubMed Spatial Tracker

**PubMed Spatial Tracker** 是一个为单细胞与空间转录组学（Spatial Transcriptomics）相关文献设计的一站式检索、清洗、分类、打标与追踪平台。
本系统将经典的文献检索（基于 NCBI E-utilities）与现代人机交互打标（React + FastAPI）相结合，并通过 Active Learning 机器学习与 Naive 规则推理在后台不断自主提纯、预测文献大类与标签。通过此流水线（Pipeline），研究者能极快地复现我们的空间组学相关文献库构建工作，并平滑地将模型与工具应用到其他的细分领域。

## 📁 核心文件树结构与职能说明

```text
PubMed_Spatial_Tracker/
├── run_server.sh                       # [核心脚本] 一键启动服务器，处理前端编译验证与安全端口释放
├── run_pipeline.py                     # [核心脚本] 数据流水线重新评估入口：一键重跑 Naive 基线映射与 ML 机器学习打标
├── main.py                             # 文献抓取脚本：利用 Biothon 从 PubMed 爬取指定关键字文献，扩展本地数据库
├── migrate_naive.py                    # 朴素规则库：记录硬编码的规则（通过关键字正则或简单匹配）实现初筛
├── requirements.txt                    # Python 后端及算法环境依赖列表
├── spatial_literature.xlsx             # [核心数据库] 存储了所有已爬取文献的内容、已确认标记与分类器跑出的结果
├── tags.json                           # [本体论字典] 用户统一管理的标签（Tag）体系，供全系统渲染与下拉选择
├── template.xlsx                       # 原始文献数据库结构模板
├── PDF_Archive/                        # 本地文档存储库：存放用户通过工具上传到本地的原始 PDF 副本
└── web_app/                            # 交互式网页主程序目录 (FastAPI + React)
    ├── app.py                          # 后端主程序与 API 路由定义 (基于 FastAPI)
    ├── ml_pipeline.py                  # 机器学习分类流水线 (Active Learning, TfidfVectorizer, 逻辑回归 等)
    ├── ml_report.py                    # 模型验证与评估指标报告生成脚本 -> 生成 ML_Performance_Report.csv
    └── frontend/                       # 前端源码 (React + Vite + TailwindCSS)
```

## 🚀 快速上手 (Quick Start)

### 1. 环境准备
确保您的机器安装了 `conda` 并且已带有 Python 3 和 Node.js 环境：
```bash
# 激活您的工作环境
conda activate zf-li23 

# 安装 Python 相关依赖
pip install -r requirements.txt

# 安装前端依赖
cd web_app/frontend
npm install
cd ../../
```

### 2. 数据爬取流水线 (Data Fetching Pipeline)
若要更新核心文献库或补充新的领域文章：
1. 编辑/浏览 `main.py` 以确认您的 API 调用关键字（如 "spatial transcriptomics"）。
2. 执行由于增量合并：
```bash
python main.py
```
这会自动把抓取下来的最新论文按标题去重并追加入 `spatial_literature.xlsx`。

### 3. 数据推理流水线 (Prediction Pipeline)
当你引入了新文献（还未人工标注），或者在前端新增了手动标签想要重训模型时，随时可以重跑流水线：
```bash
python run_pipeline.py
```
流水线干了两件事：
- **Naive 判断**：对库内文章做基于 `migrate_naive.py` 硬规则逻辑推断（如含有 Review 关键字则标为 Review）。
- **ML 机器学习预测**：抽取了您 `is_manually_confirmed == True` 的数据作为金标准重训模型，并对库中所有无人工标签的文献给出 `auto_predicted` 判断（包括独立二分类预测该文献是不是垃圾/废弃文献 Discarded）。

### 4. 交互式可视化打标平台 (Interactive Annotation)
为了以最佳体验确认分类并进行数据清洗：
```bash
bash run_server.sh
```
该指令会自动编译所有的 React UI，安全地关闭过往僵尸进程，并在本地 http://localhost:8000 提供服务。

---

## 📖 API 通信接口文档 (Backend APIs)

系统后端使用了 `FastAPI`，将对所有 JSON 数据状态以及前端的行为操作负责。

| 路由地址 (Endpoint) | HTTP 方法 | 功能描述 | 请求参数 / Body |
| :--- | :--- | :--- | :--- |
| `/api/articles` | GET | 获取库中所有文章数据以供渲染，携带已有的 ML 预测结果与人工修正基准。包含分页信息。 | `page`, `limit` |
| `/api/articles/{pmid}/annotate` | POST | 当你在右侧信息面板修改某一篇文章并保存时调用，后端将其标志位更新为确认为 `is_manually_confirmed=True`，并持久化到 Excel 中。 | `{ category: string, tags: string }` |
| `/api/articles/{pmid}/discard` | POST | 在界面的快捷动作，直接将一条无用的数据标记为 `Discarded` 废弃。模型以此用作负样本监督。 | 无 |
| `/api/tags` | GET | 抓取本项目所管理运行的所有全局 `tags.json` 中的本体字典树。 | 无 |
| `/api/tags` | POST | 覆写全局的 `tags.json`。 | `{ metaCategory:[], domain:[] ... }` |
| `/api/tags/rename` | PUT | 当重命名某个 tag 时不仅修改 JSON，还自动**溯源遍历数据库，把 Excel 里所有旧 tag 批量置换为新 tag**。 | `{ old_tag: string, new_tag: string }`|
| `/api/tags/delete` | DELETE | 从 JSON 中彻底删除 Tag，并清理清洗数据库该遗留项。 | `{ tag: string }` |
| `/api/ml/active_learning` | POST | 前端手动触发重训，对目前标注的数据情况调用 `ml_pipeline` 再训练并同步内存缓存。 | 无 |

---

## 🛠 关键函数与模块说明 (Core Python Functions)

### A. 标签管理分类器 (`web_app/ml_pipeline.py`)
- **`AutomatedActiveLearner.fit(train_df)`**
  通过接收人工矫正的数据(train_df)，抽取出包含摘要与标题的增强字段（`augment_text`）向量化（Tfidf），训练主 Category 和多标签的二分类与多标签回归器。**其中，是否包含 `Discarded` 作独立的平衡树判断**，保证废弃不影响模型正常领域的理解学习。
  
- **`AutomatedActiveLearner.predict(pred_df)`**
  接受带有基准 Naive 标签的数据，产出 `pred_cats` 与 `pred_tags` 的置信结果供前台 UI 作为辅助显示。

### B. 逻辑重映射机制 (`migrate_naive.py`)
- **`get_naive(title, abstract, journal)`**
  基础兜底过滤逻辑。遍历系统的字典集（即 `tags.json` 内储存的标签），逐字转小写后与 Title 和 Abstract 匹配并硬编码赋给类别。

### C. 数据库管理器 (`web_app/app.py` 的关键逻辑)
- **`save_df(df)`**
  系统底层统一封装了无冲突文件存储写入逻辑，保证前台点击多重触发下不会破坏原始的 `spatial_literature.xlsx` 内部数据。
