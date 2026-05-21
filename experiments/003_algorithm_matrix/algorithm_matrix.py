"""E1.2: 算法全矩阵 — TF-IDF/BioBERT × 7 models × 3 datasets."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))

from tqdm import tqdm
from _common import load_dataset, get_model, save_results, run_cv

OUT = HERE / "results"
DATASETS = {"ohsumed": {"min_df": 10, "max_samples": 5000},
            "pml": {}, "pgb": {"max_samples": 5000, "build_graph": False}}
FEATURES = ["tfidf", "biobert"]
MODELS = ["nb", "knn", "svm", "lr", "rf", "ada", "xgb"]
BIOBERT_ONLY = {"pml": {}}

if __name__ == "__main__":
    rows = []
    for ds_name, ds_kw in tqdm(DATASETS.items(), desc="E1.2 dataset", unit="ds"):
        ds = load_dataset(ds_name, **ds_kw)
        print(f"  {ds_name}: {len(ds)} docs, {ds.n_labels} labels")
        for feat in tqdm(FEATURES, desc=f"  {ds_name} feat", unit="feat", leave=False):
            if feat == "biobert" and ds_name not in BIOBERT_ONLY:
                continue
            for m in tqdm(MODELS, desc=f"    {ds_name}/{feat} model", unit="m", leave=False):
                try:
                    r = run_cv(ds, feat, get_model(m), cv=3)
                    rows.append(r)
                except Exception as e:
                    print(f"    {m} ERROR: {e}")
    save_results(rows, OUT / "algorithm_matrix.csv")
