"""LDA topic model as feature extractor."""

import numpy as np
from sklearn.decomposition import LatentDirichletAllocation
from sklearn.feature_extraction.text import CountVectorizer
from ..config import LDA_N_TOPICS


class LDAExtractor:
    def __init__(self, n_topics=LDA_N_TOPICS):
        self.cvec = CountVectorizer(max_features=2000, stop_words="english")
        self.lda = LatentDirichletAllocation(n_components=n_topics,
                                             random_state=42)

    def fit(self, texts):
        Xc = self.cvec.fit_transform(texts)
        self.lda.fit(Xc)
        return self

    def transform(self, texts):
        Xc = self.cvec.transform(texts)
        return self.lda.transform(Xc)

    def fit_transform(self, texts):
        Xc = self.cvec.fit_transform(texts)
        return self.lda.fit_transform(Xc)
