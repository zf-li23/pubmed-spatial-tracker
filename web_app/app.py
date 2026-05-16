"""
web_app/app.py — PubMed Spatial Tracker FastAPI 后端。

路由：文献 CRUD、PDF 管理、标签管理、ML 重训触发。
"""
import os, io, shutil, re, sys, json, time
import uvicorn
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import requests
from typing import Optional, Any, List
from pydantic import BaseModel

# ── 路径 ──────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "web_app"))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError

DB_FILE = os.path.join(BASE_DIR, "spatial_literature.db")
ENGINE = create_engine(f"sqlite:///{DB_FILE}", future=True)
PDF_DIR = os.path.join(BASE_DIR, "PDF_Archive")

from dotenv import load_dotenv
load_dotenv(os.path.join(BASE_DIR, ".env"))


# ── 启动初始化 ───────────────────────────────────
def retire_annotation_batch_column():
    with ENGINE.connect() as con:
        table_exists = con.execute(text(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='literature'"
        ))
        if not table_exists.fetchone():
            return
        cols = [row[1] for row in con.execute(text("PRAGMA table_info(literature)")).fetchall()]
        if "annotation_batch" not in cols:
            return
        keep_cols = [c for c in cols if c != "annotation_batch"]
        select_cols = ", ".join([f'"{c}"' for c in keep_cols])
        con.execute(text(f"CREATE TABLE literature_new AS SELECT {select_cols} FROM literature"))
        con.execute(text("DROP TABLE literature"))
        con.execute(text("ALTER TABLE literature_new RENAME TO literature"))
        con.execute(text("CREATE INDEX IF NOT EXISTS idx_pmid ON literature(pmid)"))
        con.commit()


def ensure_manual_import_table():
    with ENGINE.connect() as con:
        con.execute(text("""
            CREATE TABLE IF NOT EXISTS manual_imported_pmids (
                pmid TEXT PRIMARY KEY,
                source TEXT DEFAULT 'manual_upload',
                imported_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """))
        con.execute(text(
            "CREATE INDEX IF NOT EXISTS idx_manual_imported_at ON manual_imported_pmids(imported_at)"
        ))
        con.commit()


def record_manual_imported_pmids(pmids, source="manual_upload"):
    if not pmids:
        return
    with ENGINE.begin() as con:
        for pmid in pmids:
            con.execute(
                text("INSERT OR IGNORE INTO manual_imported_pmids (pmid, source) VALUES (:pmid, :source)"),
                {"pmid": str(pmid), "source": source},
            )


CATEGORIES = ["Review", "Technology", "Database", "Data Analysis", "Research"]
for cat in CATEGORIES:
    os.makedirs(os.path.join(PDF_DIR, cat), exist_ok=True)

app = FastAPI(title="PubMed Spatial Tracker")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True,
    allow_methods=["*"], allow_headers=["*"],
)

retire_annotation_batch_column()
ensure_manual_import_table()


# ── 数据库操作（逐行 upsert，安全并发）────────────
def get_df() -> pd.DataFrame:
    """读取全表为 DataFrame（仅用于需要全量扫描的操作）。"""
    try:
        return pd.read_sql("SELECT * FROM literature", ENGINE)
    except Exception:
        return pd.DataFrame()


def save_df(df: pd.DataFrame):
    """逐行 upsert 写入，利用 pmid 主键避免全表覆盖。

    对于 DataFrame 中的每一行，根据 pmid 执行 INSERT OR REPLACE。
    使用事务保证原子性。
    """
    if df.empty:
        return
    with ENGINE.begin() as con:
        for _, row in df.iterrows():
            row_dict = row.to_dict()
            cols = list(row_dict.keys())
            placeholders = ", ".join([f":{c}" for c in cols])
            con.execute(
                text(f"INSERT OR REPLACE INTO literature ({', '.join(cols)}) VALUES ({placeholders})"),
                row_dict,
            )
    # 同步 article_tags
    _sync_article_tags(df)


def save_article(pmid: str, updates: dict):
    """更新单篇文献的部分字段（直接 SQL UPDATE，无 DataFrame 开销）。"""
    if not updates:
        return
    set_clause = ", ".join([f"{k}=:{k}" for k in updates])
    with ENGINE.begin() as con:
        result = con.execute(
            text(f"UPDATE literature SET {set_clause} WHERE pmid=:pmid"),
            {"pmid": str(pmid), **updates},
        )
    # 如果更新了 tags，同步 article_tags
    if "tags" in updates:
        _sync_single_article_tags(str(pmid), updates["tags"])


