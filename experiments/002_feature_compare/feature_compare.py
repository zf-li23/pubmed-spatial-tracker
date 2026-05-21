"""E1.1: 特征对比 — 固定 SVM，比较 TF-IDF / BioBERT / LDA."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))

from tqdm import tqdm
from _common import load_dataset, get_model, save_results, run_cv

OUT = HERE / "results"
DATASETS = {"ohsumed": {"min_df": 10, "max_samples": 20000},
            "pml": {}, "pgb": {"max_samples": 20000, "build_graph": False}}
FEATURES = ["tfidf", "biobert", "lda"]
MODEL = "svm"

if __name__ == "__main__":
    rows = []
    for ds_name, ds_kw in tqdm(DATASETS.items(), desc="E1.1 dataset", unit="ds"):
        ds = load_dataset(ds_name, **ds_kw)
        print(f"  {ds_name}: {len(ds)} docs, {ds.n_labels} labels")
        for feat in tqdm(FEATURES, desc=f"  {ds_name} feat", unit="feat", leave=False):
            if feat == "lda" and ds_name == "pgb":
                continue
            try:
                r = run_cv(ds, feat, get_model(MODEL))
                rows.append(r)
                print(f"    {feat:8s} f1={r['f1_macro']:.4f}  {r['train_time_s']}s")
            except Exception as e:
                print(f"    {feat:8s} ERROR: {e}")
    save_results(rows, OUT / "feature_compare.csv")
