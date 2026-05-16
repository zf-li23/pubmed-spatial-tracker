import pandas as pd
import numpy as np
import os
import json
import re
import sys

# 将项目根目录加入 path，确保 migrate_naive.py 在项目根直接运行时也能正确导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "web_app"))

from web_app.shared import (
    load_tags,
    guess_novel_name,
    enforce_category_tag_policy,
    _uniq_keep_order,
)

TAG_GROUPS = load_tags()


def get_naive(title, abstract, journal):
    """基于规则给单篇文献打初始类别和标签（冷启动 / 兜底分类）。"""
    title_lower = str(title).lower() if pd.notna(title) else ""
    abstract_lower = str(abstract).lower() if pd.notna(abstract) else ""
    journal_lower = str(journal).lower() if pd.notna(journal) else ""
    combined_text = title_lower + " " + abstract_lower

    tags = []
    category = "Research"

    # 在 tags.json 的各分组中做关键词匹配
    group_counts = {g: 0 for g in TAG_GROUPS}
    for group, group_tags in TAG_GROUPS.items():
        for tag in group_tags:
            t_lower = str(tag).lower()
            if t_lower in combined_text or t_lower.replace("-", "") in combined_text:
                tags.append(tag)
                group_counts[group] += 1

    tags = _uniq_keep_order(tags)

    # 根据匹配到的分组和标题/期刊关键词推断类别
    if "review" in title_lower or "review" in journal_lower:
        category = "Review"
    elif group_counts.get("technology", 0) > 0 and group_counts.get("analysis", 0) == 0:
        category = "Technology"
    elif group_counts.get("analysis", 0) > 0:
        category = "Data Analysis"
    elif "database" in title_lower or "database" in combined_text:
        # database 组可能在 tags.json 中已被移除，用标题关键词兜底
        category = "Database"

    tags = enforce_category_tag_policy(category, tags, title=title)
    return category, "; ".join(tags)


if __name__ == "__main__":
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///spatial_literature.db")
    df = pd.read_sql("SELECT * FROM literature", engine)
    if "naive_category" not in df.columns:
        df["naive_category"] = ""
    if "naive_tags" not in df.columns:
        df["naive_tags"] = ""

    for idx, row in df.iterrows():
        cat, tags = get_naive(row["title"], row["abstract"], row["journal"])
        df.at[idx, "naive_category"] = cat
        df.at[idx, "naive_tags"] = tags

    df.to_sql("literature", engine, index=False, if_exists="replace")
    print("Naive re-computed with shared policy!")