def _sync_article_tags(df: pd.DataFrame):
    """将 DataFrame 中每行的 tags 同步到 article_tags 表。"""
    from web_app.shared import load_tags
    tag_groups = load_tags()
    tag_to_group = {}
    for group, tags in tag_groups.items():
        for t in tags:
            tag_to_group[t.strip()] = group
    with ENGINE.begin() as con:
        for _, row in df.iterrows():
            pmid = str(row.get("pmid", ""))
            tags_str = str(row.get("tags", "") or "")
            con.execute(text("DELETE FROM article_tags WHERE pmid=:pmid"), {"pmid": pmid})
            for t in tags_str.split(";"):
                t = t.strip()
                if not t:
                    continue
                group = tag_to_group.get(t, "method_note")
                con.execute(
                    text("INSERT OR IGNORE INTO article_tags (pmid, tag, tag_group) VALUES (:pmid, :tag, :group)"),
                    {"pmid": pmid, "tag": t, "group": group},
                )


def _sync_single_article_tags(pmid: str, tags_str: str):
    from web_app.shared import load_tags
    tag_groups = load_tags()
    tag_to_group = {}
    for group, tags in tag_groups.items():
        for t in tags:
            tag_to_group[t.strip()] = group
    with ENGINE.begin() as con:
        con.execute(text("DELETE FROM article_tags WHERE pmid=:pmid"), {"pmid": pmid})
        for t in tags_str.split(";"):
            t = t.strip()
            if not t:
                continue
            group = tag_to_group.get(t, "method_note")
            con.execute(
                text("INSERT OR IGNORE INTO article_tags (pmid, tag, tag_group) VALUES (:pmid, :tag, :group)"),
                {"pmid": pmid, "tag": t, "group": group},
            )


# ── 工具函数 ──────────────────────────────────────
def safe_filename(name):
    if pd.isna(name) or not str(name).strip() or str(name).strip().lower() == "nan":
        return "Unknown"
    clean_str = str(name).strip()
    if clean_str.lower().endswith(".pdf"):
        clean_str = clean_str[:-4]
    clean_str = re.sub(r'[\r\n]+', '', clean_str)
    return re.sub(r'[\\/*?:"<>|; ]', '_', clean_str)


# ── 数据模型 ──────────────────────────────────────
class AnnotationData(BaseModel):
    category: str
    tags: str

class TagRenameData(BaseModel):
    old_tag: str
    new_tag: str

class TagDeleteData(BaseModel):
    tag: str


# ══════════════════════════════════════════════════
# API 路由
# ══════════════════════════════════════════════════

# ── PMID 上传 ─────────────────────────────────────
from Bio import Entrez
EMAIL = os.getenv("PUBMED_EMAIL", "zf-li23@mails.tsinghua.edu.cn")
Entrez.email = EMAIL


@app.post("/api/pmids/upload")
async def upload_pmids(file: UploadFile = File(...)):
    content = await file.read()
    lines = content.decode("utf-8").split("\n")
    pmids = [line.strip() for line in lines if line.strip().isdigit()]
    if not pmids:
        return {"message": "查无有效的 PMID。请确保文本文件里每行一个数字ID。"}

    df = get_df()
    existing_pmids = set(df["pmid"].astype(str))
    new_pmids = [p for p in pmids if p not in existing_pmids]

    if not new_pmids:
        record_manual_imported_pmids(pmids)
        return {"message": f"已记录 {len(pmids)} 个 PMID（无新增文献）", "count": 0}

    # 从 PubMed 获取新文献
    batch_size = 200
    new_articles = []
    for start in range(0, len(new_pmids), batch_size):
        end = min(len(new_pmids), start + batch_size)
        batch = new_pmids[start:end]
        try:
            h = Entrez.efetch(db="pubmed", id=",".join(batch), retmode="xml")
            results = Entrez.read(h)
            h.close()
            new_articles.extend(results.get("PubmedArticle", []))
        except Exception as e:
            print(f"Fetch batch failed: {e}")
            time.sleep(2)

    if not new_articles:
        return {"message": "获取新增文献失败，请检查网络或 PMID 是否有效。"}

    from migrate_naive import get_naive
    from main import parse_article

    records = []
    for rec in new_articles:
        try:
            parsed = parse_article(rec)
            if not parsed.get("pmid"):
                continue
            cat, tags = get_naive(parsed.get("title", ""), parsed.get("abstract", ""),
                                   parsed.get("journal", ""))
            parsed["naive_category"] = cat
            parsed["naive_tags"] = tags
            parsed["category"] = ""
            parsed["tags"] = ""
            parsed["is_manually_confirmed"] = 0
            parsed["is_discarded"] = 0
            records.append(parsed)
        except Exception as e:
            print(f"Parse failed: {e}")

    if records:
        df_new = pd.DataFrame(records)
        for c in df.columns:
            if c not in df_new.columns:
                df_new[c] = ""
        df_new = df_new[df.columns]
        df = pd.concat([df, df_new], ignore_index=True)
        save_df(df)
        record_manual_imported_pmids(new_pmids)

    return {"message": f"成功导入 {len(records)} 篇新文献", "count": len(records)}


