"""
Spatial Transcriptomics Article Annotation with LLM (DeepSeek).

Annotates PubMed articles with:
  - category:       main article type
  - tags:           data analysis methods used
  - technology:     spatial profiling platforms involved
  - biological_topic: application domain
  - has_new_data:   whether new experimental data was produced
  - has_code:       whether code/software is provided

Inspired by the two-stage annotation framework from Biomed-Enriched (2506.20331v1).
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests
from tqdm import tqdm

# ---------------------------------------------------------------------------
# Label Schema — full vocabulary for each annotation dimension
# ---------------------------------------------------------------------------

CATEGORIES = {
    "Research": "Original research with spatial transcriptomics data analysis and biological findings",
    "Review": "Comprehensive review, survey, or perspective article",
    "Technology": "New experimental technology, computational method, or software tool development",
    "Data Resource": "Database, atlas, benchmark dataset, or open-access data resource",
    "Benchmark": "Systematic comparison/benchmarking of existing methods or technologies",
    "Protocol": "Experimental protocol, step-by-step guide, or best practices",
}

TAGS_DATA_ANALYSIS = {
    "Spatial Domain Identification": "Clustering spots/regions into spatial domains or tissue regions (e.g., BayesSpace, STAGATE, SpaGCN, GraphST, BANKSY)",
    "Spatially Variable Genes": "Detection of genes with spatial expression patterns (e.g., SPARK, SpatialDE, Trendsceek, SOMDE, SMASH)",
    "Cell-Type Deconvolution": "Estimating cell-type proportions from spatial spots (e.g., RCTD, SPOTlight, cell2location, CARD, DestVI, stereoscope)",
    "Cell-Cell Communication": "Ligand-receptor analysis, cell-cell interaction, or signaling inference (e.g., CellChat, NicheNet, Giotto, SpaTalk, COMMOT)",
    "Spatial Trajectory Inference": "Pseudotime, RNA velocity, or spatiotemporal trajectory reconstruction",
    "Spatial Integration": "Alignment of multiple spatial slices/samples or batch correction (e.g., PASTE, STAligner, Harmony, scVI)",
    "Multi-Omics Integration": "Integration of spatial transcriptomics with proteomics, metabolomics, epigenomics, or other modalities",
    "Niche & Microenvironment": "Spatial niche analysis, microenvironment characterization, or neighborhood analysis",
    "Gene Imputation": "Imputation of missing genes or enhancement of spatial resolution (e.g., SpaGE, gimVI, stPlus)",
    "Spatial Co-Expression": "Spatially aware gene co-expression networks or gene regulatory networks",
    "Image-Based Analysis": "H&E/histology image processing, segmentation, feature extraction, or image-spot registration",
    "3D Reconstruction": "Three-dimensional reconstruction of spatial transcriptomics from 2D slices",
    "Benchmarking & Evaluation": "Benchmarking, evaluating, or comparing spatial methods or technologies",
    "Spatial Preprocessing": "Quality control, normalization, batch correction specific to spatial data",
    "Spatial Data Simulation": "In silico simulation of spatial transcriptomics data",
}

TECHNOLOGY_PLATFORMS = {
    "Visium": "Visium / Visium HD (10x Genomics) — spot-based, whole transcriptome",
    "MERFISH": "MERFISH / MERSCOPE (Vizgen) — single-cell resolution, multiplexed FISH",
    "Slide-seq": "Slide-seq / Slide-tags / Slide-seqV2 — bead-based spatial barcoding",
    "Stereo-seq": "Stereo-seq (BnBio/CST) — large field-of-view, nanometer resolution",
    "seqFISH": "seqFISH / seqFISH+ / seqFISH (various) — sequential FISH methods",
    "Xenium": "Xenium Analyzer (10x Genomics) — in situ, subcellular resolution",
    "CosMx": "CosMx Spatial Molecular Imager (NanoString/Bruker) — single-cell, protein+RNA",
    "STARmap": "STARmap / STARmap PLUS — in situ sequencing-based",
    "GeoMx": "GeoMx Digital Spatial Profiler (NanoString/Bruker) — region-based, protein+RNA",
    "DBiT-seq": "Deterministic Barcoding in Tissue for spatial omics",
    "Pixel-seq": "Pixel-seq / pixel-level spatial transcriptomics methods",
    "Curio Seeker": "Curio Seeker (commercial Slide-seq platform)",
    "NAVVIX": "NAVVIX (Vizgen) — next-gen spatial transcriptomics",
    "Molecular Cartography": "Molecular Cartography (Resolve Biosciences) — subcellular resolution",
    "Spatial ATAC-seq": "Spatially resolved ATAC-seq or multi-omic spatial methods",
    "HDST": "High-Definition Spatial Transcriptomics",
    "snmC-seq": "Spatial single-nucleus methylome or epigenomic methods",
    "Spatial CUT&Tag": "Spatial CUT&Tag / spatial epigenomic profiling",
    "LCM / Microdissection": "Laser Capture Microdissection coupled with transcriptomics",
}

BIOLOGICAL_TOPICS = {
    "Cancer": "Cancer biology, tumor microenvironment, oncology, metastasis",
    "Neuroscience": "Brain atlas, neural development, neurodegeneration, neurobiology",
    "Developmental Biology": "Embryogenesis, organogenesis, development across time",
    "Immunology": "Immune cell biology, inflammation, immunotherapy response",
    "Cardiovascular": "Heart development, cardiovascular disease",
    "Liver & Hepatology": "Liver biology, hepatology, liver disease",
    "Kidney & Nephrology": "Kidney biology, nephrology, kidney disease",
    "Lung & Respiratory": "Lung biology, respiratory system",
    "Gastrointestinal": "Gut biology, intestine, gastrointestinal tract",
    "Dermatology": "Skin biology, wound healing",
    "Musculoskeletal": "Muscle, bone, skeletal system",
    "Plant Biology": "Plant spatial transcriptomics, root/shoot development",
    "Aging": "Aging, senescence, longevity biology",
    "Infectious Disease": "Pathogen-host interaction, infection, host response",
    "Metabolism": "Metabolic diseases, obesity, diabetes",
    "Regeneration": "Tissue regeneration, stem cell biology",
    "Ophthalmology": "Eye biology, vision research",
}

# ---------------------------------------------------------------------------
# Prompt Templates
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are an expert biomedical annotator specializing in spatial transcriptomics literature. Your task is to analyze a PubMed article (title + abstract + MeSH terms + keywords) and classify it into structured labels.

For each article, output a JSON object with the following fields:

1. "category": (string, one of the below) — main article type
   - "Research" — original research with data analysis and biological findings
   - "Review" — comprehensive review/survey/perspective
   - "Technology" — new experimental tech, computational method, or software tool
   - "Data Resource" — database, atlas, benchmark dataset
   - "Benchmark" — systematic method comparison
   - "Protocol" — experimental protocol or guide

2. "tags": (list of strings) — data analysis METHODS used in the article. Choose from the list below. Only include tags explicitly mentioned or clearly implied. Max 4 tags.
   - "Spatial Domain Identification" — clustering spots into spatial domains
   - "Spatially Variable Genes" — detecting spatially variable genes
   - "Cell-Type Deconvolution" — estimating cell-type proportions
   - "Cell-Cell Communication" — ligand-receptor / cell interaction
   - "Spatial Trajectory Inference" — pseudotime or trajectory
   - "Spatial Integration" — aligning multiple slices/samples
   - "Multi-Omics Integration" — integrating with proteomics etc.
   - "Niche & Microenvironment" — niche / neighborhood analysis
   - "Gene Imputation" — imputing missing genes / enhancing resolution
   - "Spatial Co-Expression" — co-expression or gene regulatory networks
   - "Image-Based Analysis" — histology image processing / segmentation
   - "3D Reconstruction" — 3D reconstruction from 2D slices
   - "Benchmarking & Evaluation" — comparing methods
   - "Spatial Preprocessing" — QC / normalization / pipeline
   - "Spatial Data Simulation" — in silico data simulation

3. "technology": (list of strings) — spatial profiling TECHNOLOGIES involved. Choose from the list below. Max 3.
   - "Visium", "MERFISH", "Slide-seq", "Stereo-seq", "seqFISH", "Xenium", "CosMx", "STARmap", "GeoMx", "DBiT-seq", "Pixel-seq", "Curio Seeker", "NAVVIX", "Molecular Cartography", "Spatial ATAC-seq", "HDST", "snmC-seq", "Spatial CUT&Tag", "LCM / Microdissection"
   If none of the above match clearly, output an empty list [].

4. "biological_topic": (string or null) — primary application domain. Choose from:
   "Cancer", "Neuroscience", "Developmental Biology", "Immunology", "Cardiovascular", "Liver & Hepatology", "Kidney & Nephrology", "Lung & Respiratory", "Gastrointestinal", "Dermatology", "Musculoskeletal", "Plant Biology", "Aging", "Infectious Disease", "Metabolism", "Regeneration", "Ophthalmology"
   If unclear or not applicable, output null.

5. "has_new_data": (bool) — whether the article produced new experimental spatial data

6. "has_code": (bool) — whether the article provides code, software, or web tool

7. "is_preprint": (bool) — whether the article appears to be a preprint

8. "confidence": (string, one of "high", "medium", "low") — your confidence in this annotation

Output ONLY valid JSON, no other text."""

