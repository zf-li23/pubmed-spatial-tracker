# 005 — Graph Models (PGB)

Three graph-aware models on PGB's citation network.

## Grid

| Model | Features | Notes |
|---|---|---|
| Node2Vec+LR | Node2Vec 128d embeddings | Graph → Walks → SkipGram |
| GCN | TF-IDF + normalized adjacency | 2-layer, 200 epochs |
| GraphSAGE | TF-IDF + mean neighbor agg | 2-layer, 200 epochs |

- Dataset: PGB (5K nodes, ~N citation edges)
- CV: 5-fold
- **Requires GPU** for GCN/GraphSAGE

## Run

```bash
sbatch run_exp.slurm
```

## Output

`results/graph_models.csv`
