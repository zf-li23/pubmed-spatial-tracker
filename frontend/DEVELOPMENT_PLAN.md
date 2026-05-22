# PubMed Spatial Tracker — 前端开发规划

## 概述

为 `data/spatial_tracker/annotated_articles.csv`（9,148 篇空间转录组学文献，LLM 标注）构建全静态 React + Vite 前端，提供便捷的浏览、筛选、搜索与跳转功能。

## 技术选型

| 层 | 技术 | 原因 |
|---|---|---|
| 框架 | React 18 + TypeScript | 类型安全，组件化 |
| 构建 | Vite 5 | 快速 HMR，静态导出友好 |
| 样式 | CSS Modules | 零依赖，作用域隔离 |
| 数据 | 静态 JSON（CSV→JSON 预处理脚本） | 无后端，fetch 即用 |
| 状态 | React useState/useMemo | 轻量，无需状态管理库 |

## 组件树

```
App
├── Header（标题 + 统计摘要）
├── SearchBar（全局搜索：PMID / Title / DOI）
├── FilterPanel
│   ├── YearFilter（多选 checkbox，2016-2026）
│   ├── CategoryFilter（checkbox 组，6 项）
│   ├── TagFilter（checkbox 组，15 项）
│   ├── TechnologyFilter（checkbox 组，24 项）
│   ├── BiologicalTopicFilter（checkbox 组，17 项）
│   └── JournalFilter（搜索式多选，1,425 项）
└── DataTable
    ├── Pagination（50 条/页）
    └── Row（每行含 Badge 组件）
```

## 列设计

| 列 | 展示方式 | 交互 |
|---|---|---|
| PMID | 可点击链接 | → `https://pubmed.ncbi.nlm.nih.gov/{pmid}/` |
| Title | 文本（截断+悬停全显） | — |
| DOI | 可点击链接 | → `https://doi.org/{doi}` |
| Year | 文本 | 筛选器联动 |
| Journal | 文本（斜体） | 筛选器联动 |
| Category | 彩色标签 | 筛选器联动 |
| Tags | 小型标签列表 | 筛选器联动 |
| Technology | 小型标签列表 | 筛选器联动 |
| Biological Topic | 文本 | 筛选器联动 |
| Has New Data | 🟢 小徽章（True 时显示） | — |
| Has Code | 🔵 小徽章（True 时显示） | — |
| Confidence | 🟡/🟢/🔴 小徽章（high/medium/low） | — |

不展示 `is_preprint`（数据中仅 2 条 True，不准确）。

## 数据流

```
annotated_articles.csv
    ↓ [scripts/convert_csv.py]
public/data/articles.json  (~8-12 MB，加载后常驻内存)
    ↓ [fetch at runtime]
React state (Article[])
    ↓ [useMemo filtered by search + filters]
filtered Articles[]
    ↓ [pagination slice]
displayed Articles (50/page)
```

## 筛选逻辑

- **搜索框**：对 `pmid`、`title`、`doi` 做大小写不敏感的包含匹配
- **列筛选器**：各维度取**交集**（AND 逻辑），同类多选取**并集**（OR 逻辑）
- **实时筛选**：每次修改即时更新结果

## 文件结构

```
frontend/
├── DEVELOPMENT_PLAN.md        # 本文档
├── README.md                  # 使用说明
├── package.json
├── tsconfig.json
├── vite.config.ts
├── index.html
├── scripts/
│   └── convert_csv.py         # CSV → JSON 转换脚本
├── public/
│   └── data/
│       └── articles.json      # 转换后的数据（.gitignore）
└── src/
    ├── main.tsx
    ├── App.tsx
    ├── App.css
    ├── types.ts               # TypeScript 类型定义
    ├── utils.ts               # 筛选/搜索工具函数
    └── components/
        ├── Header.tsx
        ├── SearchBar.tsx
        ├── FilterPanel.tsx
        ├── DataTable.tsx
        ├── Badge.tsx
        └── Pagination.tsx
```

## 开发步骤

1. ✅ 数据分析与规划
2. ⬜ 初始化 Vite + React + TS 项目
3. ⬜ 编写 CSV→JSON 转换脚本并运行
4. ⬜ 实现类型定义与数据加载
5. ⬜ 实现 SearchBar + FilterPanel
6. ⬜ 实现 DataTable + Badge + Pagination
7. ⬜ 整体样式美化（PubMed 风格）
8. ⬜ 构建测试 & 文档

## 运行方式

```bash
cd frontend
npm install
python3 scripts/convert_csv.py   # 生成 public/data/articles.json
npm run dev                       # 开发服务器 localhost:5173
npm run build                     # 生产构建 → dist/
```
