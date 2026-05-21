"""Spatial Tracker dataset loader."""

import numpy as np
from .base import BiomedDataset


class STLoader(BiomedDataset):
    """Placeholder until data is collected & annotated."""

    def __init__(self):
        super().__init__("spatial_tracker")
        self._ready = False

    def texts(self):
        raise NotImplementedError("Spatial Tracker data not yet collected.")

    def labels(self):
        raise NotImplementedError

    def pmids(self):
        raise NotImplementedError

    def metadata(self):
        return None

    @property
    def n_labels(self):
        return 0

    @property
    def task_type(self):
        return "multilabel"

    @property
    def is_ready(self):
        return self._ready
