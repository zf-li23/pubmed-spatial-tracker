"""TF-IDF vectorizer wrapper."""

from sklearn.feature_extraction.text import TfidfVectorizer
from ..config import TFIDF_MAX_FEAT


class TFIDFExtractor:
    def __init__(self, max_features=TFIDF_MAX_FEAT):
        self.vec = TfidfVectorizer(max_features=max_features,
                                   ngram_range=(1, 2), sublinear_tf=True)

    def fit(self, texts):
        self.vec.fit(texts)
        return self

    def transform(self, texts):
        return self.vec.transform(texts)

    def fit_transform(self, texts):
        return self.vec.fit_transform(texts)
