"""PubMed search & fetch for spatial transcriptomics literature."""
import json, time, sys, os
from pathlib import Path
from typing import List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from Bio import Entrez
import pandas as pd

Entrez.email = os.getenv("ENTREZ_EMAIL", "zf.li@siat.ac.cn")
Entrez.api_key = os.getenv("ENTREZ_API_KEY", "")

# Final search query (see experiments/001_query_analysis for analysis)
#   MeSH Major + text words + hasabstract + english + 2016-2026 → 9,148 articles
QUERY = (
    '("Spatial Transcriptomics"[MeSH Major Topic]'
    ' OR ("spatial transcriptom*"[Title/Abstract]'
    ' OR "spatially resolved transcriptom*"[Title/Abstract]))'
    ' AND hasabstract[text] AND english[Language] AND 2016:2026[dp]'
)
OUT_PATH = "data/spatial_tracker/articles.csv"


def search_pubmed(query: str, retmax: int = 20000) -> List[str]:
    handle = Entrez.esearch(db="pubmed", term=query, retmax=retmax, sort="relevance")
    record = Entrez.read(handle)
    handle.close()
    return record["IdList"]


def fetch_details(pmids: List[str], batch: int = 100) -> List[dict]:
    articles = []
    for i in range(0, len(pmids), batch):
        batch_ids = pmids[i:i+batch]
        handle = Entrez.efetch(db="pubmed", id=",".join(batch_ids),
                               retmode="xml", rettype="abstract")
        records = Entrez.read(handle)
        handle.close()
        for rec in records["PubmedArticle"]:
            articles.append(_parse(rec))
        time.sleep(0.35)
        print(f"  fetched {min(i+batch, len(pmids))}/{len(pmids)}", end="\r")
    print()
    return articles


def _parse(rec: dict) -> dict:
    med = rec["MedlineCitation"]
    art = med["Article"]
    pmid = str(med["PMID"])
    title = str(art.get("ArticleTitle", ""))
    parts = art.get("Abstract", {}).get("AbstractText", [])
    abstract = " ".join(str(p) for p in parts)
    mesh = []
    for h in med.get("MeshHeadingList", []):
        mesh.append(str(h.get("DescriptorName", "")))
    pd = art.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
    year = pd.get("Year", "") or pd.get("MedlineDate", "")[:4]
    journal = str(art.get("Journal", {}).get("Title", ""))
    authors = []
    for au in art.get("AuthorList", []):
        n = " ".join(filter(None, [au.get("LastName", ""), au.get("ForeName", "")]))
        if n:
            authors.append(n)
    return {
        "pmid": pmid, "title": title, "abstract": abstract,
        "year": year, "journal": journal,
        "authors": "; ".join(authors[:10]),
        "mesh_terms": "; ".join(mesh),
    }


def save(articles: List[dict], path: str):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    df = pd.DataFrame(articles)
    df.to_csv(path, index=False)
    print(f"Saved {len(df)} articles to {path}")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else OUT_PATH
    print("Searching PubMed...")
    pmids = search_pubmed(QUERY)
    print(f"Found {len(pmids)} articles")
    print("Fetching details...")
    arts = fetch_details(pmids)
    save(arts, out)