USER_PROMPT_TEMPLATE = """Analyze the following PubMed article for spatial transcriptomics annotation:

Title: {title}

Abstract: {abstract}

MeSH Terms: {mesh_terms}

Keywords: {keywords}

Return a JSON object with the 8 fields as specified in the system prompt."""


# ---------------------------------------------------------------------------
# API Client
# ---------------------------------------------------------------------------

def call_deepseek(
    title: str,
    abstract: str,
    mesh_terms: str,
    keywords: str,
    api_key: str = "sk-27482f0eceb3438dbc475ffafda3ddf7",
    model: str = "deepseek-v4-flash",
    base_url: str = "https://api.deepseek.com",
    timeout: int = 120,
    max_retries: int = 5,
) -> Optional[Dict]:
    """Send one article to DeepSeek and parse the JSON response."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    user_content = USER_PROMPT_TEMPLATE.format(
        title=title,
        abstract=abstract[:3000],  # limit abstract length
        mesh_terms=mesh_terms,
        keywords=keywords,
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
        "temperature": 0.05,  # low temperature for consistent classification
        "max_tokens": 1024,
        "response_format": {"type": "json_object"},
    }

    for attempt in range(1, max_retries + 1):
        try:
            resp = requests.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"]

            # Parse JSON
            parsed = json.loads(content)

            # Validate required fields
            required = ["category", "tags", "technology", "biological_topic",
                        "has_new_data", "has_code", "is_preprint", "confidence"]
            for field in required:
                if field not in parsed:
                    raise ValueError(f"Missing field: {field}")

            # Normalize bool fields
            for bf in ["has_new_data", "has_code", "is_preprint"]:
                if isinstance(parsed.get(bf), str):
                    parsed[bf] = parsed[bf].lower() in ("true", "yes", "y")
                parsed[bf] = bool(parsed.get(bf, False))

            return parsed

        except (requests.exceptions.RequestException, json.JSONDecodeError,
                ValueError, KeyError) as e:
            if attempt < max_retries:
                wait = 2 ** attempt
                print(f"  [Retry {attempt}/{max_retries}] {e} — waiting {wait}s",
                      flush=True)
                time.sleep(wait)
            else:
                print(f"  [FAILED] {e}", flush=True)
                return None

    return None


# ---------------------------------------------------------------------------
# Batch annotation
# ---------------------------------------------------------------------------

def annotate_batch(
    articles: pd.DataFrame,
    api_key: str = "sk-27482f0eceb3438dbc475ffafda3ddf7",
    model: str = "deepseek-v4-flash",
    base_url: str = "https://api.deepseek.com",
    batch_size: int = 10,
    sleep_per_article: float = 0.2,
    out: str = "data/spatial_tracker/annotated_articles.csv",
    start_from: int = 0,
):
    """Annotate a batch of articles using DeepSeek.

    For each article, calls the API, then appends the result to the output CSV
    incrementally so partial progress is never lost.
    """
    total = len(articles)
    Path(out).parent.mkdir(parents=True, exist_ok=True)

    # Auto-resume: load existing annotations if output file exists
    results = []
    existing_pmids = set()
    if os.path.isfile(out):
        try:
            existing = pd.read_csv(out)
            results = existing.to_dict("records")
            existing_pmids = {str(r["pmid"]) for r in results if pd.notna(r.get("pmid"))}
            print(f"   ↻ Found existing output: {len(results)} annotations loaded — will skip duplicates")
            # Auto-adjust start_from if not explicitly set
            if start_from == 0:
                start_from = 0  # still iterate from beginning to skip via PMID
        except (pd.errors.EmptyDataError, KeyError):
            print("   ⚠️  Could not read existing output — starting fresh")

    for idx in tqdm(range(start_from, total), desc="Annotating", unit="article"):
        row = articles.iloc[idx]
        pmid = str(row.get("pmid", ""))

        if pmid in existing_pmids:
            continue

        annot = call_deepseek(
            title=str(row.get("title", "")),
            abstract=str(row.get("abstract", "")),
            mesh_terms=str(row.get("mesh_terms", "")),
            keywords=str(row.get("keywords", "")),
            api_key=api_key,
            model=model,
            base_url=base_url,
        )

        record = {
            "pmid": pmid,
            "title": row.get("title", ""),
            "doi": row.get("doi", ""),
            "pub_year": row.get("pub_year", ""),
            "journal": row.get("journal", ""),
            "category": "",
            "tags": "",
            "technology": "",
            "biological_topic": "",
            "has_new_data": False,
            "has_code": False,
            "is_preprint": False,
            "confidence": "",
        }

        if annot:
            record["category"] = annot.get("category", "")
            record["tags"] = "; ".join(annot.get("tags", []))
            record["technology"] = "; ".join(annot.get("technology", []))
            record["biological_topic"] = annot.get("biological_topic") or ""
            record["has_new_data"] = annot.get("has_new_data", False)
            record["has_code"] = annot.get("has_code", False)
            record["is_preprint"] = annot.get("is_preprint", False)
            record["confidence"] = annot.get("confidence", "")

        results.append(record)

        # Incremental save every N articles
        if (idx + 1) % batch_size == 0:
            pd.DataFrame(results).to_csv(out, index=False)
            tqdm.write(f"  💾 Saved {len(results)} annotations to {out}")

        time.sleep(sleep_per_article)

    # Final save
    if results:
        pd.DataFrame(results).to_csv(out, index=False)
        print(f"\n✅ Saved {len(results)} annotations to {out}")
    else:
        print("\n⚠️  No results to save.")

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None):
    p = argparse.ArgumentParser(description="Annotate PubMed articles with DeepSeek")
    p.add_argument("--input", default="data/spatial_tracker/articles.csv",
                   help="Input CSV with articles (default: %(default)s)")
    p.add_argument("--output", default="data/spatial_tracker/annotated_articles.csv",
                   help="Output CSV path (default: %(default)s)")
    p.add_argument("--model", default="deepseek-v4-flash",
                   help="DeepSeek model name (default: %(default)s)")
    p.add_argument("--base-url", default="https://api.deepseek.com",
                   help="API base URL (default: %(default)s)")
    p.add_argument("--batch-size", type=int, default=10,
                   help="How often to save incremental output (default: %(default)d)")
    p.add_argument("--sleep", type=float, default=0.2,
                   help="Seconds between API calls (default: %(default).1f)")
    p.add_argument("--max-articles", type=int, default=None,
                   help="Limit number of articles to annotate (for testing)")
    p.add_argument("--start-from", type=int, default=0,
                   help="Resume from this row index (default: 0)")
    p.add_argument("--api-key", default=None,
                   help="DeepSeek API key. If not set, reads DEEPSEEK_API_KEY env var.")
    args = p.parse_args(argv)

    api_key = args.api_key or os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("❌ API key required. Set --api-key or DEEPSEEK_API_KEY environment variable.")
        sys.exit(1)

    print("📖 Reading articles...")
    df = pd.read_csv(args.input)
    print(f"   Loaded {len(df)} articles from {args.input}")

    if args.max_articles:
        df = df.iloc[:args.max_articles]
        print(f"   Annotating first {len(df)} articles (--max-articles)")

    print(f"🤖 Annotating with {args.model} via {args.base_url}")
    print(f"   Batch size (save interval): {args.batch_size}")
    print(f"   Sleep between calls: {args.sleep}s")
    if args.start_from > 0:
        print(f"   Resuming from row {args.start_from}")
    elif os.path.isfile(args.output):
        print(f"   ⏩ Auto-resume enabled — will skip already-annotated PMIDs")

    results = annotate_batch(
        articles=df,
        api_key=api_key,
        model=args.model,
        base_url=args.base_url,
        batch_size=args.batch_size,
        sleep_per_article=args.sleep,
        out=args.output,
        start_from=args.start_from,
    )

    # Print summary statistics
    if results:
        rdf = pd.DataFrame(results)
        print("\n📊 Annotation Summary:")
        print(f"   Total annotated: {len(rdf)}")
        cat_counts = rdf["category"].value_counts()
        for cat, cnt in cat_counts.items():
            print(f"   → {cat}: {cnt} ({100*cnt/len(rdf):.1f}%)")

        # Count unique tags
        all_tags = []
        for tags_str in rdf["tags"].dropna():
            all_tags.extend([t.strip() for t in tags_str.split(";") if t.strip()])
        if all_tags:
            from collections import Counter
            common_tags = Counter(all_tags).most_common(10)
            print(f"\n   Top-10 data analysis tags:")
            for tag, cnt in common_tags:
                print(f"   → {tag}: {cnt}")

        # Save annotation report
        report_path = args.output.replace(".csv", "_report.json")
        with open(report_path, "w") as f:
            json.dump({
                "total": len(rdf),
                "category_distribution": cat_counts.to_dict(),
                "top_tags": dict(common_tags),
            }, f, indent=2)
        print(f"\n📄 Report saved to {report_path}")


if __name__ == "__main__":
    main()
