#!/usr/bin/env python3
"""Merge 006 result files into one."""
import csv
from pathlib import Path

SRC = Path(__file__).resolve().parent / "results"
OUT = SRC / "st_benchmark.csv"

# CSV columns from save_results() are sorted(all_keys) → alphabetical order
FIELDS = ["accuracy", "accuracy_std", "dataset", "f1_macro",
          "f1_macro_std", "method", "n_labels", "n_samples", "train_time_s"]

rows = []
for f in sorted(SRC.glob("st_benchmark_*.csv")):
    with open(f) as fh:
        for line in fh:
            vals = [v.strip() for v in line.strip().split(",")]
            if vals[0] in ("dataset", "accuracy"):
                continue
            if len(vals) == 9:
                clean = dict(zip(FIELDS, vals))
                rows.append(clean)

rows.sort(key=lambda r: r["method"])
with open(OUT, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=FIELDS)
    w.writeheader()
    w.writerows(rows)
print(f"✅ Merged {len(rows)} rows → {OUT}")
