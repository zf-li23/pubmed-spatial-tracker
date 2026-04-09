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
    
    for group, group_tags in TAG_GROUPS.items():
        for tag in group_tags:
            t_lower = tag.lower()
            if t_lower in combined_text or t_lower.replace("-", "") in combined_text:
                tags.append(tag)
                
    is_method_note = False
    if "brief communication" in str(title).lower():
        is_method_note = True
        
    category = "Research"
    if "database" in title_lower or "resource" in journal_lower:
        category = "Database"
    elif "review" in title_lower or "review" in journal_lower or is_method_note:
        category = "Review"
    elif "tool" in title_lower or "software" in title_lower or "benchmark" in title_lower or "comparison" in title_lower:
        category = "Data Analysis"
    elif "sequencing" in combined_text and ("spatial" in title_lower or "resolve" in title_lower):
        category = "Technology"
        
    return category, "; ".join(tags)

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
