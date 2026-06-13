# 006 — ST Benchmark (Spatial Tracker Baseline)

3 methods on the Spatial Tracker dataset (9,148 articles, 6 LLM-annotated categories):

| Method | F1-macro | Accuracy | Time |
|---|---|---|---|
| TF-IDF + SVM | 0.6365 ± 0.0123 | 0.9167 ± 0.0011 | 913s |
| BioBERT + LR | 0.8068 ± 0.0320 | 0.9298 ± 0.0035 | **138s** |
| **BioBERT + MLP** | **0.8444 ± 0.0353** | **0.9380 ± 0.0124** | 1039s |

## Files

| File | Purpose |
|---|---|
| `st_benchmark.py` | Experiment script |
| `merge_results.py` | Merge CPU/GPU result CSV files |
| `run.sh` | Local quick test (TF-IDF+SVM only) |
| `run_exp.slurm` | Slurm cluster submission |
| `results/st_benchmark.csv` | Combined results |

## Key Finding

BioBERT+LR is the best cost-performance choice: F1=0.8068 (only 4.7% below MLP) but 7.5× faster (138s vs 1039s).
