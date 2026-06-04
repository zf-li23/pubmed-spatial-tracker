#!/usr/bin/env python3
"""Step 2 续：抽取 200 篇用于人工抽检 + Cohen's κ 评估。

使用方法：
  python3 report/sample_for_review.py

输出：
  - report/review_sample.csv     — 200 篇抽检样本（含原文摘要）
  - report/review_template.csv   — 供人工标注的模板（标注后用于计算 Cohen's κ）

人工标注格式说明：
  评估者需对每篇文章填写：
  - category_manual: Research/Technology/Review/Protocol/Data Resource/Benchmark
  - tags_manual: 分号分隔的分析标签
  - confidence_manual: high/medium/low
  - agrees: YES/NO（是否同意 LLM 标注）

计算 Cohen's κ：
  python3 -c "
  import csv, json
  from sklearn.metrics import cohen_kappa_score

  rows = []
  with open('report/review_template.csv') as f:
      for r in csv.DictReader(f):
          if r['category_manual'] and r['confidence_manual']:
              rows.append(r)

  # 类别一致性
  cat_kappa = cohen_kappa_score(
      [r['category'] for r in rows],
      [r['category_manual'] for r in rows]
  )
  print(f'类别 Cohen\\'s κ = {cat_kappa:.4f}')

  # 置信度一致性
  conf_kappa = cohen_kappa_score(
      [r['confidence'] for r in rows],
      [r['confidence_manual'] for r in rows]
  )
  print(f'置信度 Cohen\\'s κ = {conf_kappa:.4f}')

  # 总体同意率
  agrees = [r for r in rows if r['agrees']]
  print(f'总体同意率: {len(agrees)}/{len(rows)} = {len(agrees)/len(rows)*100:.1f}%')
  "
"""
import csv
import random
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent / "data/spatial_tracker"
OUT = Path(__file__).resolve().parent

random.seed(42)

# 读取标注数据
rows = []
with open(DATA / "annotated_articles.csv") as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    for r in reader:
        rows.append(r)

# 读取原文获取摘要
articles = {}
with open(DATA / "articles.csv") as f:
    for r in csv.DictReader(f):
        articles[r["pmid"]] = r.get("abstract", "")

# 分层抽样：按类别比例抽取共 200 篇
cats = [r["category"] for r in rows]
N = 200
sample_size = {}
for cat in set(cats):
    sample_size[cat] = max(1, round(cats.count(cat) / len(cats) * N))

# 调整至恰好 200
total = sum(sample_size.values())
if total < N:
    # 补到最多个的类别
    major = max(sample_size, key=sample_size.get)
    sample_size[major] += N - total
elif total > N:
    major = max(sample_size, key=sample_size.get)
    sample_size[major] -= total - N

# 抽取
pool = {cat: [r for r in rows if r["category"] == cat] for cat in sample_size}
sample = []
for cat, n in sample_size.items():
    sample.extend(random.sample(pool[cat], min(n, len(pool[cat]))))

random.shuffle(sample)
print(f"✅ 抽取 {len(sample)} 篇 (分层抽样)")
for cat in sorted(sample_size):
    actual = sum(1 for r in sample if r["category"] == cat)
    print(f"  {cat}: {actual} 篇")

# 输出抽检样本（含摘要，供审阅）
with open(OUT / "review_sample.csv", "w", newline="") as f:
    fn = ["pmid", "title", "abstract", "category", "tags", "technology",
          "biological_topic", "confidence", "has_new_data", "has_code"]
    w = csv.DictWriter(f, fieldnames=fn)
    w.writeheader()
    for r in sample:
        w.writerow({
            "pmid": r["pmid"],
            "title": r["title"],
            "abstract": articles.get(r["pmid"], "")[:500],
            "category": r["category"],
            "tags": r.get("tags", ""),
            "technology": r.get("technology", ""),
            "biological_topic": r.get("biological_topic", ""),
            "confidence": r["confidence"],
            "has_new_data": r.get("has_new_data", ""),
            "has_code": r.get("has_code", ""),
        })
print(f"✅ 抽检样本 → {OUT / 'review_sample.csv'}")

# 输出标注模板（供人工填写后计算 Cohen's κ）
with open(OUT / "review_template.csv", "w", newline="") as f:
    fn = ["pmid", "title", "category", "tags",
          "confidence", "category_manual", "tags_manual",
          "confidence_manual", "agrees", "notes"]
    w = csv.DictWriter(f, fieldnames=fn)
    w.writeheader()
    for r in sample:
        w.writerow({
            "pmid": r["pmid"],
            "title": r["title"][:120],
            "category": r["category"],
            "tags": r.get("tags", ""),
            "confidence": r["confidence"],
            "category_manual": "",
            "tags_manual": "",
            "confidence_manual": "",
            "agrees": "",
            "notes": "",
        })
print(f"✅ 标注模板 → {OUT / 'review_template.csv'}")
print()
print("=" * 60)
print("  人工标注完成后，运行下方命令计算 Cohen's κ：")
print()
print("  python3 -c \"")
print("  import csv")
print("  from sklearn.metrics import cohen_kappa_score")
print()
print("  rows = []")
print("  with open('report/review_template.csv') as f:")
print("      for r in csv.DictReader(f):")
print("          if r['category_manual'] and r['confidence_manual']:")
print("              rows.append(r)")
print()
print("  cat_kappa = cohen_kappa_score(")
print("      [r['category'] for r in rows],")
print("      [r['category_manual'] for r in rows])")
print("  print(f'类别 Cohen\\'s κ = {cat_kappa:.4f}')")
print()
print("  conf_kappa = cohen_kappa_score(")
print("      [r['confidence'] for r in rows],")
print("      [r['confidence_manual'] for r in rows])")
print("  print(f'置信度 Cohen\\'s κ = {conf_kappa:.4f}')")
print()
print("  agrees = [r for r in rows if r['agrees']]")
print("  print(f'总体同意率: {len(agrees)}/{len(rows)}')")
print('  "')
