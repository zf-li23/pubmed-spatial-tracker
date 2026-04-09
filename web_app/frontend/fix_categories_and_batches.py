import pandas as pd
import numpy as np

DATA_FILE = "/tmp/test_backup.xlsx"
df = pd.read_excel(DATA_FILE)

# Ensure naive fields use English to match ground truth semantics
TECH_KEYWORDS = ["visium", "merfish", "slide-seq", "stereo-seq", "seqfish", "cosmx", "xenium", "pixel-seq", "starmap"]
ANALYSIS_KEYWORDS = ["pipeline", "tool", "software", "algorithm", "benchmark", "integration", "interaction", "computational", "spatially variable", "deconvolution"]
DOMAIN_KEYWORDS = {"Cancer": ["cancer", "tumor", "carcinoma", "oncology", "malignan"], "Development": ["development", "embryo", "organogenesis"], "Neuroscience": ["brain", "brain", "neuron", "cortex", "alzheimer", "parkinson"], "Immunology": ["immune", "lymph", "t cell", "b cell", "macrophage"], "Plant": ["plant", "leaf", "root", "arabidopsis"]}

def naive_classify(row):
    title = str(row.get("title", "")).lower()
    abstract = str(row.get("abstract", "")).lower()
    journal = str(row.get("journal", "")).lower()
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

# Reset batches for unconfirmed
cns_exact = ["Cell", "Nature", "Science (New York, N.Y.)"]

def strict_is_cns(j):
    if pd.isna(j): return False
    j2 = str(j).strip()
    return j2 in cns_exact

unconfirmed = df["is_manually_confirmed"] == False

# Reset all unconfirmed batches to null first so we can cleanly assign
df.loc[unconfirmed, "annotation_batch"] = np.nan
last_batch_number = 999

# Current logical start for unconfirmed
# Batches 1,2,3 are locked confirmed. Let's find max confirmed batch
max_confirmed_b = df.loc[df["is_manually_confirmed"] == True, "annotation_batch"].max()
current_batch_number = max_confirmed_b + 1 if pd.notna(max_confirmed_b) else 1

BATCH_SIZE = 30
batch_counters = {current_batch_number: 0}

for idx in df[unconfirmed].index:
    # Use ground-truth category if set, else naive
    cat = df.loc[idx, "category"]
    if pd.isna(cat) or cat == "":
        cat = df.loc[idx, "naive_category"]
        
    journal = df.loc[idx, "journal"]
    
    if cat == "Research" and not strict_is_cns(journal):
        df.loc[idx, "annotation_batch"] = last_batch_number
    else:
        # Give it a batch
        while batch_counters.get(current_batch_number, 0) >= BATCH_SIZE:
             current_batch_number += 1
             if current_batch_number not in batch_counters:
                 batch_counters[current_batch_number] = 0
        
        df.loc[idx, "annotation_batch"] = current_batch_number
        batch_counters[current_batch_number] += 1

df.to_excel("/tmp/out.xlsx", index=False)
print("Data aligned to english categories, Strict CNS applied, and Batches reshifted!")
