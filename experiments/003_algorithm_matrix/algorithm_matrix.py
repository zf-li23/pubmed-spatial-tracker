"""E1.2: 算法全矩阵 — 固定 BioBERT，对所有算法排序.

Datasets: ohsumed (5K — BioBERT 太慢), pml, pgb (5K)
Models:   nb, knn, svm, lr, rf, ada, xgb
Feature:  tfidf (BioBERT 太慢，先用 TF-IDF，后续独立跑 BioBERT)
"""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))                 # experiments/
sys.path.insert(0, str(HERE.parent.parent))          # repo root

from _common import load_dataset, get_model, save_results, run_cv

OUT = HERE / "results"

DATASETS = {
    "ohsumed": {"min_df": 10, "max_samples": 5000},
    "pml":     {},
    "pgb":     {"max_samples": 5000, "build_graph": False},
}
FEATURES = ["tfidf", "biobert"]
MODELS = ["nb", "knn", "svm", "lr", "rf", "ada", "xgb"]

# ── BioBERT 只在最小数据集（pml 约 10K）上跑 ──
BIOBERT_DATASETS = {"pml": {}}

if __name__ == "__main__":
    rows = []
    for ds_name, ds_kw in DATASETS.items():
        print(f"\n{'='*50}")
        print(f"Loading {ds_name}...")
        ds = load_dataset(ds_name, **ds_kw)
        print(f"  {len(ds)} docs, {ds.n_labels} labels")

        for feat in FEATURES:
            if feat == "biobert" and ds_name not in BIOBERT_DATASETS:
                print(f"  skip biobert on {ds_name} (too large)")
                continue
            for m in MODELS:
                if feat == "lda" and m in ("svm", "rf", "xgb", "ada"):
                    continue
                print(f"  --- {feat} / {m} ---")
                try:
                    r = run_cv(ds, feat, get_model(m), cv=3)
                    rows.append(r)
                    print(f"  f1_macro={r['f1_macro']:.4f}  time={r['train_time_s']}s")
                except Exception as e:
                    print(f"  ERROR: {e}")

    save_results(rows, OUT / "algorithm_matrix.csv")

    # Ranking
    print("\n" + "=" * 50)
    print("Ranking by macro_f1 (tfidf):")
    tfidf_rows = [r for r in rows if r["feature"] == "tfidf"]
    tfidf_rows.sort(key=lambda r: r["f1_macro"], reverse=True)
    print(f"{'dataset':<12} {'model':<6} {'f1_macro':<10} {'time_s':<8}")
    print("-" * 40)
    for r in tfidf_rows:
        print(f"{r['dataset']:<12} {r['model']:<6} {r['f1_macro']:<10.4f} {r['train_time_s']:<8.2f}")