# ── 文献列表 ──────────────────────────────────────
@app.get("/api/articles")
def get_articles():
    df = get_df()
    if df.empty:
        return []

    if "uncertainty_score" not in df.columns:
        df["uncertainty_score"] = 0.0
    if "is_discarded" not in df.columns:
        df["is_discarded"] = 0

    df = df.fillna("")
    df['is_confirmed_num'] = pd.to_numeric(df['is_manually_confirmed'], errors='coerce').fillna(0).astype(int)
    df['uncertainty_score_num'] = pd.to_numeric(df['uncertainty_score'], errors='coerce').fillna(0.0)
    df = df.sort_values(by=['is_confirmed_num', 'uncertainty_score_num'],
                         ascending=[True, False])
    df = df.drop(columns=['is_confirmed_num', 'uncertainty_score_num'])
    return df.to_dict(orient="records")


# ── 标注提交 ──────────────────────────────────────
@app.post("/api/articles/{pmid}/annotate")
def annotate_article(pmid: str, data: AnnotationData):
    save_article(pmid, {
        "category": data.category,
        "tags": data.tags,
        "is_manually_confirmed": 1,
        "is_discarded": 0,
    })
    return {"message": "Annotation saved"}


# ── Discarded 标记 ────────────────────────────────
@app.post("/api/articles/{pmid}/discard")
def discard_article(pmid: str):
    save_article(pmid, {
        "category": "Discard",
        "tags": "",
        "is_manually_confirmed": 1,
        "is_discarded": 1,
    })
    return {"message": "Marked as Discarded"}


# ── ML 重训 ───────────────────────────────────────
@app.post("/api/ml/active_learning")
def trigger_active_learning():
    df = get_df()
    confirmed_df = df[df["is_manually_confirmed"] == 1].copy()
    unconfirmed_df = df[df["is_manually_confirmed"] != 1].copy()

    if unconfirmed_df.empty:
        return {"message": "所有文献均已校验完毕。", "status": "done"}

    if len(confirmed_df) < 5:
        return {
            "message": f"当前仅标注了 {len(confirmed_df)} 篇，请至少标注 10~20 篇再训练。",
            "status": "need_data",
        }

    try:
        from web_app.ml_pipeline import SpatialLiteratureClassifier
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"ML 依赖缺失: {e}")

    learner = SpatialLiteratureClassifier()
    learner.fit(confirmed_df)
    pred_cats, pred_tags, uncertainties, discard_flags = learner.predict(unconfirmed_df)

    # 更新数据库
    for i, idx in enumerate(unconfirmed_df.index):
        save_article(str(df.at[idx, "pmid"]), {
            "auto_predicted_category": pred_cats[i],
            "auto_predicted_tags": pred_tags[i],
            "uncertainty_score": uncertainties[i],
            "is_discarded": int(discard_flags[i]),
        })

    return {
        "message": f"重训完成。基于 {len(confirmed_df)} 篇已确认样本，更新了 {len(unconfirmed_df)} 篇未确认文献的预测。",
        "status": "success",
    }


