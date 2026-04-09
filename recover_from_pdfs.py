import os
import pandas as pd
import glob
import re

DATA_FILE = "/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/spatial_literature.xlsx"

def recover():
    print("[Recovery] Phase 1 - Parsing PDFs...")
    pdf_dir = "/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/PDF_Archive/"
    pdfs = glob.glob(pdf_dir + "**/*.pdf", recursive=True)
    
    recovered = []
    for p in pdfs:
        cat_dir = os.path.basename(os.path.dirname(p))
        fname = os.path.basename(p)
        # Format: [pub_year]_[tags]_[doi].pdf
        match = re.match(r"(\d{4})_(.*)_([^/]+)\.pdf", fname)
        if match:
            year, tags, doi = match.groups()
            tags = tags.replace("_", "; ") # naive space restoration
            doi = doi.replace("_", "/") # naive doi restoration (slashes were probably sanitized)
            recovered.append({
                "category": cat_dir,
                "tags": tags,
                "doi_approx": doi,
                "pub_year": year
            })
            
    if not recovered:
        print("No PDFs found for recovery.")
        return
        
    df_rec = pd.DataFrame(recovered)
    print(f"Parsed {len(df_rec)} PDF annotations.")
    
    # Try to match DOIs to PMIDs in the current DB
    df_main = pd.read_excel(DATA_FILE)
    
    matched = 0
    for idx, row in df_rec.iterrows():
        # Match using approximate DOI
        possible = df_main[df_main['doi'].astype(str).str.contains(row['doi_approx'], regex=False, na=False)]
        if not possible.empty:
            p_idx = possible.index[0]
            cat_map = {"数据分析": "Data Analysis", "数据库": "Database", "综述": "Review", "研究": "Research", "技术": "Technology"}
            cat_en = cat_map.get(row['category'], row['category'])
            
            df_main.at[p_idx, 'category'] = cat_en
            df_main.at[p_idx, 'tags'] = row['tags']
            df_main.at[p_idx, 'is_manually_confirmed'] = True
            matched += 1
            
    print(f"Successfully matched and restored {matched} annotations from PDF Archive.")
    df_main.to_excel(DATA_FILE.replace(".xlsx", "_recovered.xlsx"), index=False)
    print("Saved as spatial_literature_recovered.xlsx")
    
if __name__ == "__main__":
    recover()
