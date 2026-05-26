# 001 — Classical Algorithm Matrix

7 models × 4 features × 3 datasets = **84 combinations**.

## Grid

| Dataset | Samples | Labels | Features | Models |
|---|---|---|---|---|
| OHSUMED | 10,000 | ~1,650 | tfidf, biobert, lda, meta | NB, kNN, SVM, LR, RF, AdaBoost, XGBoost |
| PML | 10,000 | 16 | tfidf, biobert, lda, meta | NB, kNN, SVM, LR, RF, AdaBoost, XGBoost |
| PGB | 5,000 | 3 | tfidf, biobert, lda, meta | NB, kNN, SVM, LR, RF, AdaBoost, XGBoost |

- CV: 5-fold
- Strategy: Binary Relevance (OneVsRestClassifier)

## Selective Runs

```bash
# Full grid
sbatch run_exp.slurm

# Quick subset
python classical_matrix.py --datasets pml --features tfidf --models lr,svm
python classical_matrix.py --datasets ohsumed,pml --features tfidf,biobert
python classical_matrix.py --models lr,rf,xgb
```

## Output

`results/classical_matrix.csv`
