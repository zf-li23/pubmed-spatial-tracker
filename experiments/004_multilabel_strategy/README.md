# 004 — Multi-label Strategy

Compare BR / CC / LP strategies on multi-label datasets.

PGB is excluded: it is treated as 3-class single-label (argmax).

## Grid

| Dataset | Samples | Labels | Strategies |
|---|---|---|---|
| OHSUMED | 10,000 | ~1,650 | BR, CC, LP |
| PML | 10,000 | 16 | BR, CC, LP |

- Feature: TF-IDF (cached)
- Model: LogisticRegression (fresh per fold, no nested parallelism)
- CV: 5-fold

## Changes (2026-05-26)

Fixed **ClassifierChain deadlock** on PML: `copy.deepcopy` of
`LogisticRegression(n_jobs=-1)` inside `Parallel(n_jobs=-1)` caused
nested-parallelism deadlock with loky backend, causing CC on PML to
fail silently.  Fix: create fresh `LogisticRegression(max_iter=1000)`
per fold instead.

## Run

```bash
sbatch run_exp.slurm
```

## Output

`results/multilabel_strategy.csv` — 6 rows expected
