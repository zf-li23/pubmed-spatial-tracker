class MetaExtractor:
    def fit(self, texts=None):
        return self

    def transform(self, texts=None):
        return None  # meta is attached to dataset, not texts

    def fit_transform(self, texts=None):
        return None
