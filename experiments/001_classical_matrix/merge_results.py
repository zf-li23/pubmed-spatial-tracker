"""Merge 001 parallel result CSV files into one clean file.

Handles different column schemas:
  - Multi-label (OHSUMED, PML): f1_macro, f1_micro, f1_samples (12 cols)
  - Single-label (PGB):          accuracy, f1_macro (10 cols)
"""
import csv, sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "results"
OUT = SRC / "classical_matrix.csv"

FIELDS = [
    "dataset", "feature", "model",
    "n_labels", "n_samples",
    "f1_macro", "f1_macro_std",
    "f1_micro", "f1_micro_std",
    "f1_samples", "f1_samples_std",
    "accuracy", "accuracy_std",
    "train_time_s",
]

rows = []
# Strategy: full file first (complete baseline), then overlay
# individual files (fresher data from re-runs, may have gaps).

# Step 1: process full merged file as baseline
full_path = SRC / "classical_matrix_full.csv"
if full_path.exists():
    with open(full_path) as fh:
        for line in fh:
            vals = [v.strip() for v in line.strip().split(",")]
            if len(vals) < 4:
                continue
            # Skip remaining header lines (contain "dataset" or "accuracy")
            if vals[0] in ("dataset", "accuracy", "f1_macro"):
                continue
            if len(vals) == 10:
                clean = {k: "" for k in FIELDS}
                clean["accuracy"] = vals[0]
                clean["accuracy_std"] = vals[1]
                clean["dataset"] = vals[2]
                clean["f1_macro"] = vals[3]
                clean["f1_macro_std"] = vals[4]
                clean["feature"] = vals[5]
                clean["model"] = vals[6]
                clean["n_labels"] = vals[7]
                clean["n_samples"] = vals[8]
                clean["train_time_s"] = vals[9]
                rows.append(clean)
            elif len(vals) == 12:
                # Multi-label rows in the full file (no header)
                clean = {k: "" for k in FIELDS}
                clean["dataset"] = vals[0]
                clean["f1_macro"] = vals[1]
                clean["f1_macro_std"] = vals[2]
                clean["f1_micro"] = vals[3]
                clean["f1_micro_std"] = vals[4]
                clean["f1_samples"] = vals[5]
                clean["f1_samples_std"] = vals[6]
                clean["feature"] = vals[7]
                clean["model"] = vals[8]
                clean["n_labels"] = vals[9]
                clean["n_samples"] = vals[10]
                clean["train_time_s"] = vals[11]
                rows.append(clean)

# Step 2: overlay individual result files (prefer these when complete)
for f in sorted(SRC.glob("classical_matrix_*.csv")):
    if "full" in f.name or f.name == "classical_matrix.csv":
        continue
    with open(f) as fh:
        lines = fh.readlines()
    # First line is header, skip it
    for line in lines[1:]:
        vals = [v.strip() for v in line.strip().split(",")]
        if len(vals) < 2:
            continue
        # Detect format by column count
        if len(vals) == 10:
            # PGB: accuracy,accuracy_std,dataset,f1_macro,f1_macro_std,...
            clean = {k: "" for k in FIELDS}
            clean["accuracy"] = vals[0]
            clean["accuracy_std"] = vals[1]
            clean["dataset"] = vals[2]
            clean["f1_macro"] = vals[3]
            clean["f1_macro_std"] = vals[4]
            clean["feature"] = vals[5]
            clean["model"] = vals[6]
            clean["n_labels"] = vals[7]
            clean["n_samples"] = vals[8]
            clean["train_time_s"] = vals[9]
            rows.append(clean)
        elif len(vals) == 12:
            # Multi-label: dataset,f1_macro,f1_macro_std,f1_micro,f1_micro_std,...
            clean = {k: "" for k in FIELDS}
            clean["dataset"] = vals[0]
            clean["f1_macro"] = vals[1]
            clean["f1_macro_std"] = vals[2]
            clean["f1_micro"] = vals[3]
            clean["f1_micro_std"] = vals[4]
            clean["f1_samples"] = vals[5]
            clean["f1_samples_std"] = vals[6]
            clean["feature"] = vals[7]
            clean["model"] = vals[8]
            clean["n_labels"] = vals[9]
            clean["n_samples"] = vals[10]
            clean["train_time_s"] = vals[11]
            rows.append(clean)

# Deduplicate by (dataset, feature, model)
seen = set()
deduped = []
for r in rows:
    key = (r["dataset"], r["feature"], r["model"])
    if key not in seen:
        seen.add(key)
        deduped.append(r)
rows = deduped

print(f"  (unique: {len(rows)}/{len(seen) + len(rows) - 1} from {len(rows) + 1} total)")

# Sort by (dataset, feature, model)
rows.sort(key=lambda r: (r["dataset"], r["feature"], r["model"]))

with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)

print(f"✅ Merged {len(rows)} rows → {OUT}")
