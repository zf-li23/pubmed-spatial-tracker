import pandas as pd
import numpy as np

DATA_FILE = "/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/spatial_literature.xlsx"
df = pd.read_excel(DATA_FILE)

# 1. Map Chinese categories & tags to English
CAT_MAP = {
    "数据分析": "Data Analysis", 
    "数据库": "Database", 
    "综述": "Review", 
    "研究": "Research", 
    "技术": "Technology",
    "丢弃": "Discard",
    "Discard": "Discard"
}

df['category'] = df['category'].replace(CAT_MAP)

def translate_tags(tag_str):
    if pd.isna(tag_str) or not str(tag_str).strip():
        return tag_str
    
    tags = [t.strip() for t in str(tag_str).split(";")]
    new_tags = []
    
    TAG_MAP = {
        "数据分析": "Data Analysis", 
        "数据库": "Database", 
        "综述": "Review", 
        "研究": "Research", 
        "技术": "Technology",
        "丢弃": "Discarded",
        "无用": "Discarded",
        "癌症": "Cancer",
        "聚类": "Clustering"
    }
    
    for t in tags:
        new_tags.append(TAG_MAP.get(t, t))
    return "; ".join(sorted(list(set(new_tags))))

df['tags'] = df['tags'].apply(translate_tags)

# 2. Extract strict CNS matching for batch assignment
cns_exact = ["Cell", "Nature", "Science (New York, N.Y.)", "Science"]
def strict_is_cns(j):
    if pd.isna(j): return False
    j2 = str(j).strip()
    return j2 in cns_exact

# Set unconfirmed records' batch to NaN temporarily
unconfirmed_mask = df["is_manually_confirmed"] == False
df.loc[unconfirmed_mask, "annotation_batch"] = np.nan

# 3. Assign Batches (Batches 1, 2, 3 should ideally be confirmed. If they are not fully confirmed, they need batch logic)
# Let's find the max confirmed batch
max_confirmed_b = df.loc[df["is_manually_confirmed"] == True, "annotation_batch"].max()
if pd.isna(max_confirmed_b):
    current_batch_num = 1
else:
    current_batch_num = int(max_confirmed_b) + 1

# Geometrically increasing batch sizes: 50, 100, 200, 400, 800...
batch_size = 50
if current_batch_num == 2: batch_size = 100
elif current_batch_num == 3: batch_size = 200
elif current_batch_num > 3: batch_size = 50 * (2 ** (current_batch_num - 1))

items_in_current_batch = 0
last_batch_number = 999

for idx in df[unconfirmed_mask].index:
    cat = df.loc[idx, "category"]
    if pd.isna(cat) or str(cat).strip() == "":
        # Default to naive if empty
        cat = "Research"
        if "review" in str(df.loc[idx, "title"]).lower(): cat = "Review"
        
    journal = df.loc[idx, "journal"]
    
    # "除了被筛选掉的非CNS研究类文章以外的其他文章"
    if str(cat).strip() == "Research" and not strict_is_cns(journal):
        df.loc[idx, "annotation_batch"] = last_batch_number
    elif str(cat).strip() == "Discard":
        df.loc[idx, "annotation_batch"] = last_batch_number
    else:
        # Geometrically increasing size logic
        while items_in_current_batch >= batch_size:
            current_batch_num += 1
            batch_size = 50 * (2 ** (current_batch_num - 1))
            items_in_current_batch = 0
            
        df.loc[idx, "annotation_batch"] = current_batch_num
        items_in_current_batch += 1

df.to_excel(DATA_FILE, index=False)
print("Data categories translated to English, Strict CNS applied, and Batches reshifted with geometric sizes!")
