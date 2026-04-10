import os
import shutil
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import requests
import re
from pydantic import BaseModel

# Setup Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BASE_DIR, "spatial_literature.xlsx")
PDF_DIR = os.path.join(BASE_DIR, "PDF_Archive")

# Initialize PDF subfolders
CATEGORIES = ["Review", "Technology", "Database", "Data Analysis", "Research"]
for cat in CATEGORIES:
    os.makedirs(os.path.join(PDF_DIR, cat), exist_ok=True)

app = FastAPI(title="PubMed Annotation Tool")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

def safe_filename(name):
    if pd.isna(name) or not str(name).strip() or str(name).strip().lower() == "nan":
        return "Unknown"
    # Filter out `.pdf` if it was accidentally appended
    clean_str = str(name).strip()
    if clean_str.lower().endswith(".pdf"):
        clean_str = clean_str[:-4]
    clean_str = re.sub(r'[\r\n]+', '', clean_str)
    # Replace anything not alphanumeric or basic punctuation with _
    return re.sub(r'[\\/*?:"<>|; ]', '_', clean_str)

def get_df():
    if not os.path.exists(DATA_FILE):
        return pd.DataFrame()
    return pd.read_excel(DATA_FILE)

from threading import Lock
df_lock = Lock()

def save_df(df):
    with df_lock:
        temp_file = DATA_FILE + ".writing.xlsx"
        t_bak = DATA_FILE + ".backup.xlsx"
        
        # 1. Write fully to a temp file
        df.to_excel(temp_file, index=False)
        
        # 2. Swap atomically (or near-atomically across platforms)
        import shutil
        if os.path.exists(DATA_FILE):
            shutil.copyfile(DATA_FILE, t_bak) # keep a quick backup
            
        os.replace(temp_file, DATA_FILE)

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
        
    # "新加入的数据直接被标注成除了999批以外的最后一个batch，自动被naive方法分类"
    max_b = 1
    if not df.empty and "annotation_batch" in df.columns:
        valid_batches = df[df["annotation_batch"] != 999]["annotation_batch"]
        if not valid_batches.dropna().empty:
            max_b = int(valid_batches.max())
    target_batch = max_b
    
    import sys
    if BASE_DIR not in sys.path:
        sys.path.append(BASE_DIR)
    from migrate_naive import get_naive
    
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
        
        # 自动被naive方法分类
        naive_cat, naive_tags = get_naive(title, abstract, journal)
        row = {
            "pmid": pmid,
            "doi": doi,
            "url": "",
            "title": title,
            "abstract": abstract,
            "pub_year": pub_year,
            "journal": journal,
            "category": naive_cat,
            "tags": naive_tags,
            "naive_category": naive_cat,
            "naive_tags": naive_tags,
            "is_manually_confirmed": False,
            "pdf_path": "",
            "annotation_batch": target_batch,
            "auto_predicted_category": naive_cat,
            "auto_predicted_tags": naive_tags
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
        
        # 记录手动导入的PMID，以便复现
        manual_pmids_path = os.path.join(BASE_DIR, "manual_imported_pmids.txt")
        new_pmids_list = df_new["pmid"].tolist()
        try:
            with open(manual_pmids_path, "a", encoding="utf-8") as fpmids:
                for np_id in new_pmids_list:
                    fpmids.write(f"{np_id}\n")
        except Exception as e:
            print(f"Failed to write manual pmids to {manual_pmids_path}: {e}")
        
    return {"message": f"成功下载并导入了 {len(new_rows)} 篇由于您手动提供的 PubMed文献！为了方便您打标，它们已被临时分配在当前工作批次 (Batch {target_batch})。"}

@app.get("/api/articles")
@app.get("/api/articles")
def get_articles():
    df = get_df()
    if df.empty:
        return []
    df = df.fillna("")
    return df.to_dict(orient="records")

class AnnotationData(BaseModel):
    category: str
    tags: str

@app.post("/api/ml/active_learning")
def trigger_active_learning():
    df = get_df()
    
    if "annotation_batch" not in df.columns:
        raise HTTPException(status_code=400, detail="Database not upgraded with active learning schema.")
        
    confirmed_df = df[df["is_manually_confirmed"] == True]
    unconfirmed_df = df[df["is_manually_confirmed"] == False]
    
    if unconfirmed_df.empty:
        return {"message": "✅ 恭喜！当前库中所有文章均已校验完毕！", "status": "done"}
        
    next_batch = int(unconfirmed_df["annotation_batch"].min())
    
    # 如果其中有零散的被我标注了的数据，应该会被整合到当前batch，包括第999批中的数据
    scattered_mask = (df["is_manually_confirmed"] == True) & (df["annotation_batch"] > next_batch)
    if scattered_mask.any():
        df.loc[scattered_mask, "annotation_batch"] = next_batch
        confirmed_df = df[df["is_manually_confirmed"] == True]
        save_df(df)
    
    if confirmed_df.empty:
        return {
            "message": "请至少先标注并校验【第 1 批次】的部分数据，模型才拥有基线样本来学习！", 
            "status": "need_data",
            "next_batch": next_batch
        }

    try:
        from ml_pipeline import AutomatedActiveLearner
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Please install required ML libraries! {str(e)}")

    # ========= SIMULATION FOR ML_PERFORMANCE_REPORT (V3.0 Logic) =========
    # Rewriting ML report based on retrospective simulation
    report_rows = []
    
    # To properly simulate, we sort batches. We ONLY use batches that are fully completed
    # Any batch >= next_batch has unconfirmed items, meaning it's incomplete.
    all_confirmed_batches = sorted(confirmed_df["annotation_batch"].unique().tolist())
    completed_batches = [b for b in all_confirmed_batches if b < next_batch]
    
    learner = AutomatedActiveLearner()
    
    for i in range(len(completed_batches)):
        b = completed_batches[i]
        
        # Test phase for the current completed batch
        b_df = confirmed_df[confirmed_df["annotation_batch"] == b]
        y_true_cat = b_df["category"].tolist()
        
        if i == 0:
            # First batch baseline evaluation
            y_pred_cat = b_df["auto_predicted_category"].fillna("Research").tolist()
            correct = sum(1 for yt, yp in zip(y_true_cat, y_pred_cat) if yt == yp)
            acc = correct / len(y_true_cat) if len(y_true_cat) > 0 else 0
            report_rows.append({
                "Trained_On_Batches": "Baseline(0)",
                "Tested_On_Batch": b,
                "Test_Samples": len(y_true_cat),
                "Category_Accuracy": round(acc, 3),
                "Tag_Micro_F1": 0,
                "Tag_Macro_F1": 0
            })
        else:
            # We already have trained the model on batch < b in the previous iterations
            pred_cats, pred_tags = learner.predict(b_df)
            
            correct = sum(1 for yt, yp in zip(y_true_cat, pred_cats) if yt == yp)
            acc = correct / len(y_true_cat) if len(y_true_cat) > 0 else 0
            
            # calculate F1 scores for tags here
            # using learner.mlb metrics
            from sklearn.metrics import f1_score
            y_true_tags_raw = [str(t).split(';') for t in b_df["tags"].tolist()]
            y_true_tags_clean = [[t.strip() for t in ts if t.strip()] for ts in y_true_tags_raw]
            
            y_pred_tags_raw = [str(t).split(';') for t in pred_tags]
            y_pred_tags_clean = [[t.strip() for t in ts if t.strip()] for ts in y_pred_tags_raw]
            
            if learner.mlb is not None and hasattr(learner.mlb, "classes_"):
                from sklearn.preprocessing import MultiLabelBinarizer
                import warnings
                tmp_mlb = MultiLabelBinarizer(classes=learner.mlb.classes_)
                try:
                    with warnings.catch_warnings():
                        warnings.simplefilter("ignore")
                        y_true_bin = tmp_mlb.fit_transform(y_true_tags_clean)
                        y_pred_bin = tmp_mlb.transform(y_pred_tags_clean)
                        micro_f1 = f1_score(y_true_bin, y_pred_bin, average="micro", zero_division=0)
                        macro_f1 = f1_score(y_true_bin, y_pred_bin, average="macro", zero_division=0)
                except Exception:
                    micro_f1, macro_f1 = 0, 0
            else:
                micro_f1, macro_f1 = 0, 0
            
            # Rewrite original prediction columns for historical batches to match new model
            df.loc[b_df.index, "auto_predicted_category"] = pred_cats
            df.loc[b_df.index, "auto_predicted_tags"] = pred_tags
            
            report_rows.append({
                "Trained_On_Batches": str(completed_batches[:i]),
                "Tested_On_Batch": b,
                "Test_Samples": len(y_true_cat),
                "Category_Accuracy": round(acc, 3),
                "Tag_Micro_F1": round(micro_f1, 3),
                "Tag_Macro_F1": round(macro_f1, 3)
            })
            
        # Train phase utilizing current batch as well
        train_df = confirmed_df[confirmed_df["annotation_batch"] <= b]
        learner.fit(train_df)
        
    last_accuracy = report_rows[-1]["Category_Accuracy"] if report_rows else 0

    # Save progressive report to CSV
    if report_rows:
        report_df = pd.DataFrame(report_rows)
        report_path = os.path.join(BASE_DIR, "ML_Performance_Report.csv")
        report_df.to_csv(report_path, index=False)

    # Finally, retrain on ALL fully completed batches before predicting on the new unconfirmed batch
    train_df_final = confirmed_df[confirmed_df["annotation_batch"] < next_batch]
    if not train_df_final.empty:
        learner.fit(train_df_final)

    # ========= PREDICT ON ALL UNCONFIRMED =========
    unconfirmed_idx = df[(df["is_manually_confirmed"] == False)].index
    predicted_count = 0
    if not unconfirmed_idx.empty:
        target_df = df.loc[unconfirmed_idx]
        pred_cats, pred_tags = learner.predict(target_df)
        
        cns_exact = ["Cell", "Nature", "Science (New York, N.Y.)"]
        def is_cns(journal_name):
            if pd.isna(journal_name): return False
            return str(journal_name).strip() in cns_exact

        batch_999_idx = []
        remaining_unconfirmed_idx = []
        
        for k, idx in enumerate(unconfirmed_idx):
            cat = pred_cats[k]
            tag = pred_tags[k]
            journal = df.loc[idx, "journal"]
            
            df.loc[idx, "category"] = cat
            df.loc[idx, "auto_predicted_category"] = cat
            df.loc[idx, "tags"] = tag
            df.loc[idx, "auto_predicted_tags"] = tag
            
            predicted_count += 1
            
            if cat == "Research" and not is_cns(journal):
                batch_999_idx.append(idx)
            else:
                remaining_unconfirmed_idx.append(idx)
                
        df.loc[batch_999_idx, "annotation_batch"] = 999
        
        curr_batch = int(next_batch) if next_batch else 1
        while remaining_unconfirmed_idx:
            conf_in_curr = len(confirmed_df[confirmed_df["annotation_batch"] == curr_batch])
            target_size = 50 * (2 ** (curr_batch - 1))
            needed = max(0, target_size - conf_in_curr)
            
            if needed > 0:
                take_idx = remaining_unconfirmed_idx[:needed]
                df.loc[take_idx, "annotation_batch"] = curr_batch
                remaining_unconfirmed_idx = remaining_unconfirmed_idx[needed:]
            
            curr_batch += 1
            
    save_df(df)

    return {
        "message": f"🧠 主动学习与分类推断完成！\n本次重新验证吸收了全量标定经验。\n已自动按指数扩大并推断剩余数据，将非CNS正刊【研究】退至 Batch 999 储备，已生成下一被标注目标：Batch {next_batch}！",
        "accuracy": last_accuracy,
        "next_batch": next_batch,
        "predicted_count": predicted_count,
        "status": "success"
    }

@app.post("/api/articles/{pmid}/annotate")
def annotate_article(pmid: str, data: AnnotationData):
    df = get_df()
    idx = df[df["pmid"].astype(str) == str(pmid)].index
    if idx.empty:
        raise HTTPException(status_code=404, detail="Article not found")
        
    df.loc[idx, "category"] = data.category
    df.loc[idx, "tags"] = data.tags
    df.loc[idx, "is_manually_confirmed"] = True
    save_df(df)
    return {"message": "Success"}

@app.post("/api/articles/{pmid}/discard")
def discard_article(pmid: str):
    df = get_df()
    idx = df[df["pmid"].astype(str) == str(pmid)].index
    if idx.empty:
        raise HTTPException(status_code=404, detail="Article not found")
    
    # [NEW] Tag as discarded, mark confirmed, keep in dataset
    current_tags = df.loc[idx, "tags"].iloc[0] if not pd.isna(df.loc[idx, "tags"].iloc[0]) else ""
    if "Discarded" not in str(current_tags):
        new_tags = f"{current_tags}; Discarded" if current_tags else "Discarded"
        df.loc[idx, "tags"] = new_tags
    
    df.loc[idx, "is_manually_confirmed"] = True
    save_df(df)
    
    return {"message": "Tagged as Discarded"}

@app.post("/api/articles/{pmid}/pdf/upload")
async def upload_pdf(pmid: str, category: str = Form(...), tags: str = Form(...), doi: str = Form(...), pub_year: str = Form(...), url: str = Form(...), file: UploadFile = File(...)):
    df = get_df()
    idx = df[df["pmid"].astype(str) == str(pmid)].index
    if idx.empty:
        raise HTTPException(status_code=404, detail="Article not found")
        
    row = df.loc[idx].iloc[0]
    
    # Priority: FormData -> Database Row -> "Unknown"
    final_pub_year = pub_year if (pd.notna(pub_year) and str(pub_year).strip() and pub_year != "Unknown") else str(row.get("pub_year", ""))
    if pd.isna(final_pub_year) or not final_pub_year: final_pub_year = "Unknown"
    
    final_tags = tags if (pd.notna(tags) and str(tags).strip()) else str(row.get("tags", category))
    if pd.isna(final_tags) or not final_tags: final_tags = category
    
    final_doi = doi if (pd.notna(doi) and str(doi).strip()) else str(row.get("doi", ""))
    if pd.isna(final_doi) or not final_doi: 
        final_doi = str(row.get("pmid", pmid))
        
    filename = f"{safe_filename(final_pub_year)}_{safe_filename(final_tags)}_{safe_filename(final_doi)}.pdf"
    
    cat_dir = os.path.join(PDF_DIR, safe_filename(category))
    os.makedirs(cat_dir, exist_ok=True)
    
    filepath = os.path.join(cat_dir, filename)
    with open(filepath, "wb") as f:
        shutil.copyfileobj(file.file, f)
        
    db_relative_path = f"PubMed_Spatial_Tracker/PDF_Archive/{safe_filename(category)}/{filename}"
    df.loc[idx, "pdf_path"] = db_relative_path
    df.loc[idx, "url"] = url
    df.loc[idx, "category"] = category
    df.loc[idx, "tags"] = tags
    df.loc[idx, "is_manually_confirmed"] = True
    save_df(df)
    return {"message": "PDF uploaded", "path": filepath}

@app.post("/api/articles/{pmid}/pdf/url")
def upload_pdf_url(pmid: str, data: dict):
    url = data.get("url")
    category = data.get("category", "Research")
    tags = data.get("tags", "")
    doi = data.get("doi", "")
    pub_year = data.get("pub_year", "")
    
    df = get_df()
    idx = df[df["pmid"].astype(str) == str(pmid)].index
    if idx.empty:
        raise HTTPException(status_code=404, detail="Article not found")
       
    try:
        r = requests.get(url, stream=True, timeout=15)
        r.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download from URL: {e}")

    row = df.loc[idx].iloc[0]
    final_pub_year = pub_year if (pd.notna(pub_year) and str(pub_year).strip() and pub_year != "Unknown") else str(row.get("pub_year", ""))
    if pd.isna(final_pub_year) or not final_pub_year: final_pub_year = "Unknown"
    
    final_tags = tags if (pd.notna(tags) and str(tags).strip()) else str(row.get("tags", category))
    if pd.isna(final_tags) or not final_tags: final_tags = category
    
    final_doi = doi if (pd.notna(doi) and str(doi).strip()) else str(row.get("doi", ""))
    if pd.isna(final_doi) or not final_doi: 
        final_doi = str(row.get("pmid", pmid))

    filename = f"{safe_filename(final_pub_year)}_{safe_filename(final_tags)}_{safe_filename(final_doi)}.pdf"
    cat_dir = os.path.join(PDF_DIR, safe_filename(category))
    os.makedirs(cat_dir, exist_ok=True)
    filepath = os.path.join(cat_dir, filename)
    
    with open(filepath, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)
            
    db_relative_path = f"PubMed_Spatial_Tracker/PDF_Archive/{safe_filename(category)}/{filename}"
    df.loc[idx, "pdf_path"] = db_relative_path
    df.loc[idx, "url"] = url
    df.loc[idx, "category"] = category
    df.loc[idx, "tags"] = tags
    df.loc[idx, "is_manually_confirmed"] = True
    save_df(df)
    return {"message": "PDF downloaded from URL", "path": filepath}

@app.post("/api/articles/{pmid}/pdf/save_link")
def save_pdf_link(pmid: str, data: dict):
    url = data.get("url")
    category = data.get("category", "Research")
    tags = data.get("tags", "")
    
    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")
        
    df = get_df()
    idx = df[df["pmid"].astype(str) == str(pmid)].index
    if idx.empty:
        raise HTTPException(status_code=404, detail="Article not found")
        
    df.loc[idx, "url"] = url
    df.loc[idx, "category"] = category
    df.loc[idx, "tags"] = tags
    df.loc[idx, "is_manually_confirmed"] = True
    save_df(df)
    return {"message": "URL saved", "path": url}

@app.get("/pdf")
def serve_pdf(path: str):
    if not path:
        raise HTTPException(status_code=400, detail="Path is empty")
        
    # Check if the path format includes the upper repo directory 
    # e.g., PubMed_Spatial_Tracker/PDF_Archive/...
    if path.startswith("PubMed_Spatial_Tracker/"):
        abs_path = os.path.join(os.path.dirname(BASE_DIR), path)
    else:
        # Fallback if the path is relative or absolute
        abs_path = path if os.path.isabs(path) else os.path.join(BASE_DIR, path)
        
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(abs_path, media_type="application/pdf")


class TagRenameData(BaseModel):
    old_tag: str
    new_tag: str
    
class TagDeleteData(BaseModel):
    tag: str

@app.put("/api/tags/rename")
def rename_tag(data: TagRenameData):
    df = get_df()
    if df.empty:
        return {"message": "Success"}
    
    def replace_tag(tags_str):
        if pd.isna(tags_str) or not str(tags_str).strip():
            return tags_str
        tags = [t.strip() for t in str(tags_str).split(";")]
        new_tags = [data.new_tag if t == data.old_tag else t for t in tags]
        new_tags = [t for t in new_tags if t]
        return "; ".join(new_tags)
        
    df["tags"] = df["tags"].apply(replace_tag)
    save_df(df)
    return {"message": "Success"}

@app.delete("/api/tags/delete")
def delete_tag(data: TagDeleteData):
    df = get_df()
    if df.empty:
        return {"message": "Success"}
        
    def remove_tag(tags_str):
        if pd.isna(tags_str) or not str(tags_str).strip():
            return tags_str
        tags = [t.strip() for t in str(tags_str).split(";")]
        new_tags = [t for t in tags if t != data.tag]
        new_tags = [t for t in new_tags if t]
        return "; ".join(new_tags)
        
    df["tags"] = df["tags"].apply(remove_tag)
    save_df(df)
    return {"message": "Success"}








@app.get("/api/tags")
def get_tags():
    tags_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tags.json")
    if os.path.exists(tags_path):
        import json
        with open(tags_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "metaCategory": ["General", "Technology", "Database", "Data Analysis"],
        "domain": ["Neuroscience", "Development", "Cancer", "Reproduction"],
        "technology": ["Visium", "MERFISH", "Slide-seq", "Stereo-seq", "Xenium", "CosMx"],
        "analysis": ["Clustering", "Deconvolution", "Imputation", "Cell Communication", "Spatial Trajectory"]
    }

@app.post("/api/tags")
async def update_tags(request: Request):
    tags_data = await request.json()
    tags_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tags.json")
    import json
    with open(tags_path, "w", encoding="utf-8") as f:
        json.dump(tags_data, f, ensure_ascii=False, indent=2)
    return {"status": "success", "message": "Tags updated"}

# Set up static directory for React

STATIC_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")


if __name__ == "__main__":

    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)