"""
web_app/shared.py — 公共函数：标签本体加载、新实体提取、分类器约束策略。

本模块是 migrate_naive.py 和 ml_pipeline.py 的单一真相源。
"""

import json
import os
import re

# ── 路径 ──────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAGS_PATH = os.path.join(BASE_DIR, "tags.json")

# ── 通用停用词（防止泛词被当作新实体提取） ──────────
GENERIC_NAME_STOPWORDS = {
    "a", "an", "the", "study", "analysis", "analyses", "method", "methods",
    "tool", "tools", "model", "models", "framework", "pipeline", "approach",
    "database", "atlas", "resource", "repository", "portal", "review",
    "benchmark", "single", "cell", "spatial", "multi", "omics",
    "for", "of", "in", "on", "using", "with",
}

# ── 标签加载 ──────────────────────────────────────────
def load_tags(tags_path=None):
    """加载 tags.json，返回分组字典。"""
    path = tags_path or TAGS_PATH
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    # 默认兜底
    return {
        "domain": ["Neuroscience", "Development", "Cancer", "Reproduction",
                    "Pathology", "Immunology", "Zoology", "Cardiology",
                    "Lung", "Bone Tissues", "Plant"],
        "technology": ["Visium", "MERFISH", "Slide-seq", "Stereo-seq", "Xenium",
                       "CosMx", "GeoMx", "DBiT-seq", "seqFISH", "ISS",
                       "FISH", "FFPE", "RNAscope", "ISH"],
        "analysis": ["Clustering", "Deconvolution", "Imputation",
                     "Cell Communication", "Spatial Trajectory",
                     "Multimodal integration", "Domain Identification",
                     "Gene Expression Prediction", "Segmentation",
                     "Differential Expression", "Diffusion",
                     "Dimensionality Reduction", "RNA Co-localization",
                     "Denoising", "Application", "Benchmark",
                     "Foundation", "Pipeline", "Visualization", "huSA"],
        "method_note": [],
    }


def all_known_tags(tag_groups=None):
    """返回所有已知标签的集合。"""
    if tag_groups is None:
        tag_groups = load_tags()
    return set(sum(tag_groups.values(), []))


# ── 工具函数 ──────────────────────────────────────────
def _uniq_keep_order(items):
    """去重，保持原始顺序。"""
    seen = set()
    out = []
    for it in items:
        if it and it not in seen:
            seen.add(it)
            out.append(it)
    return out


def _clean_candidate_name(name):
    """清理候选实体名称。"""
    name = re.sub(r"\s+", " ", str(name or "").strip(" .,:;()[]{}\"'"))
    return name


def _is_good_novel_candidate(name):
    """判断候选名称是否值得作为新实体标签。"""
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


# ── 新实体名称提取 ────────────────────────────────────
def guess_novel_name(title):
    """从标题中提取可能的新数据库名/方法名/管道名作为候选标签。

    策略：
    1. 冒号前缀（常见于论文标题）："XXX: ..."
    2. 命名模式匹配："XXX database/atlas/..." 或 "XXX method/framework/..."
    3. 首段大写驼峰词抽取
    """
    title = str(title) if title is not None else ""
    if not title:
        return ""

    candidates = []

    # 策略1: 冒号前缀
    match = re.search(r"^([^:]{2,80}):", title)
    if match:
        candidates.append(match.group(1))

    # 策略2: 命名模式
    for pat in [
        r"\b([A-Z][A-Za-z0-9\-]{2,})\s+(?:database|atlas|resource|repository|portal|browser|knowledgebase)\b",
        r"\b([A-Z][A-Za-z0-9\-]{2,})\s+(?:method|framework|pipeline|algorithm|model|tool|approach)\b",
    ]:
        m = re.search(pat, title, flags=re.IGNORECASE)
        if m:
            candidates.append(m.group(1))

    # 策略3: 驼峰词抽取
    head = title.split(":", 1)[0]
    for tok in re.findall(r"\b[A-Za-z][A-Za-z0-9\-]{2,}\b", head):
        if re.search(r"[A-Z]", tok) or re.search(r"\d", tok):
            candidates.append(tok)

    for c in candidates:
        c = _clean_candidate_name(c)
        if _is_good_novel_candidate(c):
            return c
    return ""


# ── 分类器约束策略 ────────────────────────────────────
def enforce_category_tag_policy(category, tags, title="", tag_groups=None):
    """对给定类别和候选标签施加约束策略，返回清洗后的标签列表。

    规则摘要：
    - Review:     仅1个 domain/metaCategory 标签；无命中则 "General"
    - Technology: 最多2个 technology 标签；无命中尝试新实体提取
    - Database:   优先新实体提取；失败则空列表（不输出泛词）
    - Data Analysis: 最多3个 analysis 标签；可附一个新实体名
    - Research:   至少1个 domain + 可选 technology 标签
    """
    if tag_groups is None:
        tag_groups = load_tags()

    tags = _uniq_keep_order([str(t).strip() for t in tags if str(t).strip()])

    # 构建分组映射：{tag_name: group_name}
    tag_to_group = {}
    for group, group_tags in tag_groups.items():
        for t in group_tags:
            tag_to_group[t] = group

    domain_tags = tag_groups.get("domain", [])
    tech_tags = tag_groups.get("technology", [])
    analysis_tags = tag_groups.get("analysis", [])

    if category == "Review":
        allowed = set(domain_tags)
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
        return []

    if category == "Data Analysis":
        chosen = [t for t in tags if t in set(analysis_tags)]
        chosen = chosen[:3]
        novel = guess_novel_name(title)
        if novel:
            chosen = [novel] + [t for t in chosen if t != novel][:2]
        return chosen[:3]

    # Research
    dom = [t for t in tags if t in set(domain_tags)]
    tech = [t for t in tags if t in set(tech_tags)]
    if not dom and domain_tags:
        dom = [domain_tags[0]]
    return (dom[:3] + tech[:2])
