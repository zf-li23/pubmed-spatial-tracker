# PubMed Spatial Transcriptomics Literature Tracker

## 🌟 项目背景与简介 (Project Background)
本项目是一个专为高通量筛选、管理、标注与机器学习预分类**空间转录组学（Spatial Transcriptomics）**文献而设计的自动化智能追踪工作站。

在海量的 PubMed 进展中，Research人员经常面临**检索量大、分类繁杂、缺乏负样本积累、打标成本极高**等痛点。本项目通过前后端分离的架构与 **主动学习 (Active Learning)** 闭环机制，搭建了从“自动爬虫抓取”到“界面交互标注”，再到“AI 滚动预测”和“无纸化文件/外链留存”的全链路解决方案。非常适合作为课程作业级、可落地的科研提效平台。

---

## 🛤️ 版本迭代历程 (Version Iterations)
这个项目经历了三次极具代表性的大跨度重构，从一个干瘪的脚本进化为了全栈顺滑标注打卡流：

* **v1.0：刀耕火种的爬虫时代**
  起始于纯 Python 脚本（`Biopython` + `Pandas`）。最初的设想只是抓取 PubMed 上的空间组学文献并保存在 Excel 表格中，辅以简单的本地 PDF 下载功能。
  *痛点*：人工在 Excel 里手动修改分类标签极其痛苦且极易覆写错乱；上千篇文献如果全靠手动看摘要打标，工作量堪称灾难；批量下载 PDF 迅速占满了硬盘。

* **v2.0：前后端分离与 Active Learning 觉醒**
  引入了 `FastAPI` 和 `React` 构建可视化工作站。面对海量未标注文献，我们引入了**“Human-in-the-loop (人在回路)”**的主动学习（Active Learning）核心理念。
  *突破*：文献从一开始就被算法按照 $50, 100, 200...$ 的几何倍数切割成递增批次（Batch）。用户只需纯手工打标 Batch 1，随后一键呼叫 `Scikit-learn` 的 TF-IDF + 朴素贝叶斯进行训练，让 AI 自动给 Batch 2 预测大类（Category）。极大地降低了人工疲劳，并新增了 `is_manually_confirmed` 字段，做到了不论底层爬虫怎么更新，人类的心血均被完美保护 100% 免疫覆盖。

* **v3.0：极致体验的工程化狂飙 (当前版本)**
  系统迈入生产级流程优化，专注解决细粒度操作与盘面冗余：
  * **存储解耦**：彻底剥离了沉重的 PDF 落盘逻辑。新增轻量级的无纸化 `URL 🔗` 仅存链接选项，大幅释放本地磁盘空间。
* **模型升维与元特征扩充**：除了 `title` 和 `abstract`，现在的特征提取管线（Pipeline）已全面吸纳了 `pub_year` (年份)、`journal` (期刊)、`mesh_terms` (MeSH主题词) 与 `keywords` (作者关键字) 等更丰富的文献属性。AI 预测更加精准，并生成兼具 大类准确率 (Category Accuracy) 与 细标 Macro/Micro F1-Score 动态指标的深度 `ML_Performance_Report.csv` 报告。
  * **精准定向干预与非CNS清洗**：新增了通过批量 `.txt` 直接注入指定 PMID (补齐长尾小众文章) 的定向下载能力。重塑了主动学习分类器逻辑，在每次推进预测下批文献时，所有预测为“研究”类的非 CNS（Cell/Nature/Science）正刊文献都会被策略性打入极远期批次（如 `Batch 999`），从而让您优先审核更有价值的顶级文献或算法技术类文章。
  * **乐观 UI 单手盲操**：前端加入了 **Optimistic Updates (乐观更新)** 设计。只要前台轻点“提交”，请求立刻发往后台静默处理，而用户的界面会瞬间无缝自动“吸附”并跳转至下一条未确认记录。零阻尼、免刷新的心流体验让高通量人工校验变成了享受。

