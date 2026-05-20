"""OHSUMED dataset loader.

TREC format lines:
.I <id>
.U <medline-ui>
.S <source>
.M <MeSH terms; separated>
.T <title>
.P <publication type>
.W <abstract>
.A <authors>
"""

import numpy as np
import re
from pathlib import Path
from sklearn.preprocessing import MultiLabelBinarizer
from .base import BiomedDataset


class OHSUMEDLoader(BiomedDataset):
    def __init__(self, path: str, min_df: int = 5):
        super().__init__("ohsumed")
        self.path = Path(path)
        self._parse()
        self._build_labels(min_df)

    def _parse(self):
        self._pmids = []
        self._titles = []
        self._abstracts = []
        self._mesh_list = []
        self._years = []

        with open(self.path, encoding="latin-1") as f:
            lines = f.readlines()

        i = 0
        n = len(lines)
        while i < n:
            if lines[i].startswith(".I "):
                pmid = lines[i][3:].strip()
                i += 1
                title, abstract, mesh = "", "", []
                year = None
                while i < n and not lines[i].startswith(".I "):
                    if lines[i] == ".M\n":
                        i += 1
                        raw = lines[i].strip().rstrip(".")
                        mesh = [t.split("/")[0].strip() for t in raw.split(";") if t.strip()]
                    elif lines[i] == ".T\n":
                        i += 1
                        title = lines[i].strip()
                    elif lines[i] == ".W\n":
                        i += 1
                        abstract = lines[i].strip()
                    elif lines[i].startswith(".S "):
                        src = lines[i][3:].strip()
                        m = re.search(r'(\d{4})', src)
                        if m:
                            year = int(m.group(1))
                    i += 1
                if title or abstract:
                    self._pmids.append(pmid)
                    self._titles.append(title)
                    self._abstracts.append(abstract)
                    self._mesh_list.append(mesh)
                    self._years.append(year if year else 0)

    def _build_labels(self, min_df):
        mlb = MultiLabelBinarizer()
        y = mlb.fit_transform(self._mesh_list)
        # filter rare labels
        freq = y.sum(axis=0)
        keep = np.where(freq >= min_df)[0]
        self._labels = y[:, keep]
        self._mlb = MultiLabelBinarizer()
        self._mlb.classes_ = np.array(mlb.classes_)[keep]

    def texts(self):
        return [f"{t} {a}" for t, a in zip(self._titles, self._abstracts)]

    def labels(self):
        return self._labels

    def pmids(self):
        return self._pmids

    def metadata(self):
        yr = np.array(self._years).reshape(-1, 1)
        return (yr - yr.mean()) / (yr.std() + 1e-8)

    @property
    def n_labels(self):
        return self._labels.shape[1]

    @property
    def task_type(self):
        return "multilabel"
