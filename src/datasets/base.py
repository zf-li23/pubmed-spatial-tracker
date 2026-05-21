"""Dataset base."""

import numpy as np
from abc import ABC, abstractmethod


class BiomedDataset(ABC):

    def __init__(self, name):
        self.name = name

    @abstractmethod
    def texts(self):
        ...

    @abstractmethod
    def labels(self):
        ...

    @abstractmethod
    def pmids(self):
        ...

    @abstractmethod
    def metadata(self):
        ...

    @property
    @abstractmethod
    def n_labels(self):
        ...

    @property
    @abstractmethod
    def task_type(self):
        ...

    def get_splits(self, seed=42):
        from sklearn.model_selection import train_test_split
        n = len(self.texts())
        idx = np.arange(n)
        strat = self._stratify() if hasattr(self, '_stratify') else None
        tr, te = train_test_split(idx, test_size=0.2, random_state=seed, stratify=strat)
        return tr, te

    def __len__(self):
        return len(self.texts())
