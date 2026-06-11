#!/usr/bin/env python3
"""Merge individual per-(dataset,feature) CSVs into a single CSV with _folds columns."""
import csv
from pathlib import Path
from collections import OrderedDict

RESULTS = Path(__file__).resolve().parent / "results"
OUT = RESULTS / "classical_matrix_with_folds.csv"

# Collect all rows + union of all fieldnames
all_rows = []
all_fieldnames = set()
for fpath in sorted(RESULTS.glob("classical_matrix_*.csv")):
    with open(fpath) as f:
        reader = csv.DictReader(f)
        all_fieldnames.update(reader.fieldnames)
        for row in reader:
            all_rows.append(row)

if not all_rows:
    print("No individual CSV rows found!")
    exit(1)

# Also load original merged CSV to fill in rows missing _folds data
ORIG = RESULTS / "classical_matrix.csv"
orig_rows = {}
if ORIG.exists():
    with open(ORIG) as f:
        for r in csv.DictReader(f):
            key = (r["dataset"], r["feature"], r["model"])
            orig_rows[key] = r

# Preserve a canonical column order
base_cols = ["dataset","feature","model","n_labels","n_samples"]
metric_cols = sorted(c for c in all_fieldnames if c not in set(base_cols))
fieldnames = base_cols + metric_cols

# Deduplicate: keep last occurrence per (dataset, feature, model)
seen = {}
for row in all_rows:
    key = (row["dataset"], row["feature"], row["model"])
    seen[key] = row  # last wins

# Fill in any combos that only exist in original (no _folds data available)
missing_from_orig = 0
for key, row in orig_rows.items():
    if key not in seen:
        # Add with _folds columns as blank
        for col in [c for c in fieldnames if c.endswith("_folds")]:
            row[col] = ""
        seen[key] = row
        missing_from_orig += 1

deduped = [seen[k] for k in seen]

with open(OUT, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(deduped)

print(f"Merged {len(deduped)} rows (from {len(all_rows)} raw + {missing_from_orig} from original) → {OUT}")
print(f"Columns ({len(fieldnames)}): {', '.join(fieldnames)}")
print(f"Rows with _folds: {sum(1 for r in deduped if r.get('f1_macro_folds','').strip())} / {len(deduped)}")

print(f"Merged {len(deduped)} rows (from {len(all_rows)} raw) → {OUT}")
print(f"Columns ({len(fieldnames)}): {', '.join(fieldnames)}")
