import pandas as pd
import numpy as np

DATA_FILE = "spatial_literature.xlsx"
df = pd.read_excel(DATA_FILE)

# 1. 重新规划批次 (Batch 1, 2, 3 不动，其他已确定的全归类为 Batch 4)
confirmed_mask = df["is_manually_confirmed"] == True
# Identify manual vs non-manual. Set annotation_batch correctly.
# If it's manually confirmed but hasn't a proper batch (or > 3), assign it to 4.
df.loc[confirmed_mask & (~df["annotation_batch"].isin([1, 2, 3])), "annotation_batch"] = 4

# 2. Naive Classifier (增强版)
TECH_KEYWORDS = ["Visium", "merfish", "Slide-seq", "Stereo-seq", "seqfish", "CosMx", "Xenium", "pixel-seq", "starmap"]
ANALYSIS_KEYWORDS = ["pipeline", "tool", "software", "algorithm", "benchmark", "integration", "interaction", "computational", "spatially variable", "deconvolution"]
DOMAIN_KEYWORDS = {"Development": ["development", "embryo", "organogenesis"], "Cancer": ["cancer", "tumor", "carcinoma", "oncology", "malignan"], "Neuroscience": ["brain", "brain", "neuron", "cortex", "alzheimer", "parkinson"], "Immunology": ["immune", "lymph", "t cell", "b cell", "macrophage"], "Plant": ["plant", "leaf", "root", "arabidopsis"]}

def naive_classify(row):
    title = str(row.get("title", "")).lower()
    abstract = str(row.get("abstract", "")).lower()
    journal = str(row.get("journal", "")).lower()
    text = title + " " + abstract
    
    cat = "Research"
    if "review" in title or "Review" in title:
        cat = "Review"
    elif "database" in title or "database" in abstract:
        cat = "Database"
    elif any(kw in title for kw in ANALYSIS_KEYWORDS) and not any(kw in title for kw in TECH_KEYWORDS):
        cat = "Data Analysis"
    elif any(kw in title for kw in TECH_KEYWORDS) and ("novel" in title or "new" in title or "method" in title):
        cat = "Technology"

    tags = []
    for tech in TECH_KEYWORDS:
        if tech in text:
            tags.append(tech.upper() if tech != "pixel-seq" else "Pixel-seq")
            
    if "clustering" in text or "cluster" in text: tags.append("Clustering")
    if "deconvolution" in text: tags.append("Deconvolution")
    if "cellphone" in text or "communication" in text: tags.append("Cell Communication")
    if "trajectory" in text: tags.append("Spatial Trajectory")

    for domain, kws in DOMAIN_KEYWORDS.items():
        if any(kw in text for kw in kws):
            tags.append(domain)
            
    return pd.Series([cat, "; ".join(list(set(tags)))])

print("Running baseline naive classifier on all data...")
df[["naive_category", "naive_tags"]] = df.apply(naive_classify, axis=1)

df.to_excel(DATA_FILE, index=False)
print("Naive fields added and dataset batches reorganized.")
