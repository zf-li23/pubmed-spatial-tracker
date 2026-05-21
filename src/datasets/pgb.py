"""PGB dataset loader (JSONL, diabetes subset)."""

import json
import numpy as np
from pathlib import Path
from typing import List, Optional, Tuple
from sklearn.preprocessing import LabelEncoder
from .base import BiomedDataset


class PGBLoader(BiomedDataset):
    """Load PGB's diabetes subset for node classification (3 classes)."""

    def __init__(self, data_dir: str, max_samples: int = 50000, build_graph: bool = False):
        super().__init__("pgb")
        self.data_dir = Path(data_dir)
        self.build_graph = build_graph
        self._load_data(max_samples)
        self._assign_diabetes_labels()

    def _load_data(self, max_samples):
        self._pmids, self._titles, self._abstracts = [], [], []
        self._mesh_terms, self._years, self._venues = [], [], []
        self._citations = []  # list of (from_idx, to_idx)
        self._idx_map = {}

        count = 0
        for f in sorted(self.data_dir.glob("pgb_*.jsonl")):
            if count >= max_samples:
                break
            with open(f) as fh:
                for line in fh:
                    if count >= max_samples:
                        break
                    d = json.loads(line)
                    pmid = d.get("pmid")
                    title = d.get("title", "") or ""
                    abstract = d.get("abstract", "") or ""
                    if not title and not abstract:
                        continue
                    idx = len(self._pmids)
                    self._idx_map[pmid] = idx
                    self._pmids.append(pmid)
                    self._titles.append(title)
                    self._abstracts.append(abstract)
                    self._mesh_terms.append([m["term"] for m in d.get("mesh", [])])
                    self._years.append(d.get("year", 0))
                    self._venues.append(d.get("venue", "") or "")
                    count += 1

        # build citation graph
        if self.build_graph:
            self._citations = []
            for f in sorted(self.data_dir.glob("pgb_*.jsonl")):
                with open(f) as fh:
                    for line in fh:
                        d = json.loads(line)
                        pmid = d.get("pmid")
                        if pmid not in self._idx_map:
                            continue
                        src = self._idx_map[pmid]
                        for cit in d.get("outbound_citations", []):
                            if cit in self._idx_map:
                                self._citations.append((src, self._idx_map[cit]))

    def _assign_diabetes_labels(self):
        """Heuristic: assign diabetes type labels based on MeSH terms."""
        self._labels = np.zeros((len(self._pmids), 3), dtype=np.float32)
        type1_kw = {"diabetes mellitus, type 1", "type 1 diabetes", "insulin-dependent"}
        type2_kw = {"diabetes mellitus, type 2", "type 2 diabetes", "non-insulin-dependent"}
        exp_kw = {"diabetes mellitus, experimental", "experimental diabetes"}

        for i, mesh in enumerate(self._mesh_terms):
            ms = set(t.lower() for t in mesh)
            if exp_kw & ms:
                self._labels[i, 0] = 1
            if type1_kw & ms:
                self._labels[i, 1] = 1
            if type2_kw & ms:
                self._labels[i, 2] = 1

    def texts(self):
        return [f"{t} {a}" for t, a in zip(self._titles, self._abstracts)]

    def labels(self):
        return self._labels

    def pmids(self):
        return self._pmids

    def metadata(self):
        yr = np.array(self._years).reshape(-1, 1)
        yr = (yr - yr.mean()) / (yr.std() + 1e-8)
        return yr

    @property
    def n_labels(self):
        return self._labels.shape[1]

    @property
    def task_type(self):
        return "multilabel"

    def get_graph(self):
        """Return adjacency list for nodes present in the subset."""
        if not self.build_graph:
            return None
        n = len(self._pmids)
        adj = [[] for _ in range(n)]
        for s, t in self._citations:
            if s < n and t < n:
                adj[s].append(t)
                adj[t].append(s)
        return adj
