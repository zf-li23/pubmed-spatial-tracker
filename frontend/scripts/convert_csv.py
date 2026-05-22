#!/usr/bin/env python3
"""
合并 annotated_articles.csv + articles.csv（以 PMID 为键），输出 public/data/articles.json。

用法：
    python3 scripts/convert_csv.py

输入:
  - ../../data/spatial_tracker/annotated_articles.csv  (LLM 标注: category/tags/technology/...)
  - ../../data/spatial_tracker/articles.csv            (PubMed 元数据: abstract/mesh_terms/keywords)
输出:
  - ../public/data/articles.json
"""

import csv
import json
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(FRONTEND_DIR, '..', 'data', 'spatial_tracker')

ANNOTATED_PATH = os.path.join(DATA_DIR, 'annotated_articles.csv')
ARTICLES_PATH = os.path.join(DATA_DIR, 'articles.csv')
OUT_DIR = os.path.join(FRONTEND_DIR, 'public', 'data')
OUT_PATH = os.path.join(OUT_DIR, 'articles.json')


def parse_bool(val: str) -> bool:
    return val.strip().lower() in ('true', '1', 'yes')


def split_semicolon(val: str) -> list[str]:
    return [t.strip() for t in val.split(';') if t.strip()]


def main():
    for p in [ANNOTATED_PATH, ARTICLES_PATH]:
        if not os.path.exists(p):
            print(f"ERROR: CSV not found at {p}", file=sys.stderr)
            sys.exit(1)

    # 读取 articles.csv → pmid -> {abstract, mesh_terms, keywords}
    meta: dict[str, dict] = {}
    with open(ARTICLES_PATH, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            pid = row['pmid'].strip()
            meta[pid] = {
                'abstract': row.get('abstract', '').strip(),
                'mesh_terms': split_semicolon(row.get('mesh_terms', '')),
                'keywords': split_semicolon(row.get('keywords', '')),
            }

    # 读取 annotated_articles.csv 并合并
    articles = []
    missing = 0
    with open(ANNOTATED_PATH, 'r', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            pid = row['pmid'].strip()
            m = meta.get(pid, {})
            if not m:
                missing += 1
                m = {'abstract': '', 'mesh_terms': [], 'keywords': []}

            article = {
                'pmid': pid,
                'title': row['title'].strip(),
                'doi': row['doi'].strip(),
                'abstract': m['abstract'],
                'pub_year': row['pub_year'].strip(),
                'journal': row['journal'].strip(),
                'mesh_terms': m['mesh_terms'],
                'keywords': m['keywords'],
                # LLM 标注
                'category': row['category'].strip(),
                'tags': split_semicolon(row['tags']),
                'technology': split_semicolon(row['technology']),
                'biological_topic': row['biological_topic'].strip(),
                'has_new_data': parse_bool(row['has_new_data']),
                'has_code': parse_bool(row['has_code']),
                'confidence': row['confidence'].strip() or 'medium',
            }
            articles.append(article)

    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(articles, f, ensure_ascii=False, separators=(',', ':'))

    size_mb = os.path.getsize(OUT_PATH) / (1024 * 1024)
    print(f"✅ Merged {len(articles)} articles → {OUT_PATH} ({size_mb:.1f} MB)")
    if missing:
        print(f"⚠️  {missing} articles missing from articles.csv (no abstract/mesh/keywords)")


if __name__ == '__main__':
    main()
