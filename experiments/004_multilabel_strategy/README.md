# 004 — Multi-label Strategy

Compare BR / CC / LP strategies on multi-label datasets.

PGB is excluded: it is treated as 3-class single-label (argmax).

## Grid

| Dataset | Samples | Labels | Strategies |
|---|---|---|---|
| OHSUMED | 10,000 | ~1,650 | BR, CC, LP |
| PML | 10,000 | 16 | BR, CC, LP |

- Feature: TF-IDF (cached)
- Model: LogisticRegression
- CV: 5-fold

## Run

```bash
sbatch run_exp.slurm
```

## Output

`results/multilabel_strategy.csv`
