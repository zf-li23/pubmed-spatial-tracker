"""Experiment result logging & summary."""

import csv
import time
from pathlib import Path
from datetime import datetime


class ExpLogger:
    """Logs each experiment run to CSV."""

    def __init__(self, path: str = "src/results/log.csv"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._writer = None

    def log(self, **kwargs):
        row = {**kwargs, "timestamp": datetime.now().isoformat()}
        if not self._writer:
            self._file = open(self.path, "a", newline="")
            self._writer = csv.DictWriter(self._file, fieldnames=list(row.keys()))
            if self.path.stat().st_size == 0:
                self._writer.writeheader()
        self._writer.writerow(row)
        self._file.flush()

    def close(self):
        if self._file:
            self._file.close()
