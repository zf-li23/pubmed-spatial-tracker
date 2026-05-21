"""PubMed search & fetch for spatial transcriptomics literature.
- Prefer Biopython Entrez when available
- CLI args: --retmax, --batch, --out, --incremental
- Per-batch incremental save and robust retries/timeouts
"""
import argparse
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

try:
    from Bio import Entrez
    HAVE_ENTREZ = True
except Exception:
    HAVE_ENTREZ = False

import pandas as pd
from tqdm import tqdm

# Defaults
EMAIL = "zf.li@siat.ac.cn"
OUT_PATH = "data/spatial_tracker/articles.csv"
QUERY = ('("Spatial Transcriptomics"[MeSH Major Topic]'
         ' OR "spatial transcriptom*"[Title/Abstract]'
         ' OR "spatially resolved transcriptom*"[Title/Abstract])'
         ' AND hasabstract[text] AND english[Language]'
         ' AND 2016:2026[dp]')


def search_pubmed_entrez(query: str, retmax: int = 20000) -> List[str]:
    Entrez.email = EMAIL
    handle = Entrez.esearch(db="pubmed", term=query, retmax=retmax)
    res = Entrez.read(handle)
    handle.close()
    return res.get("IdList", [])


def fetch_details_entrez(pmids, batch=200, save_every=2,
                         out=OUT_PATH, incremental=True):
    articles = []
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    total = len(pmids)
    for i in tqdm(range(0, total, batch), desc="Fetching", unit="batch"):
        batch_ids = pmids[i:i+batch]
        for attempt in range(3):
            try:
                handle = Entrez.efetch(db="pubmed", id=','.join(batch_ids), retmode="xml")
                batch_results = Entrez.read(handle)
                handle.close()
                # batch_results may contain PubmedArticle elements
                for rec in batch_results.get("PubmedArticle", []):
                    articles.append(_parse_entrez_record(rec))
                break
            except Exception:
                time.sleep(2)
        time.sleep(0.35)
        if incremental and (i // batch) % save_every == 0 and i > 0:
            _save_partial(articles, out)
    return articles


def _parse_entrez_record(record: dict) -> dict:
    # Similar parsing to script.py's parse_article
    medline = record.get("MedlineCitation", {})
    article = medline.get("Article", {})
    pmid = str(medline.get("PMID", ""))
    # DOI
    doi = ""
    for aid in record.get("PubmedData", {}).get("ArticleIdList", []):
        try:
            if getattr(aid, 'attributes', {}).get('IdType') == 'doi':
                doi = str(aid)
                break
        except Exception:
            continue
    title = article.get("ArticleTitle", "")
    journal = article.get("Journal", {}).get("Title", "")
    pub_year = ""
    pub_date = article.get("Journal", {}).get("JournalIssue", {}).get("PubDate", {})
    if isinstance(pub_date, dict):
        pub_year = pub_date.get("Year", "") or (pub_date.get("MedlineDate", "")[:4] if pub_date.get("MedlineDate") else "")
    abstract_texts = article.get("Abstract", {}).get("AbstractText", [])
    abstract = " ".join([str(t) for t in abstract_texts]) if abstract_texts else ""
    mesh_terms = []
    for mesh in medline.get("MeshHeadingList", []):
        desc = mesh.get("DescriptorName")
        if desc:
            mesh_terms.append(str(desc))
    mesh_str = "; ".join(mesh_terms)
    keywords = []
    kwlist = medline.get("KeywordList", [])
    if kwlist:
        for kw in kwlist[0]:
            keywords.append(str(kw))
    keywords_str = "; ".join(keywords)
    return {
        "pmid": pmid,
        "doi": doi,
        "title": title,
        "abstract": abstract,
        "pub_year": pub_year,
        "journal": journal,
        "mesh_terms": mesh_str,
        "keywords": keywords_str,
    }


def _save_partial(records: List[dict], out: str):
    if not records:
        return
    df = pd.DataFrame(records)
    # overwrite partial file to keep latest progress
    df.to_csv(out, index=False)


def search_pubmed_fallback(query: str, retmax: int = 20000) -> List[str]:
    # lightweight fallback using NCBI URL (no Entrez dependency)
    import urllib.request, urllib.parse, xml.etree.ElementTree as ET
    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    params = {'db': 'pubmed', 'term': query, 'retmax': retmax, 'email': EMAIL, 'tool': 'pubmed_tracker'}
    url = f"{BASE}/esearch.fcgi?{urllib.parse.urlencode(params)}"
    with urllib.request.urlopen(url, timeout=30) as r:
        txt = r.read().decode()
    root = ET.fromstring(txt)
    return [e.text for e in root.findall('.//Id') if e.text]


def fetch_details_fallback(pmids: List[str], batch: int = 100, save_every: int = 5, out: str = OUT_PATH, incremental: bool = True):
    import urllib.request, urllib.parse, xml.etree.ElementTree as ET
    BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    records = []
    total = len(pmids)
    for i in tqdm(range(0, total, batch), desc="Fetching", unit="batch"):
        batch_ids = pmids[i:i+batch]
        params = {'db': 'pubmed', 'id': ','.join(batch_ids), 'retmode': 'xml', 'email': EMAIL}
        url = f"{BASE}/efetch.fcgi?{urllib.parse.urlencode(params)}"
        for attempt in range(3):
            try:
                with urllib.request.urlopen(url, timeout=60) as r:
                    xml = r.read().decode()
                break
            except Exception:
                time.sleep(2)
        # parse xml
        root = ET.fromstring(xml)
        for art in root.findall('.//PubmedArticle'):
            med = art.find('MedlineCitation')
            if med is None:
                continue
            pmid = med.findtext('PMID', '')
            a = med.find('Article')
            if a is None:
                continue
            title = a.findtext('ArticleTitle', '')
            abs_parts = [p.text or '' for p in a.findall('.//AbstractText')]
            abstract = ' '.join(abs_parts)
            mesh = [h.findtext('DescriptorName', '') for h in med.findall('.//MeshHeading')]
            journal = a.findtext('Journal/Title', '')
            records.append({
                'pmid': pmid, 'title': title, 'abstract': abstract,
                'pub_year': (a.findtext('.//Journal/JournalIssue/PubDate/Year') or '')[:4],
                'journal': journal, 'mesh_terms': '; '.join(mesh)
            })
        time.sleep(0.35)
        if incremental and (i // batch) % save_every == 0 and i > 0:
            _save_partial(records, out)
    return records


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--retmax', type=int, default=20000)
    p.add_argument('--batch', type=int, default=100)
    p.add_argument('--out', type=str, default=OUT_PATH)
    p.add_argument('--incremental', action='store_true')
    p.add_argument('--save-every', type=int, default=5, help='save partial file every N batches')
    args = p.parse_args(argv)

    print('Searching PubMed...')
    if HAVE_ENTREZ:
        pmids = search_pubmed_entrez(QUERY, retmax=args.retmax)
    else:
        pmids = search_pubmed_fallback(QUERY, retmax=args.retmax)
    print(f'Found {len(pmids)} articles')
    if HAVE_ENTREZ:
        arts = fetch_details_entrez(pmids, batch=args.batch, save_every=args.save_every, out=args.out, incremental=args.incremental)
    else:
        arts = fetch_details_fallback(pmids, batch=args.batch, save_every=args.save_every, out=args.out, incremental=args.incremental)
    # final save
    if arts:
        _save_partial(arts, args.out)
        print(f'Saved {len(arts)} articles to {args.out}')
    else:
        print('No articles fetched.')


if __name__ == '__main__':
    main()
