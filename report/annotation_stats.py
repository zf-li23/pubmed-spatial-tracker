#!/usr/bin/env python3
"""Step 2 续：标注统计分析 — 生成标签分布报告与可视化数据。"""
import csv
import json
from collections import Counter
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data/spatial_tracker"
OUT = Path(__file__).resolve().parent / "annotation_stats.json"

# 读取标注数据
rows = []
with open(DATA / "annotated_articles.csv") as f:
    reader = csv.DictReader(f)
    for r in reader:
        rows.append(r)

report = {"total": len(rows)}

# ── 类别分布 ──
cats = Counter(r["category"] for r in rows)
report["category_distribution"] = dict(cats.most_common())

# ── 置信度分布 ──
conf = Counter(r["confidence"] for r in rows)
report["confidence_distribution"] = dict(conf.most_common())

# ── 标签频次 ──
all_tags, all_tech, all_bio = [], [], []
for r in rows:
    all_tags.extend(t.strip() for t in r.get("tags", "").split(";") if t.strip())
    all_tech.extend(t.strip() for t in r.get("technology", "").split(";") if t.strip())
    all_bio.extend(t.strip() for t in r.get("biological_topic", "").split(";") if t.strip())

report["analysis_tags_top20"] = dict(Counter(all_tags).most_common(20))
report["technology_tags_top20"] = dict(Counter(all_tech).most_common(20))
report["biological_topics_top20"] = dict(Counter(all_bio).most_common(20))

# ── 标签共现（分析标签 × 类别） ──
cat_tag = Counter()
for r in rows:
    for t in r.get("tags", "").split(";"):
        t = t.strip()
        if t:
            cat_tag[(r["category"], t)] += 1
report["category_tag_cooccurrence"] = {
    f"{c}×{t}": v for (c, t), v in cat_tag.most_common(30)
}

# ── 每年分布 ──
years = Counter(r["pub_year"] for r in rows)
report["year_distribution"] = dict(sorted(years.items()))

# ── 每篇文章标签数分布 ──
n_tags = [len([t for t in r.get("tags","").split(";") if t.strip()]) for r in rows]
tag_count_dist = Counter(n_tags)
report["tags_per_article"] = {
    "min": min(n_tags), "max": max(n_tags),
    "mean": round(sum(n_tags) / len(n_tags), 2),
    "median": sorted(n_tags)[len(n_tags)//2],
    "distribution": dict(sorted(tag_count_dist.items()))
}

# ── 数据可用性 ──
has_data = Counter(r["has_new_data"] for r in rows)
has_code = Counter(r["has_code"] for r in rows)
preprint = Counter(r["is_preprint"] for r in rows)
report["data_availability"] = {
    "has_new_data": dict(has_data),
    "has_code": dict(has_code),
    "is_preprint": dict(preprint),
}

# ── 类别 × 置信度 ──
cat_conf = Counter()
for r in rows:
    cat_conf[(r["category"], r["confidence"])] += 1
report["category_confidence"] = {
    f"{c}×{cf}": v for (c, cf), v in cat_conf.most_common()
}

with open(OUT, "w") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)
print(f"✅ 标注统计报告 → {OUT}")
print(f"\n{'='*60}")
print(f"  总文献数: {report['total']}")
print(f"  类别数: {len(report['category_distribution'])}")
print(f"  分析标签数: {len(all_tags)} 条, {len(set(all_tags))} 唯一")
print(f"  技术标签数: {len(all_tech)} 条, {len(set(all_tech))} 唯一")
print(f"  生物学领域: {len(all_bio)} 条, {len(set(all_bio))} 唯一")
print(f"  平均每篇标签数: {report['tags_per_article']['mean']}")
print(f"{'='*60}")

# ── 同时输出简易 Markdown 表格 ──
md = OUT.with_suffix(".md")
with open(md, "w") as f:
    f.write("# 标注统计分析报告\n\n")
    f.write(f"总文献数: **{report['total']}** 篇\n\n")
    f.write("## 类别分布\n\n| 类别 | 数量 | 占比 |\n|---|---|---|\n")
    for k, v in report["category_distribution"].items():
        f.write(f"| {k} | {v} | {v/report['total']*100:.1f}% |\n")
    f.write("\n## 置信度分布\n\n| 置信度 | 数量 | 占比 |\n|---|---|---|\n")
    for k, v in report["confidence_distribution"].items():
        f.write(f"| {k} | {v} | {v/report['total']*100:.1f}% |\n")
    f.write("\n## 分析标签 Top 20\n\n| 标签 | 频次 |\n|---|---|\n")
    for k, v in list(report["analysis_tags_top20"].items())[:20]:
        f.write(f"| {k} | {v} |\n")
    f.write("\n## 技术平台 Top 20\n\n| 平台 | 频次 |\n|---|---|\n")
    for k, v in list(report["technology_tags_top20"].items())[:20]:
        f.write(f"| {k} | {v} |\n")
    f.write("\n## 生物学领域 Top 20\n\n| 领域 | 频次 |\n|---|---|\n")
    for k, v in list(report["biological_topics_top20"].items())[:20]:
        f.write(f"| {k} | {v} |\n")
    f.write(f"\n## 标签密度\n\n")
    f.write(f"- 每篇标签数: 均值 {report['tags_per_article']['mean']}, ")
    f.write(f"中位数 {report['tags_per_article']['median']}, ")
    f.write(f"范围 [{report['tags_per_article']['min']}, {report['tags_per_article']['max']}]\n")
    f.write(f"- 有新数据的文献: {report['data_availability']['has_new_data'].get('True', 0)}/{report['total']}\n")
    f.write(f"- 附代码的文献: {report['data_availability']['has_code'].get('True', 0)}/{report['total']}\n")

print(f"✅ Markdown 报告 → {md}")
