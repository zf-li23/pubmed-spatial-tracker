import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multiclass import OneVsRestClassifier

import os
import json

# Load centralized tags
TAGS_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tags.json")
try:
    with open(TAGS_PATH, "r", encoding="utf-8") as f:
        TAG_GROUPS = json.load(f)
except Exception:
    # Fallback if tags.json is somehow missing
    TAG_GROUPS = {
      "metaCategory": ["General", "Technology", "Database", "Data Analysis"],
      "domain": ["Neuroscience", "Development", "Cancer", "Reproduction"],
      "technology": ["Visium", "MERFISH", "Slide-seq", "Stereo-seq", "Xenium", "CosMx"],
      "analysis": ["Clustering", "Deconvolution", "Imputation", "Cell Communication", "Spatial Trajectory"]
    }

ALL_KNOWN_TAGS = set(sum(TAG_GROUPS.values(), []))

def augment_text(title, abstract, pub_year=None, journal=None, mesh=None, kw=None, naive_cat=None, naive_tags=None):
    title = str(title) if pd.notna(title) else ""
    abstract = str(abstract) if pd.notna(abstract) else ""
    pub_year_str = str(pub_year) if pd.notna(pub_year) else ""
    journal_str = str(journal) if pd.notna(journal) else ""
    mesh_str = str(mesh) if pd.notna(mesh) else ""
    kw_str = str(kw) if pd.notna(kw) else ""
    ncat_str = str(naive_cat) if pd.notna(naive_cat) else ""
    ntag_str = str(naive_tags) if pd.notna(naive_tags) else ""
    
    prefix = " HAS_COLON " if ":" in title else " "
    return title + prefix + abstract + " " + pub_year_str + " " + journal_str + " " + mesh_str + " " + kw_str + " " + ncat_str + " " + ntag_str

def extract_top_tags(probs, classes, allowed_set, max_n=3, prob_thresh=0.3):
    valid_tags = []
    for tag, p in zip(classes, probs):
        if allowed_set is None or tag in allowed_set or tag not in ALL_KNOWN_TAGS:
            valid_tags.append((tag, p))
    valid_tags.sort(key=lambda x: x[1], reverse=True)
    selected = [t for t, p in valid_tags if p > prob_thresh]
    if not selected and valid_tags:
        selected = [valid_tags[0][0]] # Always output at least one tag if possible
    return selected[:max_n]

class AutomatedActiveLearner:
    def __init__(self):
        self.clf_discard = None
        self.clf_category = None
        self.clf_tags = None
        self.mlb = MultiLabelBinarizer()
        
    def fit(self, train_df):
        X_train = [
            augment_text(t, a, py, j, m, k) 
            for t, a, py, j, m, k in zip(
                train_df["title"], 
                train_df["abstract"],
                train_df["pub_year"],
                train_df["journal"],
                train_df["mesh_terms"],
                train_df["keywords"]
            )
        ]
        
        tags_list = train_df["tags"].tolist()
        categories = train_df["category"].tolist()
        
        y_discard = [1 if "Discarded" in str(tg) else 0 for tg in tags_list]
        self.clf_discard = Pipeline([
            ('tfidf', TfidfVectorizer(stop_words='english', max_features=5000)),
            ('clf', LogisticRegression(class_weight='balanced', max_iter=1000))
        ])
        
        # Guard against zero variance
        if sum(y_discard) == 0 or sum(y_discard) == len(y_discard):
            # No discard variance, fake it or skip
            self.clf_discard = None
        else:
            self.clf_discard.fit(X_train, y_discard)
            
        non_discard_idx = [i for i, y in enumerate(y_discard) if y == 0]
        if not non_discard_idx:
            return # Everything is discarded

        X_non_discard = [X_train[i] for i in non_discard_idx]
        y_cat_non_discard = [categories[i] for i in non_discard_idx]
        
        y_tags_raw = [str(tags_list[i]).split(';') for i in non_discard_idx]
        y_tags_clean = [[tt.strip() for t in ts for tt in [t] if tt.strip() and tt.strip() != 'Discarded'] for ts in y_tags_raw]
        
        # Ensure variance for categories
        if len(set(y_cat_non_discard)) > 1:
            self.clf_category = Pipeline([
                ('tfidf', TfidfVectorizer(stop_words='english', max_features=5000)),
                ('clf', LogisticRegression(class_weight='balanced', max_iter=1000))
            ])
            self.clf_category.fit(X_non_discard, y_cat_non_discard)
        else:
            self.clf_category = None
            self.fallback_cat = y_cat_non_discard[0] if y_cat_non_discard else "Research"
            
        y_tags_bin = self.mlb.fit_transform(y_tags_clean)
        if len(self.mlb.classes_) > 1 and len(X_non_discard) > 1:
            self.clf_tags = Pipeline([
                ('tfidf', TfidfVectorizer(stop_words='english', max_features=5000)),
                ('clf', OneVsRestClassifier(LogisticRegression(class_weight='balanced', max_iter=1000)))
            ])
            self.clf_tags.fit(X_non_discard, y_tags_bin)
        else:
            self.clf_tags = None

    def predict(self, pred_df):
        X_target = [
            augment_text(t, a, py, j, m, k, nc, nt) 
            for t, a, py, j, m, k, nc, nt in zip(
                pred_df["title"], 
                pred_df["abstract"],
                pred_df["pub_year"],
                pred_df["journal"],
                pred_df["mesh_terms"],
                pred_df["keywords"],
                pred_df.get("naive_category", [""]*len(pred_df)),
                pred_df.get("naive_tags", [""]*len(pred_df))
            )
        ]
        
        pred_cats = []
        pred_tags = []
        
        for i in range(len(X_target)):
            x_i = X_target[i:i+1]
            
            is_discard = 0
            if self.clf_discard is not None:
                is_discard = self.clf_discard.predict(x_i)[0]
                
            if is_discard:
                pred_cats.append("Discard")
                pred_tags.append("Discarded")
                continue
                
            if self.clf_category is not None:
                cat = self.clf_category.predict(x_i)[0]
            else:
                cat = self.fallback_cat
            pred_cats.append(cat)
            
            if self.clf_tags is not None:
                probs = self.clf_tags.predict_proba(x_i)[0]
                if cat == "Review":
                    allowed = set(TAG_GROUPS["metaCategory"] + TAG_GROUPS["domain"])
                    tags = extract_top_tags(probs, self.mlb.classes_, allowed, max_n=1, prob_thresh=0.1)
                elif cat == "Technology":
                    allowed = set(TAG_GROUPS["technology"])
                    tags = extract_top_tags(probs, self.mlb.classes_, allowed, max_n=2, prob_thresh=0.3)
                elif cat == "Data Analysis":
                    allowed = set(TAG_GROUPS["analysis"])
                    tags = extract_top_tags(probs, self.mlb.classes_, allowed, max_n=2, prob_thresh=0.3)
                elif cat == "Research":
                    allowed = set(TAG_GROUPS["domain"] + TAG_GROUPS["technology"])
                    tags = extract_top_tags(probs, self.mlb.classes_, allowed, max_n=2, prob_thresh=0.3)
                elif cat == "Database":
                    tags = extract_top_tags(probs, self.mlb.classes_, None, max_n=2, prob_thresh=0.2)
                else:
                    tags = extract_top_tags(probs, self.mlb.classes_, None, max_n=2, prob_thresh=0.3)
                pred_tags.append("; ".join(tags))
            else:
                pred_tags.append("")
                
        return pred_cats, pred_tags
