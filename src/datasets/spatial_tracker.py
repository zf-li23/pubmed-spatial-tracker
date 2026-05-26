"""Spatial Tracker dataset loader (LLM-annotated)."""

import csv
import numpy as np
from pathlib import Path
from sklearn.preprocessing import MultiLabelBinarizer
from .base import BiomedDataset


class STLoader(BiomedDataset):
    """Load annotated_articles.csv with LLM labels and metadata.

    Labels: category (single-label, 6 classes).
    """

    def __init__(self, csv_path: str = None, max_samples: int = None):
        super().__init__("spatial_tracker")
        if csv_path is None:
            repo = Path(__file__).resolve().parent.parent.parent
            csv_path = repo / "data" / "spatial_tracker" / "annotated_articles.csv"
        self.path = Path(csv_path)
        self.max_samples = max_samples
        self._pmids, self._titles, self._abstracts = [], [], []
        self._dois, self._journals, self._pub_years = [], [], []
        self._categories, self._tags, self._technologies = [], [], []
        self._bio_topics, self._has_data, self._has_code = [], [], []
        self._confidences = []
        self._load()
        self._build_labels()

    def _load(self):
        with open(self.path, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if self.max_samples and len(self._pmids) >= self.max_samples:
                    break
                self._pmids.append(row["pmid"].strip())
                self._titles.append(row["title"].strip())
                self._dois.append(row.get("doi", "").strip())
                self._pub_years.append(int(row.get("pub_year", 0) or 0))
                self._journals.append(row.get("journal", "").strip())
                self._categories.append(row.get("category", "").strip())
                self._tags.append([t.strip() for t in row.get("tags", "").split(";") if t.strip()])
                self._technologies.append([t.strip() for t in row.get("technology", "").split(";") if t.strip()])
                self._bio_topics.append(row.get("biological_topic", "").strip())
                self._has_data.append(row.get("has_new_data", "").strip().lower() == "true")
                self._has_code.append(row.get("has_code", "").strip().lower() == "true")
                self._confidences.append(row.get("confidence", "medium").strip())

        # Also load abstracts from articles.csv
        articles_csv = self.path.parent / "articles.csv"
        if articles_csv.exists():
            abstract_map = {}
            with open(articles_csv, encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    abstract_map[row["pmid"].strip()] = row.get("abstract", "").strip()
            self._abstracts = [abstract_map.get(p, "") for p in self._pmids]
        else:
            self._abstracts = [""] * len(self._pmids)

    def _build_labels(self):
        self._label_names = sorted(set(self._categories) - {""})
        self._labels = np.zeros((len(self._pmids), len(self._label_names)), dtype=np.float32)
        for i, cat in enumerate(self._categories):
            if cat in self._label_names:
                self._labels[i, self._label_names.index(cat)] = 1.0

    def texts(self):
        return [f"{t} {a}" for t, a in zip(self._titles, self._abstracts)]

    def labels(self):
        return self._labels

    def pmids(self):
        return self._pmids

    def metadata(self):
        """Meta features: [year_norm, has_new_data, has_code, n_tags_norm, n_tech_norm]."""
        yr = np.array(self._pub_years, dtype=np.float64).reshape(-1, 1)
        yr = (yr - yr.mean()) / (yr.std() + 1e-8)
        has_data = np.array(self._has_data, dtype=np.float64).reshape(-1, 1)
        has_code = np.array(self._has_code, dtype=np.float64).reshape(-1, 1)
        n_tags = np.array([len(t) for t in self._tags], dtype=np.float64).reshape(-1, 1)
        n_tags = (n_tags - n_tags.mean()) / (n_tags.std() + 1e-8)
        n_tech = np.array([len(t) for t in self._technologies], dtype=np.float64).reshape(-1, 1)
        n_tech = (n_tech - n_tech.mean()) / (n_tech.std() + 1e-8)
        return np.hstack([yr, has_data, has_code, n_tags, n_tech])

    @property
    def n_labels(self):
        return len(self._label_names)

    @property
    def task_type(self):
        return "multilabel"

    @property
    def label_names(self):
        return self._label_names
