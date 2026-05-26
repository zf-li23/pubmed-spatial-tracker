# 002 — BioBERT+MLP Fine-tuning

End-to-end BioBERT fine-tuning on **raw text**, no feature cache.

## Grid

| Dataset | Samples | Labels | Model |
|---|---|---|---|
| OHSUMED | 10,000 | ~1,650 | BioBERT+MLP |
| PML | 10,000 | 16 | BioBERT+MLP |
| PGB | 5,000 | 3 | BioBERT+MLP |

- CV: 3-fold (constrained by GPU time)
- Epochs: 3, batch_size: 16, lr: 2e-5
- **Requires GPU** (`--gres=gpu:1` in slurm)

## Run

```bash
sbatch run_exp.slurm
```

## Output

`results/biobert_mlp.csv`

## Notes

- This is the only model that fine-tunes BioBERT end-to-end
  (instead of using frozen embeddings).  Compare with 001's
  `biobert`+LR row to quantify the benefit of fine-tuning.
- Cluster fix (2026-05-26): Added `local_files_only=True` to
  `AutoModel.from_pretrained()` and `AutoTokenizer.from_pretrained()`
  in `src/models/deep.py` so BioBERT loads from HuggingFace cache
  without network access.
- `sentencepiece` is **not** required — BioBERT uses WordPiece tokenizer.
