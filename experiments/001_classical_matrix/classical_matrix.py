"""001 — Classical Algorithm Matrix: 7 models × 4 features × 3 datasets

Systematic comparison of classical/ensemble classifiers across
all text representations and datasets.

Usage:
    # Full run (all 84 combinations)
    python classical_matrix.py

    # Selective runs for quick iteration
    python classical_matrix.py --datasets pml --features tfidf --models lr,svm
    python classical_matrix.py --datasets ohsumed,pml --features tfidf,biobert
    python classical_matrix.py --models lr,rf,xgb

Grid:
    OHSUMED (10K, ~1.6K labels) × [tfidf, biobert, lda, meta] × 7 models
    PML     (10K, 16 labels)    × [tfidf, biobert, lda, meta] × 7 models
    PGB     (5K,  3 labels)     × [tfidf, biobert, lda, meta] × 7 models
    = 84 combinations

Caching:
    Features are cached in experiments/_cache/ and shared across experiments.
"""
from pathlib import Path
import sys, argparse
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))

from tqdm import tqdm
from _common import load_dataset, get_model, save_results, run_cv, model_label

OUT = HERE / "results"

# ── Default full grid ──
DATASETS = {
    "ohsumed": {"min_df": 10, "max_samples": 10000},
    "pml":     {},
    "pgb":     {"build_graph": False, "max_samples": 5000},
}
FEATURES = ["tfidf", "biobert", "lda", "meta"]
MODELS   = ["nb", "knn", "svm", "lr", "rf", "ada", "xgb"]
CV       = 5


def parse_args():
    p = argparse.ArgumentParser(description="001 — Classical Algorithm Matrix")
    p.add_argument("--datasets", type=str, default=None,
                   help="Comma-separated datasets (default: all). Options: ohsumed,pml,pgb")
    p.add_argument("--features", type=str, default=None,
                   help="Comma-separated features (default: all). Options: tfidf,biobert,lda,meta")
    p.add_argument("--models",   type=str, default=None,
                   help="Comma-separated models (default: all). Options: nb,knn,svm,lr,rf,ada,xgb")
    p.add_argument("--cv",       type=int, default=CV,
                   help=f"CV folds (default: {CV})")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Filter by CLI args
    ds_list = args.datasets.split(",") if args.datasets else list(DATASETS)
    ft_list = args.features.split(",") if args.features else FEATURES
    md_list = args.models.split(",")   if args.models   else MODELS

    # Validate
    for d in ds_list:
        if d not in DATASETS:
            raise ValueError(f"Unknown dataset: {d}. Options: {list(DATASETS)}")
    for f in ft_list:
        if f not in FEATURES:
            raise ValueError(f"Unknown feature: {f}. Options: {FEATURES}")
    for m in md_list:
        if m not in MODELS:
            raise ValueError(f"Unknown model: {m}. Options: {MODELS}")

    total = len(ds_list) * len(ft_list) * len(md_list)
    print(f"001 Classical Matrix: {len(ds_list)} datasets × {len(ft_list)} features × "
          f"{len(md_list)} models = {total} runs, CV={args.cv}")
    print(f"  datasets: {ds_list}")
    print(f"  features: {ft_list}")
    print(f"  models:   {md_list}")

    rows = []
    pbar = tqdm(total=total, desc="001", unit="run")

    for ds_name in ds_list:
        ds_kw = DATASETS[ds_name]
        ds = load_dataset(ds_name, **ds_kw)
        print(f"\n{'='*50}")
        print(f"  {ds_name}: {len(ds)} docs, {ds.n_labels} labels")
        print(f"{'='*50}")

        for feat in ft_list:
            print(f"\n  --- {feat} ---")
            for m in md_list:
                label = f"001 {ds_name}/{feat}/{m}"
                pbar.set_description(label[:40])
                try:
                    r = run_cv(ds, feat, get_model(m), cv=args.cv, ds_kwargs=ds_kw)
                    r["model"] = model_label(m)
                    rows.append(r)
                    print(f"  {m:5s}  f1_macro={r.get('f1_macro','?'):.4f}  "
                          f"time={r['train_time_s']:.1f}s")
                except Exception as e:
                    print(f"  {m:5s}  ERROR: {e}")
                pbar.update(1)

    pbar.close()
    save_results(rows, OUT / "classical_matrix.csv")
    print(f"\n✅ 001 done — {len(rows)} results")
