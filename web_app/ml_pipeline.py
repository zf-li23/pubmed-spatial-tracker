import numpy as np
import pandas as pd

import os
# 设置 HuggingFace 镜像，解决国内网络无法直连下载预训练模型的问题
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from sentence_transformers import SentenceTransformer
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multiclass import OneVsRestClassifier
import json
import re

# Load centralized tags
TAGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tags.json")
try:
    with open(TAGS_PATH, "r", encoding="utf-8") as f:
        TAG_GROUPS = json.load(f)
except Exception:
    TAG_GROUPS = {
      "metaCategory": ["General", "Technology", "Database", "Data Analysis"],
      "domain": ["Neuroscience", "Development", "Cancer", "Reproduction"],
      "technology": ["Visium", "MERFISH", "Slide-seq", "Stereo-seq", "Xenium", "CosMx"],
      "analysis": ["Clustering", "Deconvolution", "Imputation", "Cell Communication", "Spatial Trajectory"]
    }

ALL_KNOWN_TAGS = set(sum(TAG_GROUPS.values(), []))

# Init embedding model globally to avoid reloading
EMBEDDING_MODEL = None
def get_embedding_model():
    global EMBEDDING_MODEL
    if EMBEDDING_MODEL is None:
        # A tiny and robust PLM model for generating text embeddings locally
        EMBEDDING_MODEL = SentenceTransformer('all-MiniLM-L6-v2') 
    return EMBEDDING_MODEL

def augment_text(title, abstract, pub_year=None, journal=None, mesh=None, kw=None, naive_cat=None, naive_tags=None):
    title = str(title).strip() if pd.notna(title) else ""
    abstract = str(abstract).strip() if pd.notna(abstract) else ""
    ncat_str = str(naive_cat).strip() if pd.notna(naive_cat) else ""
    ntag_str = str(naive_tags).strip() if pd.notna(naive_tags) else ""
    
    # We construct a clean semantic block for the transformer instead of bag of words
    context = f"Title: {title}. "
    if ncat_str: context += f"Category context: {ncat_str}. "
    if ntag_str: context += f"Keywords context: {ntag_str}. "
    context += f"Abstract: {abstract}"
    return context

def extract_top_tags(probs, classes, allowed_set, min_n=1, max_n=3, prob_thresh=0.2):
    valid_tags = []
    for tag, p in zip(classes, probs):
        if allowed_set is None or tag in allowed_set:
            valid_tags.append((tag, p))
    valid_tags.sort(key=lambda x: x[1], reverse=True)
    
    selected = [t for t, p in valid_tags if p > prob_thresh][:max_n]
    if len(selected) < min_n and valid_tags:
        selected = [valid_tags[i][0] for i in range(min(min_n, len(valid_tags)))]
    return selected

def guess_novel_name(title):
    # Heuristically try to extract a new technology, database or software name from title
    # Usually capitalized word before a colon or the first acronym
    match = re.search(r'^([A-Za-z0-9\-]+):', title)
    if match: return match.group(1).strip()
    return ""

