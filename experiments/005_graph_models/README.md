# 005 — Graph Models (PGB)

Nine runs on PGB's citation network: Node2Vec × 7 classical models + GCN + GraphSAGE.

## Grid

| # | Model | Features | Notes |
|---|---|---|---|
| 1‑7 | Node2Vec+NB/kNN/SVM/LR/RF/Ada/XGB | Node2Vec 128d embeddings | Graph → Walks → SkipGram (gensim fallback) |
| 8 | GCN | TF-IDF + normalized adjacency | 2-layer GCN, 200 epochs |
| 9 | GraphSAGE | TF-IDF + mean neighbor agg | 2-layer GraphSAGE, 200 epochs |

- Dataset: PGB (5K nodes)
- CV: 5-fold (Node2Vec), CV: 5-fold fixed split (GCN/GraphSAGE)
- Node2Vec runs on **CPU**; GCN/GraphSAGE **require GPU** (`--gres=gpu:1`)
- Node2Vec features auto-cached on first run

## Run

```bash
sbatch run_exp.slurm
```

## Output

`results/graph_models.csv` — 9 rows
```

## Output

`results/graph_models.csv`
