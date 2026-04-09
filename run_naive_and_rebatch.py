import pandas as pd
import numpy as np

DATA_FILE = "/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/spatial_literature.xlsx"
df = pd.read_excel(DATA_FILE)

# 1. Map Chinese categories & tags to English (just in case any remain)
CAT_MAP = {
    "数据分析": "Data Analysis", 
    "数据库": "Database", 
    "综述": "Review", 
    "研究": "Research", 
    "技术": "Technology",
    "丢弃": "Discard",
    "Discard": "Discard",
    "无用": "Discard"
}
if 'category' in df.columns:
    df['category'] = df['category'].replace(CAT_MAP)

# 2. Baseline Naive Classifier
TECH_KEYWORDS = ["visium", "merfish", "slide-seq", "stereo-seq", "seqfish", "cosmx", "xenium", "pixel-seq", "starmap"]
ANALYSIS_KEYWORDS = ["pipeline", "tool", "software", "algorithm", "benchmark", "integration", "interaction", "computational", "spatially variable", "deconvolution"]
DOMAIN_KEYWORDS = {"Cancer": ["cancer", "tumor", "carcinoma", "oncology", "malignan"], "Development": ["development", "embryo", "organogenesis"], "Neuroscience": ["brain", "neuron", "cortex", "alzheimer", "parkinson"], "Immunology": ["immune", "lymph", "t cell", "b cell", "macrophage"], "Plant": ["plant", "leaf", "root", "arabidopsis"]}

def naive_classify(row):
    title = str(row.get("title", "")).lower()
    abstract = str(row.get("abstract", "")).lower()
    text = title + " " + abstract
    
    cat = "Research"
    if "review" in title or "综述" in title:
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

print("Running baseline naive classifier mapped to English categories...")
df[["naive_category", "naive_tags"]] = df.apply(naive_classify, axis=1)

# Merge Naive into Actual if empty
for idx in df.index:
    if pd.isna(df.loc[idx, "category"]) or str(df.loc[idx, "category"]).strip() == "":
        df.loc[idx, "category"] = df.loc[idx, "naive_category"]
    if pd.isna(df.loc[idx, "tags"]) or str(df.loc[idx, "tags"]).strip() == "":
        df.loc[idx, "tags"] = df.loc[idx, "naive_tags"]


# 3. Strict CNS matching for batch assignment
cns_exact = ["Cell", "Nature", "Science (New York, N.Y.)", "Science"]
def strict_is_cns(j):
    if pd.isna(j): return False
    return str(j).strip() in cns_exact

unconfirmed_mask = df["is_manually_confirmed"] == False
df.loc[unconfirmed_mask, "annotation_batch"] = np.nan

# 4. Assign Batches (Geometrically increasing: 50, 100, 200, 400...)
# Get highest confirmed batch
max_confirmed_b = df.loc[~unconfirmed_mask, "annotation_batch"].max()
current_batch_num = 1 if pd.isna(max_confirmed_b) else int(max_confirmed_b) + 1

batch_size = 50 * (2 ** (current_batch_num - 1)) if current_batch_num > 1 else 50
items_in_current_batch = 0
last_batch_number = 999

for idx in df[unconfirmed_mask].index:
    cat = str(df.loc[idx, "category"]).strip()
    journal = df.loc[idx, "journal"]
    
    # "除了被筛选掉的非CNS研究类文章以外的其他文章，我还是希望先按照数据集依次增大的方式来划分"
    if cat == "Research" and not strict_is_cns(journal):
        df.loc[idx, "annotation_batch"] = last_batch_number
    elif cat == "Discard":
        df.loc[idx, "annotation_batch"] = last_batch_number
    else:
        while items_in_current_batch >= batch_size:
            current_batch_num += 1
            batch_size = 50 * (2 ** (current_batch_num - 1))
            items_in_current_batch = 0
            
        df.loc[idx, "annotation_batch"] = current_batch_num
        items_in_current_batch += 1

# Make sure auto_predicted_category and auto_predicted_tags are initialized
if 'auto_predicted_category' not in df.columns:
    df['auto_predicted_category'] = ""
if 'auto_predicted_tags' not in df.columns:
    df['auto_predicted_tags'] = ""

df.to_excel(DATA_FILE, index=False)
print("Data categories translated to English, naive classified, Strict CNS applied, and Batches reshifted with geometric sizes!")
