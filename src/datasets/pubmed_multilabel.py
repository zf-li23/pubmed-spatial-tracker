"""PubMed-MultiLabel (Kaggle) loader."""

import numpy as np
import pandas as pd
from pathlib import Path
from .base import BiomedDataset


class PMLLoader(BiomedDataset):
    def __init__(self, path: str, use_processed: bool = False):
        super().__init__("pubmed_multilabel")
        self.path = Path(path)
        if self.path.is_dir():
            if use_processed:
                self.path = self.path / "PubMed Multi Label Text Classification Dataset Processed.csv"
            else:
                self.path = self.path / "PubMed Multi Label Text Classification Dataset.csv"
        df = pd.read_csv(self.path)
        self._pmids = df["pmid"].astype(str).tolist()
        self._titles = df["Title"].fillna("").tolist()
        self._abstracts = df["abstractText"].fillna("").tolist()
        # meshMajor is a stringified list
        raw_mesh = df.get("meshMajor", pd.Series([""] * len(df)))
        self._mesh_terms = [
            [m.strip() for m in str(v).strip("[]").replace("'", "").split(",") if m.strip()]
            if pd.notna(v) else []
            for v in raw_mesh
        ]
        # label columns: A B C D E F G H I J K L M N V Z
        label_cols = [c for c in df.columns if c.isupper() and len(c) == 1]
        self._label_names = label_cols
        self._labels = df[label_cols].fillna(0).values.astype(np.float32)

    def texts(self):
        return [f"{t} {a}" for t, a in zip(self._titles, self._abstracts)]

    def labels(self):
        return self._labels

    def pmids(self):
        return self._pmids

    def metadata(self):
        """Meta features: [title_len_norm, abstract_len_norm, num_mesh_norm]."""
        t_len = np.array([len(t) for t in self._titles], dtype=np.float64).reshape(-1, 1)
        a_len = np.array([len(a) for a in self._abstracts], dtype=np.float64).reshape(-1, 1)
        n_mesh = np.array([len(m) for m in self._mesh_terms], dtype=np.float64).reshape(-1, 1)
        t_len = (t_len - t_len.mean()) / (t_len.std() + 1e-8)
        a_len = (a_len - a_len.mean()) / (a_len.std() + 1e-8)
        n_mesh = (n_mesh - n_mesh.mean()) / (n_mesh.std() + 1e-8)
        return np.hstack([t_len, a_len, n_mesh])

    @property
    def n_labels(self):
        return self._labels.shape[1]

    @property
    def task_type(self):
        return "multilabel"

    @property
    def label_names(self):
        return self._label_names
