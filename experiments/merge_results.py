"""Merge per-feature classical_matrix CSVs into a single unified file.

Run after all cluster Exp 001 jobs complete:
    conda activate pubmed-tracker
    cd experiments/001_classical_matrix/results
    python ../../merge_results.py

Handles different column schemas:
  - OHSUMED/PML: 15 cols (f1_macro, f1_micro, f1_samples + _std + _folds)
  - PGB:         12 cols (f1_macro, accuracy + _std + _folds)
"""

import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
RESULTS = HERE / "001_classical_matrix" / "results"

files = sorted(RESULTS.glob("classical_matrix_*.csv"))
all_cols = set()
rows = []

for f in files:
    with open(f) as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            all_cols.update(row.keys())
            rows.append(row)

priority = [
    "dataset", "feature", "model", "n_labels", "n_samples",
    "f1_macro", "f1_macro_std", "f1_macro_folds",
    "f1_micro", "f1_micro_std", "f1_micro_folds",
    "f1_samples", "f1_samples_std", "f1_samples_folds",
    "accuracy", "accuracy_std", "accuracy_folds",
    "train_time_s",
]
ordered = priority + sorted(k for k in all_cols if k not in priority)

with open(RESULTS / "classical_matrix.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=ordered, extrasaction="ignore")
    w.writeheader()
    w.writerows(rows)

print(f"Merged {len(rows)} rows from {len(files)} files ({len(ordered)} columns)")
