# Experiments

本目录存放项目中的**可复现实验**。每个实验独立编号，包含完整代码、说明和结果。

## 规范

每个实验是一个独立子目录 `NNN_experiment_name/`，包含：

```
NNN_experiment_name/
├── README.md          # 实验目的、方法、结论
├── run.sh             # 一键运行脚本（bash ./run.sh 即复现）
├── {script}.py        # 实验代码
└── results/           # 输出结果存放处
```

## 原则

1. **可复现** — `bash run.sh` 即复现全部结果，无需手动操作
2. **自包含** — 实验脚本可独立运行；若需要引用 `src/` 中的代码，通过 `sys.path` 或 `PYTHONPATH` 引入
3. **不提交产物** — `results/` 中的输出文件应加入 `.gitignore`（但保留 `results/.gitkeep` 使目录结构入仓）
4. **记录原始数据** — 关键中间结果（如检索 ID 列表、计数）保存为 CSV/JSON，供后续报告使用
5. **迭代编号** — 新实验按顺序编号 `NNN_`，避免冲突

## 实验清单

| 编号 | 名称 | 目的 | 状态 |
|---|---|---|---|
| 001 | query_analysis | PubMed 检索式设计 & 各字段对比 | ✅ 完成 |