---

## 🏗️ 核心架构与Technology栈 (Architecture & Tech Stack)
* **数据抓取与持久化**：`Biopython (Entrez)` + `Pandas`。爬区增量更新，完美保护人工修改的心血，绝不覆盖已有校验数据。
* **后端引擎与机器学习 API**：`FastAPI` + `Uvicorn` + `Scikit-learn`。内置 TF-IDF 文本向量化与 MultinomialNB（多项式朴素贝叶斯）机器学习流水线。
* **前端交互界面**：`Vite` + `React 19` + `TailwindCSS`。工程化前端架构，分页渲染丝滑流畅，支持乐观 UI 状态更新（免刷新极速响应）。

---

## ✨ 核心功能流 (Core Features)

### 1. 🤖 Active Learning 自动标注与人工校验闭环 (Human-in-the-Loop)
通过机器与人类的交互循环，极大降低上千篇文献的人工打标成本：
* **递增批次切分**：底表已被智能分片为不断几何递增的编组（第一批 50篇，第二批 100篇，之后200, 400...）。
* **学习与预测体系**：
  * 您只需要在网页端专注于手工精标当前批次（如 `Batch 1`）。
  * 标完后点击右上角 **"🚀 AI 本地学习并预测下批"**，系统将调用专用的机器学习端点，利用完全干净的已标注批次（如 Batch 1）训练基线分类器和标签预测器。
  * **双轨预测**：不仅预测“文章大类 (Category)”，还会直接预测几十种组合的“细分标签 (Tags)”，并在表格中对机器修改前后的痕迹打上小扳手 `🔧` 图标供您追踪。
* **严格性能报告**：每次触发 AI 学习时，系统会在根目录输出并追加 `ML_Performance_Report.csv`，真实反映由零碎小样本积累至大样本时，准确率 (Accuracy)、查准率与召回率的动态爬坡表现。

### 2. 💡 绝不覆写的增量爬取保护
当您在底层重新运行爬虫查漏补缺时：
* 含有 `"is_manually_confirmed": True` 的任何数据均获得最高保护优先级（免疫所有字段和行列覆盖）。
* 在前端被您判定为无用/假阳性的论文不再被物理删除，而是标记为 `Discarded` 并转存保留。这为我们的文本挖掘留下了至关重要的**负样本（Negative Samples）**环境。

### 3. 🔗 存储空间友好的链接留存机制 (Local PDF & URL External Links)
为了防止大量 PDF 塞满您的物理硬盘，系统现提供两种双源入库方式：
* **轻量🔗留存 (仅存链接)**：通过表单直接记录论文的外链 URL。表格中会以青色 `🔗 外链` 展示，点击直达外部站点，完美节省个人本地存储。
* **深度📥归档 (同时存 PDF)**：在填报了源链接后即可将电脑里的原件拖拽进系统，系统将以严格的格式：`[pub_year]_[tags]_[doi].pdf` 帮您对其在本地重命名并分类建档，并向表格渲染蓝色 `👁 查看`。

---

## 🗃️ Database结构字典 (Data Schema)
生成的 `spatial_literature.xlsx` 包含以下核心维护字段：

| 顺序 | 字段名 | 类型 | 说明 |
|----|--------|------|------|
| 1 | `pmid` | str | PubMed唯一标识符，主键 |
| 2 | `doi` | str | 论文数字对象唯一标识符 |
| 3 | `url` | str | **(新增)** 原始或下载来源的外链 URL |
| 4 | `title` | str | 论文标题 (用于 NLP 特征提取) |
| 5 | `abstract` | str | 摘要 (用于 NLP 特征提取) |
| 6 | `pub_year` | str/int | 发表年份 |
| 7 | `journal` | str | 期刊名称 |
| 8 | `category` | str | 主类别：Review / Technology / Data Analysis / Research等 |
| 9 | `tags` | str | 用分号分隔的自动标注/人工修改细分标签 |
| 10 | `is_manually_confirmed`| bool | (核心) 是否经人工确认。置 `True` 后免疫更新覆盖 |
| 11 | `pdf_path` | str | 本地文献绝对归档路径 |
| 12 | `annotation_batch` | int | Active Learning **递增标注批次号** (1, 2, 3...) |
| 13 | `auto_predicted_category`| str | 机器自动预测的大类，方便追踪 AI 原始预判 |
| 14 | `auto_predicted_tags` | str | 机器自动预测的组合标签 |

