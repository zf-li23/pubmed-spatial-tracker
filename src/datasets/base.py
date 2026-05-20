"""Base dataset interface."""

import numpy as np
from abc import ABC, abstractmethod
from typing import List, Optional, Tuple


class BiomedDataset(ABC):
    """All datasets share this interface."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def texts(self) -> List[str]:
        """Title + abstract."""
        ...

    @abstractmethod
    def labels(self) -> np.ndarray:
        """Multi-label matrix, shape (n, n_labels)."""
        ...

    @abstractmethod
    def pmids(self) -> List[str]:
        ...

    @abstractmethod
    def metadata(self) -> Optional[np.ndarray]:
        """Extra numeric features, shape (n, n_feat). None if none."""
        ...

    @property
    @abstractmethod
    def n_labels(self) -> int:
        ...

    @property
    @abstractmethod
    def task_type(self) -> str:
        """'multilabel' | 'multiclass' | 'binary'"""
        ...

    def get_splits(self, seed: int = 42):
        """Train/test indices. Override for fixed splits."""
        from sklearn.model_selection import train_test_split
        n = len(self.texts())
        idx = np.arange(n)
        strat = self._stratify() if hasattr(self, '_stratify') else None
        tr, te = train_test_split(idx, test_size=0.2, random_state=seed, stratify=strat)
        return tr, te

    def __len__(self):
        return len(self.texts())
