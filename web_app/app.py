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
from typing import Optional, Any
from pydantic import BaseModel

# Setup Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sqlite3
from sqlalchemy import create_engine, text
DB_FILE = os.path.join(BASE_DIR, "spatial_literature.db")
engine = create_engine(f"sqlite:///{DB_FILE}")
PDF_DIR = os.path.join(BASE_DIR, "PDF_Archive")


def retire_annotation_batch_column():
    with engine.connect() as con:
        table_exists = con.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='literature'"))
        if not table_exists.fetchone():
            return

        cols = [row[1] for row in con.execute(text("PRAGMA table_info(literature)")).fetchall()]
        if "annotation_batch" not in cols:
            return

        keep_cols = [c for c in cols if c != "annotation_batch"]
        if not keep_cols:
            return

        select_cols = ", ".join([f'"{c}"' for c in keep_cols])
        con.execute(text(f"CREATE TABLE literature_new AS SELECT {select_cols} FROM literature"))
        con.execute(text("DROP TABLE literature"))
        con.execute(text("ALTER TABLE literature_new RENAME TO literature"))
        con.execute(text("CREATE INDEX IF NOT EXISTS idx_pmid ON literature(pmid)"))
        con.commit()


def ensure_manual_import_table():
    with engine.connect() as con:
        con.execute(text("""
            CREATE TABLE IF NOT EXISTS manual_imported_pmids (
                pmid TEXT PRIMARY KEY,
                source TEXT DEFAULT 'manual_upload',
                imported_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))
        con.execute(text("CREATE INDEX IF NOT EXISTS idx_manual_imported_at ON manual_imported_pmids(imported_at)"))
        con.commit()


def record_manual_imported_pmids(pmids, source="manual_upload"):
    if not pmids:
        return
    with engine.connect() as con:
        for pmid in pmids:
            con.execute(
                text("""
                    INSERT OR IGNORE INTO manual_imported_pmids (pmid, source)
                    VALUES (:pmid, :source)
                """),
                {"pmid": str(pmid), "source": source},
            )
        con.commit()

# Initialize PDF subfolders
CATEGORIES = ["Review", "Technology", "Database", "Data Analysis", "Research"]
for cat in CATEGORIES:
    os.makedirs(os.path.join(PDF_DIR, cat), exist_ok=True)

app = FastAPI(title="PubMed Annotation Tool")

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

retire_annotation_batch_column()
ensure_manual_import_table()

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
    try:
        return pd.read_sql("SELECT * FROM literature", engine)
    except Exception:
        return pd.DataFrame()

from threading import Lock
df_lock = Lock()

def save_df(df):
    with df_lock:
        df.to_sql('literature', engine, index=False, if_exists='replace')
        with engine.connect() as con:
            try: con.execute(text('CREATE INDEX IF NOT EXISTS idx_pmid ON literature(pmid)'))
            except: pass
            con.commit()

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
            "is_manually_confirmed": 0,
            "pdf_path": "",
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
        
        # 记录手动导入的 PMID 到 SQLite，替代外部 txt 记录
        new_pmids_list = df_new["pmid"].tolist()
        record_manual_imported_pmids(new_pmids_list)
        
    return {"message": f"成功下载并导入了 {len(new_rows)} 篇您手动提供的 PubMed 文献，并已纳入当前统一推送队列。"}

@app.get("/api/articles")
def get_articles():
    df = get_df()
    if df.empty:
        return []
    
    if "uncertainty_score" not in df.columns:
        df["uncertainty_score"] = 0.0
        
    df['is_manually_confirmed'] = pd.to_numeric(df['is_manually_confirmed'], errors='coerce').fillna(0).astype(int)
    
    df = df.fillna("")
    
    # 置顶未核验记录，高不确定性分数靠前
    df['uncertainty_score_num'] = pd.to_numeric(df['uncertainty_score'], errors='coerce').fillna(0.0)
    df = df.sort_values(by=['is_manually_confirmed', 'uncertainty_score_num'], ascending=[True, False])
    df = df.drop(columns=['uncertainty_score_num'])
    
    return df.to_dict(orient="records")

class AnnotationData(BaseModel):
    category: str
    tags: str

@app.post("/api/ml/active_learning")
def trigger_active_learning():
    df = get_df()
    
    confirmed_df = df[df["is_manually_confirmed"] == 1]
    unconfirmed_df = df[df["is_manually_confirmed"] == 0]
    
    if unconfirmed_df.empty:
        return {"message": "✅ 恭喜！当前库中所有文章均已校验完毕！", "status": "done"}
    
    if len(confirmed_df) < 5:
        return {
            "message": f"当前仅标注了 {len(confirmed_df)} 篇，请至少先标注并校验 10~20 篇数据，模型才拥有足够的基线样本来学习！", 
            "status": "need_data"
        }

    try:
        from ml_pipeline import AutomatedActiveLearner
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"Please install required ML libraries! {str(e)}")

    learner = AutomatedActiveLearner()
    
    # 在全部人工确认的数据上进行拟合（Active Learning 的知识吸取）
    learner.fit(confirmed_df)
    
    # 在全部未确认的数据上推送最新预测与计算疑惑度 (Uncertainty Score)
    pred_cats, pred_tags, uncertainties = learner.predict(unconfirmed_df)
    
    # 更新推断与分数
    df.loc[df["is_manually_confirmed"] == 0, "auto_predicted_category"] = pred_cats
    df.loc[df["is_manually_confirmed"] == 0, "auto_predicted_tags"] = pred_tags
    df.loc[df["is_manually_confirmed"] == 0, "uncertainty_score"] = uncertainties
    
    save_df(df)

    return {
        "message": f"🎉 AI 重训成功！\n基于已标注的 {len(confirmed_df)} 篇样本重构了认知网络。\n余下无标签文献已按【不确定性分数】重新计算并置顶排列，\n请在上方优先标注最具有信息量（最棘手）的一批文章！",
        "status": "success"
    }

@app.post("/api/articles/{pmid}/annotate")
def annotate_article(pmid: str, data: AnnotationData):
    with engine.connect() as con:
        result = con.execute(text("UPDATE literature SET category=:cat, tags=:tags, is_manually_confirmed=1 WHERE pmid=:pmid"), 
                             {"cat": data.category, "tags": data.tags, "pmid": pmid})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Article not found")
        con.commit()
    return {"message": "Success"}

@app.post("/api/articles/{pmid}/discard")
def discard_article(pmid: str):
    with engine.connect() as con:
        row = con.execute(text("SELECT tags FROM literature WHERE pmid=:pmid"), {"pmid": pmid}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Article not found")
        
        current_tags = str(row[0]) if row[0] is not None else ""
        if "Discarded" not in current_tags:
            new_tags = f"{current_tags}; Discarded" if current_tags else "Discarded"
        else:
            new_tags = current_tags
            
        con.execute(text("UPDATE literature SET tags=:tags, is_manually_confirmed=1 WHERE pmid=:pmid"), 
                    {"tags": new_tags, "pmid": pmid})
        con.commit()
    return {"message": "Discard tagged successfully"}

@app.post("/api/articles/{pmid}/pdf/upload")
async def upload_pdf(pmid: str, category: str = Form(""), tags: str = Form(""), doi: str = Form(""), pub_year: str = Form(""), url: str = Form(""), file: UploadFile = File(...)):
    df = get_df()
    pmid_str = str(pmid)
    with engine.connect() as con: row = con.execute(text("SELECT pmid FROM literature WHERE pmid=:pmid"), {"pmid": pmid}).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Article not found")
        
    row = df[df["pmid"].astype(str) == pmid_str].iloc[0]
    
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
    pmid_str = str(pmid)
    df.loc[df["pmid"].astype(str) == pmid_str, "pdf_path"] = db_relative_path
    df.loc[df["pmid"].astype(str) == pmid_str, "url"] = url
    df.loc[df["pmid"].astype(str) == pmid_str, "category"] = category
    df.loc[df["pmid"].astype(str) == pmid_str, "tags"] = tags
    df.loc[df["pmid"].astype(str) == pmid_str, "is_manually_confirmed"] = 1
    save_df(df)
    return {"message": "PDF uploaded", "path": filepath, "db_path": db_relative_path}

class URLDownloadData(BaseModel):
    url: Optional[Any] = ""
    category: Optional[Any] = ""
    tags: Optional[Any] = ""
    doi: Optional[Any] = ""
    pub_year: Optional[Any] = ""

@app.post("/api/articles/{pmid}/pdf/url")
def download_pdf_from_url(pmid: str, request_data: URLDownloadData):
    url = str(request_data.url) if request_data.url else ""
    category = str(request_data.category) if request_data.category else ""
    tags = str(request_data.tags) if request_data.tags else ""
    doi = str(request_data.doi) if request_data.doi else ""
    pub_year = str(request_data.pub_year) if request_data.pub_year else ""
    
    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")
        
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
        r = requests.get(url, stream=True, timeout=15, headers=headers)
        r.raise_for_status()
        
        # Guard against HTML responses when PDF is requested (e.g. Publisher paywalls/CAPTCHAs)
        content_type = r.headers.get("Content-Type", "")
        if "text/html" in content_type:
            raise Exception("URL returned HTML webpage instead of a PDF file. The publisher may require login, Javascript execution, or CAPTCHA. Please manually download and upload.")
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download PDF from URL: {str(e)}")
        
    df = get_df()
    with engine.connect() as con:
        row = con.execute(text("SELECT title FROM literature WHERE pmid=:pmid"), {"pmid": pmid}).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Article not found")
        title = row[0]
    
    cat_dir = os.path.join(PDF_DIR, safe_filename(category))
    os.makedirs(cat_dir, exist_ok=True)
    
    final_pub_year = pub_year if (pd.notna(pub_year) and str(pub_year).strip() and pub_year != "Unknown") else "Unknown"
    final_tags = tags if (pd.notna(tags) and str(tags).strip()) else category
    final_doi = doi if (pd.notna(doi) and str(doi).strip()) else pmid
        
    filename = f"{safe_filename(final_pub_year)}_{safe_filename(final_tags)}_{safe_filename(final_doi)}.pdf"
    pdf_path = os.path.join(cat_dir, filename)
    
    with open(pdf_path, "wb") as f_out:
        for chunk in r.iter_content(chunk_size=8192):
            f_out.write(chunk)
            
    db_relative_path = f"PubMed_Spatial_Tracker/PDF_Archive/{safe_filename(category)}/{filename}"
    
    pmid_str = str(pmid)
    df.loc[df["pmid"].astype(str) == pmid_str, "pdf_path"] = db_relative_path
    df.loc[df["pmid"].astype(str) == pmid_str, "url"] = url
    df.loc[df["pmid"].astype(str) == pmid_str, "category"] = category
    df.loc[df["pmid"].astype(str) == pmid_str, "tags"] = tags
    df.loc[df["pmid"].astype(str) == pmid_str, "is_manually_confirmed"] = 1
    save_df(df)
    
    return {"message": "Downloaded", "path": pdf_path, "db_path": db_relative_path}

class SaveLinkData(BaseModel):
    url: Optional[Any] = ""
    category: Optional[Any] = ""
    tags: Optional[Any] = ""

@app.post("/api/articles/{pmid}/pdf/save_link")
def save_link_only(pmid: str, request_data: SaveLinkData):
    url = str(request_data.url) if request_data.url else ""
    category = str(request_data.category) if request_data.category else ""
    tags = str(request_data.tags) if request_data.tags else ""
    
    if not url:
        raise HTTPException(status_code=400, detail="No URL provided")
        
    df = get_df()
    pmid_str = str(pmid)
    df.loc[df["pmid"].astype(str) == pmid_str, "url"] = url
    df.loc[df["pmid"].astype(str) == pmid_str, "category"] = category
    df.loc[df["pmid"].astype(str) == pmid_str, "tags"] = tags
    df.loc[df["pmid"].astype(str) == pmid_str, "is_manually_confirmed"] = 1
    save_df(df)

    with engine.connect() as con:
        result = con.execute(text("UPDATE literature SET url=:url, category=:cat, tags=:tags, is_manually_confirmed=1 WHERE pmid=:pmid"), 
                             {"url": url, "cat": category, "tags": tags, "pmid": pmid})
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail="Article not found")
        con.commit()
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