*(注：其他爬虫抓取的辅助字段如 mesh_terms, keywords 亦会平级保留)*

---

## 🚀 快速上手与操作指南 (Getting Started)

### 1. 环境准备
确保拥有 `Python >= 3.8` (推荐 conda 环境) 及 `Node.js`。
```bash
pip install -r requirements.txt
# 必需库中包含：fastapi, uvicorn, pandas, scikit-learn, biopython, openpyxl等
```

### 2. 爬虫获取文献 (可选)
如果需要执行初轮拉取或定期新增查漏补缺：
```bash
python main.py
```
> *爬虫会自动分配未处理的数据到接续的编组批次中，且已标注的数据会被 100% 保护。*

### 3. 编译现代前端界面 (Vite Build)
若您是对前端有过修改的开发者：
```bash
cd web_app/frontend
npm install
npm run build
```

### 4. 开启工作站服务器
在 `web_app/` 目录下冷启动 FastAPI：
```bash
cd web_app
python app.py
```
打开浏览器访问：[http://localhost:8000](http://localhost:8000)

### 5. 标准人工-AI交替标定工作流
1. 网页载入后，在右上角漏斗中筛选出 `Batch 1`。
2. 逐一点击列表并浏览下方侧边栏论文细节，点击 `🔗 仅存链接` 保存外部地址，或者拖拽本地 PDF 进行归档，提交结果。
3. 当所有 `Batch 1` 数据完成标定后，点击页面右上角的：**"🚀 AI 本地学习并预测下批"**。
4. 转至后端控制台或页面提示，查看生成的模型准确度评价。再去查看被机器提前打好初标的 `Batch 2`，反复打磨和确认，让系统越学越聪明！


### 新增进阶特性 (Advanced Features v3.1)
- **多维度元数据特征提取**：机器学习分类器的输入 `Text` 现已全面整合并吸收了文献的 `pub_year` (发表年份), `journal` (期刊全称), `mesh_terms` (MeSH 医学主题词) 以及 `keywords` (作者自定义关键词) 等特征。大大增强了文本的表征能力。
- **严格匹配与非CNS隔离清洗**：为了避免繁杂零碎的普通文献污染核心前沿综述与工具评估，我们将基于 `Research` 类别的文章增加了最严格的顶刊匹配（严卡 `"Nature"`, `"Cell"`, `"Science (New York, N.Y.)"`，完全杜绝诸如 *Nature communications* 等子刊带来的假阳性），未命中的非顶刊 `Research` 原文会自动在预测时被置入 `Batch 999` 等极远期搁置批次，保证了早期人工校对池的极致精华度与纯净度。
- **详尽指标度量跟踪**：通过动态累加输出 `ML_Performance_Report.csv` 文件，全面跟进并记录当批数据的 `Macro F1-Score` 与 `Micro F1-Score`，辅助评估小众标签学习效果。

## Recent Updates
- Centralized tag groups via `tags.json` for frontend, crawler, and ML pipeline.
- Fixed active learning category bug and enabled priority-based Naive/AI predictions in the UI.
- Removed unused `patch*.py` scripts and temporary logic.
## Recent Updates
- Centralized tag groups via `tags.json` for frontend, crawler, and ML pipeline.
- Fixed active learning category bug and enabled priority-based Naive/AI predictions in the UI.
- Removed unused `patch*.py` scripts and temporary logic.