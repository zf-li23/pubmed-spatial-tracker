"""PubMed search & fetch for spatial transcriptomics literature."""
import json, time, sys, os
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Add Biopython Entrez
from Bio import Entrez
import pandas as pd

Entrez.email = os.getenv("ENTREZ_EMAIL", "anonymous@example.com")
Entrez.api_key = os.getenv("ENTREZ_API_KEY", "")

# Core search query - spatial transcriptomics as primary topic
QUERY = (
    '"Spatial Transcriptomics"[MeSH Major Topic]'
    " OR "
    '("spatial transcriptom*"[Title/Abstract]'
    ' OR "spatially resolved transcriptom*"[Title/Abstract])'
    " AND hasabstract[text]"
)


def search_pubmed(query: str, retmax: int = 10000) -> List[str]:
    """Return PMID list matching query."""
    handle = Entrez.esearch(db="pubmed", term=query, retmax=retmax, sort="relevance")
    record = Entrez.read(handle)
    handle.close()
    return record["IdList"]


def fetch_details(pmids: List[str], batch: int = 100) -> List[dict]:
    """Fetch article metadata in batches."""
    articles = []
    for i in range(0, len(pmids), batch):
        batch_ids = pmids[i:i+batch]
        handle = Entrez.efetch(db="pubmed", id=",".join(batch_ids),
                               retmode="xml", rettype="abstract")
        records = Entrez.read(handle)
        handle.close()
        for rec in records["PubmedArticle"]:
            articles.append(_parse_article(rec))
        time.sleep(0.5)
        print(f"  fetched {min(i+batch, len(pmids))}/{len(pmids)}", end="\r")
    print()
    return articles


def _parse_article(rec: dict) -> dict:
    med = rec["MedlineCitation"]
    art = med["Article"]
    pmid = str(med["PMID"])

    title = str(art.get("ArticleTitle", ""))
    abstract_parts = art.get("Abstract", {}).get("AbstractText", [])
    abstract = " ".join(str(p) for p in abstract_parts)

    mesh = []
    for heading in med.get("MeshHeadingList", []):
        desc = heading.get("DescriptorName", "")
        quals = [str(q) for q in heading.get("QualifierName", [])]
        mesh.append({"term": str(desc), "qualifiers": quals})

    # publication year
    pub_date = art.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
    year = pub_date.get("Year", "")
    if not year:
        year = pub_date.get("MedlineDate", "")[:4]

    journal = str(art.get("Journal", {}).get("Title", ""))
    authors = []
    for au in art.get("AuthorList", []):
        last = au.get("LastName", "")
        fore = au.get("ForeName", "")
        if last or fore:
            authors.append(f"{fore} {last}".strip())

    return {
        "pmid": pmid,
        "title": title,
        "abstract": abstract,
        "year": year,
        "journal": journal,
        "authors": "; ".join(authors[:10]),
        "mesh_terms": "; ".join(m["term"] for m in mesh),
    }


def save_dataset(articles: List[dict], path: str):
    df = pd.DataFrame(articles)
    df.to_csv(path, index=False)
    print(f"Saved {len(df)} articles to {path}")


if __name__ == "__main__":
    out = sys.argv[1] if len(sys.argv) > 1 else "data/spatial_tracker/articles.csv"
    Path(out).parent.mkdir(parents=True, exist_ok=True)

    print("Searching PubMed...")
    pmids = search_pubmed(QUERY)
    print(f"Found {len(pmids)} articles")

    print("Fetching details...")
    arts = fetch_details(pmids)

    save_dataset(arts, out)
