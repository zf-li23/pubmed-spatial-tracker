import re

with open('../app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# Add endpoint for fetching PMIDs
new_endpoints = """
from Bio import Entrez
import io

@app.post("/api/pmids/upload")
async def upload_pmids(file: UploadFile = File(...)):
    content = await file.read()
    text = content.decode('utf-8')
    pmids = [line.strip() for line in text.splitlines() if line.strip().isdigit()]
    
    if not pmids:
        return {"message": "查无有效的 PMID。请确保文本文件里每行一个数字ID。"}
        
    df = get_df()
    existing_pmids = set(df["pmid"].astype(str))
    new_pmids = [p for p in pmids if p not in existing_pmids]
    
    if not new_pmids:
        return {"message": f"所传文本里的 {len(pmids)} 个 PMID 均已在Database中存在，无需重复下载！"}
        
    Entrez.email = "zf-li23@mails.tsinghua.edu.cn"
    articles = []
    
    batch_size = 200
    try:
        from tqdm import tqdm
        for i in range(0, len(new_pmids), batch_size):
            batch = new_pmids[i:i+batch_size]
            fetch_handle = Entrez.efetch(db="pubmed", id=",".join(batch), retmode="xml")
            batch_results = Entrez.read(fetch_handle)
            fetch_handle.close()
            articles.extend(batch_results.get("PubmedArticle", []))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载时出错 NCBI E-utilities Error: {str(e)}")
        
    # Assign new ones to max batch so they are the current focus. Wait, just let them be unconfirmed.
    # Set them to be in the "current" active unconfirmed batch, or max batch.
    max_b = int(df["annotation_batch"].max()) if not df.empty and "annotation_batch" in df.columns else 1
    unconf_b = df[df["is_manually_confirmed"] == False]["annotation_batch"].min()
    target_batch = int(unconf_b) if pd.notna(unconf_b) else max_b
    
    new_rows = []
    from datetime import datetime
    for record in articles:
        medline = record.get("MedlineCitation", {})
        article = medline.get("Article", {})
        pmid = str(medline.get("PMID", ""))
        doi = ""
        for aid in record.get("PubmedData", {}).get("ArticleIdList", []):
            if aid.attributes.get("IdType") == "doi":
                doi = str(aid)
                break
        title = article.get("ArticleTitle", "")
        journal = article.get("Journal", {}).get("Title", "")
        pub_year = ""
        pub_date = article.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
        if "Year" in pub_date:
            pub_year = pub_date["Year"]
        elif "MedlineDate" in pub_date:
            match = re.search(r"\d{4}", pub_date["MedlineDate"])
            if match: pub_year = match.group(0)
            
        abstract_texts = article.get("Abstract", {}).get("AbstractText", [])
        abstract = " ".join([str(t) for t in abstract_texts]) if abstract_texts else ""
        
        row = {
            "pmid": pmid,
            "doi": doi,
            "url": "",
            "title": title,
            "abstract": abstract,
            "pub_year": pub_year,
            "journal": journal,
            "category": "",
            "tags": "",
            "is_manually_confirmed": False,
            "pdf_path": "",
            "annotation_batch": target_batch,
            "auto_predicted_category": "",
            "auto_predicted_tags": ""
        }
        new_rows.append(row)
        
    if new_rows:
        df_new = pd.DataFrame(new_rows)
        # Ensure columns match
        for c in df.columns:
            if c not in df_new.columns:
                df_new[c] = ""
        for c in df_new.columns:
            if c not in df.columns:
                df[c] = ""
        df = pd.concat([df, df_new], ignore_index=True)
        save_df(df)
        
    return {"message": f"成功下载并导入了 {len(new_rows)} 篇由于您手动提供的 PubMed文献！为了方便您打标，它们已被临时分配在当前工作批次 (Batch {target_batch})。"}
"""
if "@app.post(\"/api/pmids/upload\")" not in text:
    text = text.replace("def get_articles():", new_endpoints + "\n@app.get(\"/api/articles\")\ndef get_articles():")

# Now handle the Auto-confirm logic in active learning
regex_trigger = r'target_idx = df\[\(df\["annotation_batch"\] == next_batch\) & \(df\["is_manually_confirmed"\] == False\)\].index.*?save_df\(df\)'

new_trigger = r'''target_idx = df[(df["annotation_batch"] == next_batch) & (df["is_manually_confirmed"] == False)].index
    predicted_count = 0
    if not target_idx.empty:
        target_df = df.loc[target_idx]
        pred_cats, pred_tags = learner.predict(target_df["title"].tolist(), target_df["abstract"].tolist())
        
        for k, idx in enumerate(target_idx):
            cat = pred_cats[k]
            tag = pred_tags[k]
            journal = str(target_df.loc[idx, "journal"]).lower()
            
            df.loc[idx, "category"] = cat
            df.loc[idx, "auto_predicted_category"] = cat
            df.loc[idx, "tags"] = tag
            df.loc[idx, "auto_predicted_tags"] = tag
            
            predicted_count += 1
            
            if cat == "Research":
                is_top = False
                for top_j in ["cell", "nature", "science"]:
                    # very strict match (word boundary)
                    if re.search(r'\b' + top_j + r'\b', journal):
                        is_top = True
                        break
                if not is_top:
                    df.loc[idx, "is_manually_confirmed"] = True
        
    save_df(df)'''
    
text = re.sub(regex_trigger, new_trigger, text, flags=re.DOTALL)

with open('../app.py', 'w', encoding='utf-8') as f:
    f.write(text)

