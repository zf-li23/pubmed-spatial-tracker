"""Meta feature extractor — wraps dataset.metadata() into standard API.

Usage:
    extractor = MetaExtractor(dataset=ds)
    X_meta = extractor.fit_transform(ds.texts())

The extractor delegates to ds.metadata() which each dataset implements
with its own available fields (year, text length, MeSH count, etc.).
All values are z-score normalized by the dataset.
"""

import numpy as np


class MetaExtractor:
    """Pass-through extractor that exposes dataset metadata as features."""

    def __init__(self, dataset=None):
        self.dataset = dataset

    def fit(self, texts=None):
        return self

    def transform(self, texts=None):
        if self.dataset is None:
            raise ValueError("MetaExtractor requires a dataset object. "
                             "Pass `dataset=ds` to constructor or use "
                             "get_cached_features() which provides it.")
        meta = self.dataset.metadata()
        if meta is None:
            raise ValueError(f"Dataset '{self.dataset.name}' has no metadata.")
        return np.asarray(meta, dtype=np.float64)

    def fit_transform(self, texts=None):
        return self.transform(texts)

