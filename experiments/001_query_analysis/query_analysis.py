"""001: PubMed query comparison."""
import csv, json, sys, time, os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent / "src"))

from Bio import Entrez

Entrez.email = "zf.li@siat.ac.cn"
OUT = Path(__file__).parent / "results"
OUT.mkdir(exist_ok=True)


def esearch_count(q: str) -> int:
    h = Entrez.esearch(db="pubmed", term=q, retmax=0)
    r = Entrez.read(h)
    h.close()
    return int(r["Count"])


def esearch_ids(q: str, label: str, retmax: int = 20000) -> set:
    """Fetch PMIDs up to retmax."""
    ids = set()
    for start in range(0, retmax, 5000):
        h = Entrez.esearch(db="pubmed", term=q, retmax=5000, retstart=start)
        r = Entrez.read(h)
        h.close()
        ids.update(r["IdList"])
        if len(r["IdList"]) < 5000:
            break
        time.sleep(0.35)
    print(f"  {label}: {len(ids)} ids")
    return ids


# ── Part 1: 各字段单独命中数 ──
print("=" * 50)
print("Part 1: Query variant counts")
print("=" * 50)

variants = [
    ("MeSH_Major",       '"Spatial Transcriptomics"[MeSH Major Topic]'),
    ("MeSH_All",         '"Spatial Transcriptomics"[Mesh]'),
    ("text_spatial",     '"spatial transcriptom*"[Title/Abstract]'),
    ("text_resolved",    '"spatially resolved transcriptom*"[Title/Abstract]'),
    ("text_both",        '("spatial transcriptom*"[Title/Abstract] OR "spatially resolved transcriptom*"[Title/Abstract])'),
    ("review_only",      '("spatial transcriptom*"[Title/Abstract] OR "spatially resolved transcriptom*"[Title/Abstract]) AND "Review"[pt]'),
    ("research_only",    '("spatial transcriptom*"[Title/Abstract] OR "spatially resolved transcriptom*"[Title/Abstract]) NOT "Review"[pt]'),
]

rows = []
for name, q in variants:
    c = esearch_count(q)
    rows.append({"variant": name, "query": q, "count": c})
    print(f"  {name:20s} {c:>6}")

