# 003 — LDA + Clustering

Unsupervised topic discovery via LDA+KMeans, evaluated with NMI/ARI.

## Grid

| Dataset | Samples | Labels | Method |
|---|---|---|---|
| OHSUMED | 10,000 | ~1,650 | LDA+KMeans |
| PML | 10,000 | 16 | LDA+KMeans |
| PGB | 5,000 | 3 | LDA+KMeans |

- K = ground-truth label count
- Uses LDA features from cache

## Run

```bash
sbatch run_exp.slurm
```

## Output

`results/lda_cluster.csv` — NMI, ARI per dataset
