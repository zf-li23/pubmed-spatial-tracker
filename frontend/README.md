# PubMed Spatial Tracker — Frontend

全静态 React + Vite 前端，用于浏览、筛选和搜索 9,148 篇空间转录组学文献（DeepSeek LLM 标注）。

## 快速开始

```bash
cd frontend

# 1. 安装依赖（仅首次）
npm install

# 2. 转换 CSV 数据（仅首次，或数据更新后）
python3 scripts/convert_csv.py

# 3. 启动开发服务器
npm run dev
# → 浏览器打开 http://localhost:5173

# 4. 生产构建
npm run build
# → 静态文件输出到 dist/
```

## 功能

| 功能 | 说明 |
|---|---|
| **紧凑浏览表格** | 7 列：Title / Year / Category / Tags / Technology / Bio Topic / Indicators |
| **文章详情页** | 点击标题进入，展示 PMID/DOI/Journal + Abstract + MeSH Terms + Keywords + LLM 标注 |
| **全局搜索** | 按 PMID、Title、DOI 实时搜索 |
| **多维度筛选** | Year / Category / Tags / Technology / Biological Topic / Journal |
| **PubMed 跳转** | 详情页 PMID 链接 → `https://pubmed.ncbi.nlm.nih.gov/{pmid}/` |
| **DOI 跳转** | 详情页 DOI 链接 → `https://doi.org/{doi}` |
| **小徽章** | 📊 Data（有新数据）、💻 Code（有新方法/工具）、置信度标签 |
| **分页** | 50 条/页，支持快速翻页 |

## 数据流程

```
annotated_articles.csv  ──┐  (LLM 标注：category/tags/technology/...)
                          ├── scripts/convert_csv.py ──→ public/data/articles.json
articles.csv           ──┘  (PubMed 元数据：abstract/mesh_terms/keywords)
```

以 PMID 为键合并两个 CSV，生成包含全部字段的 JSON（9,148 条，约 19 MB）。

## 技术栈

- React 18 + TypeScript
- Vite 6
- 纯 CSS（无 UI 框架依赖）

## 数据来源

`public/data/articles.json` 由 `scripts/convert_csv.py` 从 `data/spatial_tracker/annotated_articles.csv` 生成，包含全部 9,148 篇文献的 LLM 标注信息。
