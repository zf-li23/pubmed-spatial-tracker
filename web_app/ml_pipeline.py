"""
web_app/ml_pipeline.py — 空间转录组文献分类器。

基于 TF-IDF（默认）或 sentence-transformers 做文本向量化，
SVC 做多分类（category）+ 多标签（tags）+ 二分类（discarded）。
"""

import numpy as np
import pandas as pd
import os
import json
import re

os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None

from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MultiLabelBinarizer
from sklearn.multiclass import OneVsRestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer

from web_app.shared import (
    load_tags,
    all_known_tags,
    guess_novel_name,
    enforce_category_tag_policy,
)

TAG_GROUPS = load_tags()

# 全局嵌入模型（惰性加载）
EMBEDDING_MODEL = None


def get_embedding_model():
    global EMBEDDING_MODEL
    if SentenceTransformer is None:
        return None
    if EMBEDDING_MODEL is None:
        EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
    return EMBEDDING_MODEL


def augment_text(title, abstract, pub_year=None, journal=None,
                 mesh=None, kw=None, naive_cat=None, naive_tags=None):
    """将文献多字段拼接为统一语义文本块，供向量化器使用。"""
    title = str(title or "").strip()
    abstract = str(abstract or "").strip()
    ncat_str = str(naive_cat or "").strip()
    ntag_str = str(naive_tags or "").strip()
    mesh_str = str(mesh or "").strip()
    kw_str = str(kw or "").strip()

    context = f"Title: {title}. "
    if ncat_str:
        context += f"Category context: {ncat_str}. "
    if ntag_str:
        context += f"Keywords context: {ntag_str}. "
    if mesh_str:
        context += f"MeSH: {mesh_str}. "
    context += f"Abstract: {abstract}"
    return context


def extract_top_tags(probs, classes, allowed_set, min_n=1, max_n=3, prob_thresh=0.2):
    """从多标签概率中按约束选取 top 标签。"""
    valid_tags = []
    for tag, p in zip(classes, probs):
        if allowed_set is None or tag in allowed_set:
            valid_tags.append((tag, p))
    valid_tags.sort(key=lambda x: x[1], reverse=True)

    selected = [t for t, p in valid_tags if p > prob_thresh][:max_n]
    if len(selected) < min_n and valid_tags:
        selected = [valid_tags[i][0] for i in range(min(min_n, len(valid_tags)))]
    return selected


class SpatialLiteratureClassifier:
    """
    空间转录组文献分类器。

    三个子任务：
    1. category: 多分类（Research / Review / Technology / Database / Data Analysis）
    2. tags:     多标签预测（domain / technology / analysis）
    3. discarded: 二分类（是否为无关文献）
    """

    def __init__(self):
        self.clf_category = None      # SVC 多分类
        self.clf_tags = None          # OneVsRestClassifier(SVC) 多标签
        self.clf_discard = None       # SVC 二分类
        self.mlb = MultiLabelBinarizer()
        self.vectorizer = None        # TfidfVectorizer 或 None（用 embedding）
        self._use_embeddings = get_embedding_model() is not None
        self._fitted = False

    def _build_features(self, texts):
        if self._use_embeddings:
            model = get_embedding_model()
            return model.encode(texts, batch_size=64, show_progress_bar=False)
        else:
            if self.vectorizer is None:
                self.vectorizer = TfidfVectorizer(
                    max_features=5000, ngram_range=(1, 2), stop_words="english"
                )
                return self.vectorizer.fit_transform(texts).toarray()
            return self.vectorizer.transform(texts).toarray()

    def fit(self, df):
        """
        用已确认样本训练三个分类器。

        df 需包含: title, abstract, category, tags, is_discarded
        （is_discarded 列由数据库迁移脚本保证存在）
        """
        texts = [
            augment_text(
                row.get("title", ""), row.get("abstract", ""),
                row.get("pub_year", ""), row.get("journal", ""),
                row.get("mesh_terms", ""), row.get("keywords", ""),
                row.get("naive_category", ""), row.get("naive_tags", ""),
            )
            for _, row in df.iterrows()
        ]
        X = self._build_features(texts)

        # 任务1: 类别多分类
        y_cat = df["category"].astype(str).values
        self.clf_category = SVC(probability=True, class_weight="balanced",
                                kernel="rbf", C=1.0, random_state=42)
        self.clf_category.fit(X, y_cat)

        # 任务2: 多标签预测
        tag_sets = [
            [t.strip() for t in str(r.get("tags", "")).split(";") if t.strip()]
            for _, r in df.iterrows()
        ]
        y_tags = self.mlb.fit_transform(tag_sets)
        if self.mlb.classes_.size > 0:
            self.clf_tags = OneVsRestClassifier(
                SVC(probability=True, kernel="linear", C=0.8, random_state=42)
            )
            self.clf_tags.fit(X, y_tags)
        else:
            self.clf_tags = None

        # 任务3: 二分类——Discarded
        if "is_discarded" in df.columns:
            y_discard = df["is_discarded"].astype(int).values
            if len(set(y_discard)) >= 2:
                self.clf_discard = SVC(probability=True, class_weight="balanced",
                                       kernel="rbf", C=1.0, random_state=42)
                self.clf_discard.fit(X, y_discard)
            else:
                self.clf_discard = None

        self._fitted = True

    def predict(self, df):
        """
        对未确认样本做三维预测，返回 (categories, tags, uncertainties, discarded_flags)。
        """
        if not self._fitted:
            raise RuntimeError("Classifier not fitted. Call .fit() first.")

        texts = [
            augment_text(
                row.get("title", ""), row.get("abstract", ""),
                row.get("pub_year", ""), row.get("journal", ""),
                row.get("mesh_terms", ""), row.get("keywords", ""),
                row.get("naive_category", ""), row.get("naive_tags", ""),
            )
            for _, row in df.iterrows()
        ]
        titles = df["title"].tolist()
        X = self._build_features(texts)

        # 类别预测 + 不确定性
        pred_cats = self.clf_category.predict(X).tolist()
        cat_probs = self.clf_category.predict_proba(X)

        # 多标签预测
        tag_probs_list = None
        if self.clf_tags is not None:
            tag_probs_list = self.clf_tags.predict_proba(X)

        # Discarded 预测
        discard_flags = [0] * len(X)
        if self.clf_discard is not None:
            discard_preds = self.clf_discard.predict(X)
            discard_flags = discard_preds.tolist()

        pred_tags_all = []
        uncertainties = []

        for i in range(len(X)):
            cat = pred_cats[i]

            # 不确定性 = 1 - margin
            probs_i = cat_probs[i]
            sorted_p = np.sort(probs_i)[::-1]
            margin = (sorted_p[0] - sorted_p[1]) if len(sorted_p) > 1 else 1.0
            uncertainties.append(round(1.0 - margin, 4))

            # 收集候选标签（ML 概率 + naive 候选，策略引擎统一清洗）
            candidate_tags = []
            if tag_probs_list is not None:
                probs_t = tag_probs_list[i]
                for t, p in zip(self.mlb.classes_, probs_t):
                    if p > 0.1:
                        candidate_tags.append(t)

            # 使用共享策略引擎做约束
            cleaned = enforce_category_tag_policy(cat, candidate_tags, title=titles[i])
            pred_tags_all.append("; ".join(cleaned))

        return pred_cats, pred_tags_all, uncertainties, discard_flags


# 兼容旧名
AutomatedActiveLearner = SpatialLiteratureClassifier
