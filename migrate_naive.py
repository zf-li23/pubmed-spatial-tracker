import pandas as pd
import numpy as np
import os
import json
import re

def load_tags():
    tags_path = "tags.json"
    if os.path.exists(tags_path):
        with open(tags_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "technology": ["Visium", "MERFISH", "Slide-seq", "Stereo-seq", "Xenium", "CosMx"],
        "analysis": ["Clustering", "Deconvolution", "Imputation", "Cell Communication", "Spatial Trajectory"],
        "domain": ["Neuroscience", "Development", "Cancer", "Reproduction"]
    }

TAG_GROUPS = load_tags()

GENERIC_NAME_STOPWORDS = {
    "a", "an", "the", "study", "analysis", "analyses", "method", "methods", "tool", "tools",
    "model", "models", "framework", "pipeline", "approach", "database", "atlas", "resource",
    "repository", "portal", "review", "benchmark", "single", "cell", "spatial", "multi", "omics",
    "for", "of", "in", "on", "using", "with"
}


def _uniq_keep_order(items):
    seen = set()
    out = []
    for it in items:
        if it and it not in seen:
            seen.add(it)
            out.append(it)
    return out


def _clean_candidate_name(name):
    name = re.sub(r"\s+", " ", str(name or "").strip(" .,:;()[]{}\"'"))
    return name


def _is_good_novel_candidate(name):
    if not name:
        return False
    n = _clean_candidate_name(name)
    if len(n) < 3 or len(n) > 48:
        return False

    tokens = [t for t in re.split(r"[\s\-/]+", n) if t]
    if not tokens:
        return False

    low_tokens = [t.lower() for t in tokens]
    if all(t in GENERIC_NAME_STOPWORDS for t in low_tokens):
        return False

    if n.lower() in GENERIC_NAME_STOPWORDS:
        return False

    has_signal = bool(re.search(r"[A-Z]", n)) or bool(re.search(r"\d", n))
    return has_signal


def guess_novel_name(title):
    title = str(title) if title is not None else ""
    if not title:
        return ""

    candidates = []

    match = re.search(r"^([^:]{2,80}):", title)
    if match:
        candidates.append(match.group(1))

    for pat in [
        r"\b([A-Z][A-Za-z0-9\-]{2,})\s+(?:database|atlas|resource|repository|portal|browser|knowledgebase)\b",
        r"\b([A-Z][A-Za-z0-9\-]{2,})\s+(?:method|framework|pipeline|algorithm|model|tool|approach)\b",
    ]:
        m = re.search(pat, title, flags=re.IGNORECASE)
        if m:
            candidates.append(m.group(1))

    head = title.split(":", 1)[0]
    for tok in re.findall(r"\b[A-Za-z][A-Za-z0-9\-]{2,}\b", head):
        if re.search(r"[A-Z]", tok) or re.search(r"\d", tok):
            candidates.append(tok)

    for c in candidates:
        c = _clean_candidate_name(c)
        if _is_good_novel_candidate(c):
            return c
    return ""


def enforce_category_tag_policy(category, tags, title=""):
    """Apply the same category-tag constraints used by ML prediction path."""
    tags = _uniq_keep_order([str(t).strip() for t in tags if str(t).strip()])

    meta_tags = TAG_GROUPS.get("metaCategory", ["General", "Technology", "Database", "Data Analysis"])
    domain_tags = TAG_GROUPS.get("domain", [])
    tech_tags = TAG_GROUPS.get("technology", [])
    analysis_tags = TAG_GROUPS.get("analysis", [])

    if category == "Review":
        allowed = set(meta_tags + domain_tags)
        chosen = [t for t in tags if t in allowed]
        if not chosen:
            chosen = ["General"]
        return chosen[:1]

    if category == "Technology":
        chosen = [t for t in tags if t in set(tech_tags)]
        if not chosen:
            novel = guess_novel_name(title)
            if novel:
                chosen = [novel]
        if not chosen and tech_tags:
            chosen = [tech_tags[0]]
        return chosen[:2]

    if category == "Database":
        novel = guess_novel_name(title)
        if novel:
            return [novel]
        # If no reliable name is found, avoid outputting noisy non-database generic tags.
        return []

    if category == "Data Analysis":
        chosen = [t for t in tags if t in set(analysis_tags)]
        chosen = chosen[:3]
        novel = guess_novel_name(title)
        if novel:
            chosen = [novel] + [t for t in chosen if t != novel][:2]
        return chosen[:3]

    # Research: at least one domain + optional technologies.
    dom = [t for t in tags if t in set(domain_tags)]
    tech = [t for t in tags if t in set(tech_tags)]
    if not dom and domain_tags:
        dom = [domain_tags[0]]
    return (dom[:3] + tech[:2])

def get_naive(title, abstract, journal):
    title_lower = str(title).lower() if pd.notna(title) else ""
    abstract_lower = str(abstract).lower() if pd.notna(abstract) else ""
    journal_lower = str(journal).lower() if pd.notna(journal) else ""
    combined_text = title_lower + " " + abstract_lower
    
    tags = []
    
    category = "Research" # 默认兜底
    
    # 根据在 tags.json 匹配到的标签所在的 group 来动态推断大类
    group_counts = {g: 0 for g in TAG_GROUPS.keys()}
    
    for group, group_tags in TAG_GROUPS.items():
        for tag in group_tags:
            t_lower = str(tag).lower()
            # 简单的全词匹配，避免部分前缀匹配（为简单起见先使用in，但可使用正则来提升精度）
            if t_lower in combined_text or t_lower.replace("-", "") in combined_text:
                tags.append(tag)
                group_counts[group] += 1
                
    # 去重并保持顺序
    tags = _uniq_keep_order(tags)
    
    if "Review".lower() in title_lower or "Review".lower() in journal_lower:
        category = "Review"
    elif group_counts.get("database", 0) > 0 or "database".lower() in title_lower:
        category = "Database"
    elif group_counts.get("technology", 0) > 0 and group_counts.get("analysis", 0) == 0:
        category = "Technology"
    elif group_counts.get("analysis", 0) > 0:
        category = "Data Analysis"

    tags = enforce_category_tag_policy(category, tags, title=title)
        
    return category, "; ".join(tags)

if __name__ == "__main__":
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///spatial_literature.db")
    df = pd.read_sql("SELECT * FROM literature", engine)
    if "naive_category" not in df.columns:
        df["naive_category"] = ""
    if "naive_tags" not in df.columns:
        df["naive_tags"] = ""
        
    for idx, row in df.iterrows():
        cat, tags = get_naive(row["title"], row["abstract"], row["journal"])
        df.at[idx, "naive_category"] = cat
        df.at[idx, "naive_tags"] = tags
        
    df.to_sql("literature", engine, index=False, if_exists="replace")
    print("Naive re-computed with new tags!")
