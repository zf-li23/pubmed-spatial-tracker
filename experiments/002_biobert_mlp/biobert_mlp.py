"""002 — BioBERT+MLP Fine-tuning: end-to-end deep model on raw text

End-to-end BioBERT fine-tuning with an MLP classification head.
Does NOT use the feature cache — BioBERT is fine-tuned jointly with the
classifier, not frozen for embedding extraction.

Grid:
    OHSUMED (10K) × BioBERT+MLP
    PML     (10K) × BioBERT+MLP
    PGB     (5K)  × BioBERT+MLP
    = 3 runs (but each takes GPU hours)

Requires GPU (slurm --gres=gpu:1).
"""
from pathlib import Path
import sys, time
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))

import numpy as np
from tqdm import tqdm
from _common import load_dataset, save_results

OUT = HERE / "results"

DATASETS = {
    "ohsumed": {"min_df": 10, "max_samples": 10000},
    "pml":     {},
    "pgb":     {"build_graph": False, "max_samples": 5000},
}

EPOCHS = 3
BATCH_SIZE = 16
LR = 2e-5
CV = 3  # fewer folds due to training cost


def run_biobert_mlp(ds, epochs=EPOCHS, batch_size=BATCH_SIZE, lr=LR, cv=CV):
    """Run BioBERT fine-tuning with manual CV."""
    from src.models.deep import BioBERTFineTuner
    from sklearn.model_selection import KFold
    from sklearn.metrics import f1_score, accuracy_score

    texts = ds.texts()
    y = ds.labels()
    if hasattr(y, "toarray"):
        y = y.toarray()

    # For PGB, use multi-class; others use multi-label
    is_ml = ds.task_type == "multilabel" and ds.name != "pgb"
    if ds.name == "pgb":
        y = y.argmax(axis=1)

    splits = list(KFold(cv, shuffle=True, random_state=42).split(texts))
    fold_scores = []
    t0 = time.time()

    for fold_i, (tr_idx, te_idx) in enumerate(
        tqdm(splits, desc="CV", unit="fold", leave=False), 1
    ):
        texts_tr = [texts[i] for i in tr_idx]
        texts_te = [texts[i] for i in te_idx]
        y_tr = y[tr_idx]
        y_te = y[te_idx]

        n_labels = y_tr.shape[1] if y_tr.ndim > 1 else len(np.unique(y_tr))
        tuner = BioBERTFineTuner(n_labels=n_labels, lr=lr,
                                 epochs=epochs, batch_size=batch_size,
                                 multilabel=is_ml)
        tuner.fit(texts_tr, y_tr)
        y_pred = tuner.predict(texts_te)

        if is_ml:
            fold_scores.append({
                "f1_macro": f1_score(y_te, y_pred, average="macro", zero_division=0),
                "f1_micro": f1_score(y_te, y_pred, average="micro", zero_division=0),
            })
        else:
            fold_scores.append({
                "f1_macro": f1_score(y_te, y_pred, average="macro", zero_division=0),
                "accuracy": accuracy_score(y_te, y_pred),
            })

    elapsed = time.time() - t0
    res = {
        "dataset": ds.name, "model": "BioBERT+MLP",
        "n_samples": len(ds), "n_labels": ds.n_labels,
        "train_time_s": round(elapsed, 2),
        "epochs": epochs, "batch_size": batch_size,
    }
    for metric in fold_scores[0]:
        vals = [fs[metric] for fs in fold_scores]
        res[metric] = round(np.mean(vals), 4)
        res[f"{metric}_std"] = round(np.std(vals), 4)
    return res


if __name__ == "__main__":
    rows = []
    for ds_name, ds_kw in tqdm(DATASETS.items(), desc="002", unit="ds"):
        ds = load_dataset(ds_name, **ds_kw)
        print(f"\n{'='*50}")
        print(f"  {ds_name}: {len(ds)} docs, {ds.n_labels} labels")
        print(f"{'='*50}")

        try:
            r = run_biobert_mlp(ds)
            rows.append(r)
            print(f"  f1_macro={r.get('f1_macro','?'):.4f}  time={r['train_time_s']:.1f}s")
        except Exception as e:
            print(f"  ERROR: {e}")
            import traceback; traceback.print_exc()

    save_results(rows, OUT / "biobert_mlp.csv", key_fields=["dataset", "model"])
    print(f"\n✅ 002 done — {len(rows)} results")