# ── PDF 上传 ──────────────────────────────────────
@app.post("/api/articles/{pmid}/pdf/upload")
async def upload_pdf(
    pmid: str,
    category: str = Form(""),
    tags: str = Form(""),
    doi: str = Form(""),
    pub_year: str = Form(""),
    url: str = Form(""),
    file: UploadFile = File(...),
):
    pmid_str = str(pmid)
    # 确认文献存在
    with ENGINE.connect() as con:
        row = con.execute(
            text("SELECT pmid FROM literature WHERE pmid=:pmid"), {"pmid": pmid_str}
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Article not found")

    cat_dir = category if category in CATEGORIES else "Research"
    safe_doi = re.sub(r'[\\/*?:"<>|]', '_', str(doi or pmid_str)[:60])
    year_str = str(pub_year or "Unknown")
    tags_abbr = "_".join([t.strip()[:12] for t in (tags or "").split(";") if t.strip()][:2]) or "NoTag"
    fname = f"{year_str}_{tags_abbr}_{safe_doi}.pdf"
    filepath = os.path.join(PDF_DIR, cat_dir, fname)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    db_relative_path = f"PDF_Archive/{cat_dir}/{fname}"
    save_article(pmid_str, {
        "category": category,
        "tags": tags,
        "pdf_path": db_relative_path,
        "url": url,
        "is_manually_confirmed": 1,
        "is_discarded": 0,
    })
    return {"message": "PDF uploaded", "path": filepath, "db_path": db_relative_path}


# ── PDF URL 抓取 ──────────────────────────────────
@app.post("/api/articles/{pmid}/pdf/download")
async def download_pdf(pmid: str, url: str = Form(""), category: str = Form(""),
                       tags: str = Form(""), doi: str = Form(""), pub_year: str = Form("")):
    pmid_str = str(pmid)
    with ENGINE.connect() as con:
        row = con.execute(
            text("SELECT pmid FROM literature WHERE pmid=:pmid"), {"pmid": pmid_str}
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Article not found")

    if not url:
        raise HTTPException(status_code=400, detail="URL is required")

    try:
        resp = requests.get(url, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to download PDF: {e}")

    cat_dir = category if category in CATEGORIES else "Research"
    safe_doi = re.sub(r'[\\/*?:"<>|]', '_', str(doi or pmid_str)[:60])
    year_str = str(pub_year or "Unknown")
    tags_abbr = "_".join([t.strip()[:12] for t in (tags or "").split(";") if t.strip()][:2]) or "NoTag"
    fname = f"{year_str}_{tags_abbr}_{safe_doi}.pdf"
    pdf_path = os.path.join(PDF_DIR, cat_dir, fname)
    with open(pdf_path, "wb") as f:
        f.write(resp.content)

    db_relative_path = f"PDF_Archive/{cat_dir}/{fname}"
    save_article(pmid_str, {
        "category": category,
        "tags": tags,
        "pdf_path": db_relative_path,
        "url": url,
        "is_manually_confirmed": 1,
        "is_discarded": 0,
    })
    return {"message": "Downloaded", "path": pdf_path, "db_path": db_relative_path}


# ── 仅存链接 ──────────────────────────────────────
@app.post("/api/articles/{pmid}/pdf/save_link")
async def save_link(pmid: str, url: str = Form(""), category: str = Form(""),
                    tags: str = Form("")):
    save_article(str(pmid), {
        "category": category,
        "tags": tags,
        "url": url,
        "is_manually_confirmed": 1,
        "is_discarded": 0,
    })
    return {"message": "URL saved", "path": url}


# ── PDF 服务 ──────────────────────────────────────
@app.get("/pdf")
def serve_pdf(path: str):
    if not path:
        raise HTTPException(status_code=400, detail="Path is empty")
    abs_path = os.path.join(BASE_DIR, path) if not os.path.isabs(path) else path
    if not os.path.exists(abs_path):
        raise HTTPException(status_code=404, detail="PDF not found")
    return FileResponse(abs_path, media_type="application/pdf")


# ── 标签管理 API ──────────────────────────────────
@app.get("/api/tags")
def get_tags():
    tags_path = os.path.join(BASE_DIR, "tags.json")
    if os.path.exists(tags_path):
        with open(tags_path, "r", encoding="utf-8") as f:
            return json.load(f)
    from web_app.shared import load_tags
    return load_tags()


@app.post("/api/tags")
async def update_tags(request: Request):
    tags_data = await request.json()
    tags_path = os.path.join(BASE_DIR, "tags.json")
    with open(tags_path, "w", encoding="utf-8") as f:
        json.dump(tags_data, f, ensure_ascii=False, indent=2)
    return {"status": "success", "message": "Tags updated"}


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
        return "; ".join([t for t in new_tags if t])

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
        return "; ".join([t for t in tags if t != data.tag])

    df["tags"] = df["tags"].apply(remove_tag)
    save_df(df)
    return {"message": "Success"}


# ── 静态文件 ──────────────────────────────────────
STATIC_DIR = os.path.join(os.path.dirname(__file__), "frontend", "dist")
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