class AutomatedActiveLearner:
    def __init__(self):
        self.clf_discard = None
        self.clf_category = None
        self.clf_tags = None
        self.mlb = MultiLabelBinarizer()
        
    def fit(self, train_df):
        X_train_text = [
            augment_text(t, a, py, j, m, k, nc, nt) 
            for t, a, py, j, m, k, nc, nt in zip(
                train_df["title"], train_df["abstract"], train_df["pub_year"],
                train_df["journal"], train_df["mesh_terms"], train_df["keywords"],
                train_df.get("naive_category", [""]*len(train_df)),
                train_df.get("naive_tags", [""]*len(train_df))
            )
        ]
        
        print(f"[*] Embedding {len(X_train_text)} training abstracts...")
        X_train_emb = get_embedding_model().encode(X_train_text, batch_size=32, show_progress_bar=False)
        
        tags_list = train_df["tags"].tolist()
        categories = train_df["category"].tolist()
        
        y_discard = [1 if "Discarded" in str(tg) else 0 for tg in tags_list]
        self.clf_discard = SVC(probability=True, class_weight={0: 5, 1: 1}, kernel='rbf', C=1.0)
        
        if sum(y_discard) == 0 or sum(y_discard) == len(y_discard):
            self.clf_discard = None
        else:
            self.clf_discard.fit(X_train_emb, y_discard)
            
        X_valid = []
        y_cat_valid = []
        y_tags_clean = []
        for i in range(len(X_train_emb)):
            if pd.notna(categories[i]) and str(categories[i]).strip():
                X_valid.append(X_train_emb[i])
                y_cat_valid.append(categories[i])
                raw_t = [tt.strip() for t in str(tags_list[i]).split(';') for tt in [t] if tt.strip() and tt.strip() != 'Discarded']
                y_tags_clean.append(raw_t)

        if not X_valid:
            X_valid = X_train_emb
            y_cat_valid = ["Research"] * len(X_train_emb)
            y_tags_clean = [[]] * len(X_train_emb)

        X_valid = np.array(X_valid)
        
        if len(set(y_cat_valid)) > 1:
            self.clf_category = SVC(probability=True, class_weight='balanced', kernel='rbf', C=1.0)
            self.clf_category.fit(X_valid, y_cat_valid)
        else:
            self.clf_category = None
            self.fallback_cat = y_cat_valid[0] if y_cat_valid else "Research"
            
        y_tags_bin = self.mlb.fit_transform(y_tags_clean)
        if len(self.mlb.classes_) > 1 and len(X_valid) > 1:
            # We use RandomForest for Multi-label to handle mixed overlapping tags properly
            self.clf_tags = OneVsRestClassifier(RandomForestClassifier(n_estimators=100, class_weight='balanced_subsample', max_depth=10))
            self.clf_tags.fit(X_valid, y_tags_bin)
        else:
            self.clf_tags = None

    def predict(self, pred_df):
        titles = pred_df["title"].tolist()
        X_target_text = [
            augment_text(t, a, py, j, m, k, nc, nt) 
            for t, a, py, j, m, k, nc, nt in zip(
                titles, pred_df["abstract"], pred_df["pub_year"],
                pred_df["journal"], pred_df["mesh_terms"], pred_df["keywords"],
                pred_df.get("naive_category", [""]*len(pred_df)),
                pred_df.get("naive_tags", [""]*len(pred_df))
            )
        ]
        
        print(f"[*] Embedding {len(X_target_text)} unannotated target documents...")
        X_target_emb = get_embedding_model().encode(X_target_text, batch_size=32, show_progress_bar=True)
        
        pred_cats = []
        pred_tags = []
        uncertainties = []
        
        if self.clf_category is not None:
            pred_cats_all = self.clf_category.predict(X_target_emb)
            pred_cats_probs = self.clf_category.predict_proba(X_target_emb)
        else:
            pred_cats_all = [self.fallback_cat] * len(X_target_emb)
            pred_cats_probs = np.ones((len(X_target_emb), 1))
            
        pred_tags_probs_all = self.clf_tags.predict_proba(X_target_emb) if self.clf_tags is not None else None
        
        if self.clf_discard is not None:
            is_discard_all = self.clf_discard.predict(X_target_emb) 
        else:
            is_discard_all = [0] * len(X_target_emb)

        for i in range(len(X_target_emb)):
            cat = pred_cats_all[i]
            pred_cats.append(cat)
            
            # Compute margin for uncertainty sample (top prob - second prob). Lower means more uncertain.
            # We invert it so higher score = more uncertain.
            probs = pred_cats_probs[i]
            sorted_probs = np.sort(probs)[::-1]
            margin = (sorted_probs[0] - sorted_probs[1]) if len(sorted_probs) > 1 else 1.0
            uncertainties.append(round(1.0 - margin, 4))
            
            tags = []
            if self.clf_tags is not None:
                probs_t = pred_tags_probs_all[i]
                
                # Rigid rules according to the design specification:
                if cat == "Review":
                    # 仅在“大类”和“领域”中二选一
                    allowed = set(TAG_GROUPS["metaCategory"] + TAG_GROUPS["domain"])
                    tags = extract_top_tags(probs_t, self.mlb.classes_, allowed, min_n=1, max_n=1, prob_thresh=0.0)
                
                elif cat == "Technology":
                    # 在"技术"中选一个，或者新创建
                    allowed = set(TAG_GROUPS["technology"])
                    tags = extract_top_tags(probs_t, self.mlb.classes_, allowed, min_n=0, max_n=2, prob_thresh=0.3)
                    novel_name = guess_novel_name(titles[i])
                    if len(tags) == 0 and novel_name:
                        tags.append(novel_name)
                    elif len(tags) == 0:
                        # Fallback choose 1 if strictly required
                        tags = extract_top_tags(probs_t, self.mlb.classes_, allowed, min_n=1, max_n=1, prob_thresh=0.0)
                
                elif cat == "Database":
                    # 直接新创建一个名字
                    novel_name = guess_novel_name(titles[i])
                    if novel_name: tags.append(novel_name)
                
                elif cat == "Data Analysis":
                    # 会在”分析“tag中选一个或多个，大概率新创建
                    allowed = set(TAG_GROUPS["analysis"])
                    tags = extract_top_tags(probs_t, self.mlb.classes_, allowed, min_n=1, max_n=3, prob_thresh=0.2)
                    novel_name = guess_novel_name(titles[i])
                    if novel_name and novel_name not in tags:
                        tags.append(novel_name)
                
                elif cat == "Research":
                    # 至少在“领域”中选1个，技术>=0 个
                    allowed_dom = set(TAG_GROUPS["domain"])
                    tags_dom = extract_top_tags(probs_t, self.mlb.classes_, allowed_dom, min_n=1, max_n=3, prob_thresh=0.1)
                    
                    allowed_tech = set(TAG_GROUPS["technology"])
                    tags_tech = extract_top_tags(probs_t, self.mlb.classes_, allowed_tech, min_n=0, max_n=2, prob_thresh=0.3)
                    
                    tags = tags_dom + tags_tech
            
            # Independent Discard evaluation
            if is_discard_all[i]:
                tags.append("Discarded")
                 
            # Distinct tags string
            cleaned_tags = []
            for tg in tags:
                if tg not in cleaned_tags: cleaned_tags.append(tg)
            pred_tags.append("; ".join(cleaned_tags))
                
        return pred_cats, pred_tags, uncertainties
