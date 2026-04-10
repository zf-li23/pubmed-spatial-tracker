import pandas as pd
import numpy as np
import os
import json

def load_tags():
    tags_path = "tags.json"
    if os.path.exists(tags_path):
        with open(tags_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "technology": ["Visium", "MERFISH", "Slide-seq", "Stereo-seq", "Xenium", "CosMx"],
        "analysis": ["Clustering", "Deconvolution", "Imputation", "Cell Communication", "Spatial Trajectory"],
        "domain": ["Neuroscience", "Development", "Cancer", "Reproduction"]
    }

TAG_GROUPS = load_tags()

def get_naive(title, abstract, journal):
    title_lower = str(title).lower() if pd.notna(title) else ""
    abstract_lower = str(abstract).lower() if pd.notna(abstract) else ""
    journal_lower = str(journal).lower() if pd.notna(journal) else ""
    combined_text = title_lower + " " + abstract_lower
    
    tags = []
    
    category = "Research" # 默认兜底
    
    # 根据在 tags.json 匹配到的标签所在的 group 来动态推断大类
    group_counts = {g: 0 for g in TAG_GROUPS.keys()}
    
    for group, group_tags in TAG_GROUPS.items():
        for tag in group_tags:
            t_lower = str(tag).lower()
            # 简单的全词匹配，避免部分前缀匹配（为简单起见先使用in，但可使用正则来提升精度）
            if t_lower in combined_text or t_lower.replace("-", "") in combined_text:
                tags.append(tag)
                group_counts[group] += 1
                
    # 去重
    tags = list(set(tags))
    
    if "Review".lower() in title_lower or "Review".lower() in journal_lower:
        category = "Review"
    elif group_counts.get("database", 0) > 0 or "database".lower() in title_lower:
        category = "Database"
    elif group_counts.get("technology", 0) > 0 and group_counts.get("analysis", 0) == 0:
        category = "Technology"
    elif group_counts.get("analysis", 0) > 0:
        category = "Data Analysis"
        
    return category, "; ".join(tags)

if __name__ == "__main__":
    df = pd.read_excel("spatial_literature.xlsx")
    if "naive_category" not in df.columns:
        df["naive_category"] = ""
    if "naive_tags" not in df.columns:
        df["naive_tags"] = ""
        
    for idx, row in df.iterrows():
        cat, tags = get_naive(row["title"], row["abstract"], row["journal"])
        df.at[idx, "naive_category"] = cat
        df.at[idx, "naive_tags"] = tags
        
    df.to_excel("spatial_literature.xlsx", index=False)
    print("Naive re-computed with new tags!")