with open(OUT / "query_counts.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["variant", "query", "count"])
    w.writeheader()
    w.writerows(rows)

# ── Part 2: 组合变体对比 ──
print("\n" + "=" * 50)
print("Part 2: Combined variant comparison")
print("=" * 50)

combos = [
    ("MeSH_Major_only",    '"Spatial Transcriptomics"[MeSH Major Topic]'),
    ("plus_text",          '("Spatial Transcriptomics"[MeSH Major Topic] OR "spatial transcriptom*"[Title/Abstract] OR "spatially resolved transcriptom*"[Title/Abstract])'),
    ("plus_hasabstract",   '("Spatial Transcriptomics"[MeSH Major Topic] OR "spatial transcriptom*"[Title/Abstract] OR "spatially resolved transcriptom*"[Title/Abstract]) AND hasabstract[text]'),
    ("no_letter_edit",     '("Spatial Transcriptomics"[MeSH Major Topic] OR "spatial transcriptom*"[Title/Abstract] OR "spatially resolved transcriptom*"[Title/Abstract]) AND hasabstract[text] NOT ("Letter"[pt] OR "Editorial"[pt] OR "Comment"[pt])'),
    ("since_2016",         '("Spatial Transcriptomics"[MeSH Major Topic] OR "spatial transcriptom*"[Title/Abstract] OR "spatially resolved transcriptom*"[Title/Abstract]) AND hasabstract[text] AND 2016:2026[dp]'),
    ("english_only",       '("Spatial Transcriptomics"[MeSH Major Topic] OR "spatial transcriptom*"[Title/Abstract] OR "spatially resolved transcriptom*"[Title/Abstract]) AND hasabstract[text] AND english[Language]'),
]

combo_rows = []
for name, q in combos:
    c = esearch_count(q)
    combo_rows.append({"variant": name, "count": c})
    print(f"  {name:25s} {c:>6}")

with open(OUT / "combined_counts.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["variant", "count"])
    w.writeheader()
    w.writerows(combo_rows)

# ── Part 3: 重叠分析 ──
print("\n" + "=" * 50)
print("Part 3: Overlap between MeSH Major and text words")
print("=" * 50)

maj = esearch_ids('"Spatial Transcriptomics"[MeSH Major Topic]', "MeSH_Major")
txt = esearch_ids(
    '("spatial transcriptom*"[Title/Abstract] OR "spatially resolved transcriptom*"[Title/Abstract])',
    "Text",
)

overlap = {
    "mesh_major_only": len(maj - txt),
    "text_only": len(txt - maj),
    "both": len(maj & txt),
    "union": len(maj | txt),
    "overlap_pct": round(len(maj & txt) / max(len(maj | txt), 1) * 100, 2),
}
print(json.dumps(overlap, indent=2))

with open(OUT / "overlap.json", "w") as f:
    json.dump(overlap, f, indent=2)

# ── Part 4: Final recommended query ──
print("\n" + "=" * 50)
print("Part 4: Final recommended query")
print("=" * 50)

final_variants = [
    ("C_hasabstract",     '("Spatial Transcriptomics"[MeSH Major Topic] OR ("spatial transcriptom*"[Title/Abstract] OR "spatially resolved transcriptom*"[Title/Abstract])) AND hasabstract[text]'),
    ("E_since_2016",      '("Spatial Transcriptomics"[MeSH Major Topic] OR ("spatial transcriptom*"[Title/Abstract] OR "spatially resolved transcriptom*"[Title/Abstract])) AND hasabstract[text] AND 2016:2026[dp]'),
    ("F_english",         '("Spatial Transcriptomics"[MeSH Major Topic] OR ("spatial transcriptom*"[Title/Abstract] OR "spatially resolved transcriptom*"[Title/Abstract])) AND hasabstract[text] AND english[Language]'),
    ("RECOMMENDED",       '("Spatial Transcriptomics"[MeSH Major Topic] OR ("spatial transcriptom*"[Title/Abstract] OR "spatially resolved transcriptom*"[Title/Abstract])) AND hasabstract[text] AND english[Language] AND 2016:2026[dp]'),
]

final_rows = []
for name, q in final_variants:
    c = esearch_count(q)
    final_rows.append({"variant": name, "count": c})
    print(f"  {name:20s} {c:>6}")

with open(OUT / "final_comparison.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["variant", "count"])
    w.writeheader()
    w.writerows(final_rows)

# ── Part 5: Verify overlap in final recommended set ──
print("\n" + "=" * 50)
print("Part 5: Overlap within recommended set (sampling IDs)")
print("=" * 50)

final_q = final_variants[-1][1]  # RECOMMENDED
h = Entrez.esearch(db="pubmed", term=final_q, retmax=0)
r = Entrez.read(h); h.close()
print(f"  Total: {r['Count']}")

# Sample year distribution
h = Entrez.esearch(db="pubmed", term=final_q, retmax=5000, retstart=0, sort="relevance")
r = Entrez.read(h); h.close()
sample_ids = r["IdList"]

import xml.etree.ElementTree as ET
year_counts = {}
for i in range(0, len(sample_ids), 200):
    batch = sample_ids[i:i+200]
    for attempt in range(3):
        try:
            h = Entrez.efetch(db="pubmed", id=",".join(batch), retmode="xml")
            tree = ET.parse(h)
            h.close()
            break
        except Exception as e:
            print(f"  retry {attempt+1} batch {i}: {e}")
            time.sleep(2)
    else:
        print(f"  SKIP batch {i}")
        continue
    for pub in tree.findall(".//PubDate"):
        y = pub.findtext("Year")
        if not y:
            y = (pub.findtext("MedlineDate") or "unknown")[:4]
        year_counts[y] = year_counts.get(y, 0) + 1
    time.sleep(0.35)

year_rows = sorted(year_counts.items())
with open(OUT / "year_distribution.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["year", "count"])
    w.writerows(year_rows)

for y, c in year_rows:
    bar = "#" * max(1, c // 10)
    print(f"  {y:6s} | {c:>4d} {bar}")

print("\nAll results saved to", OUT)
