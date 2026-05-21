"""E1.1: 特征对比 — 固定 SVM，比较 TF-IDF / BioBERT / LDA.

Datasets: ohsumed (20K), pml (10K), pgb (20K)
Model:    SVM (RBF)
Metric:   macro F1, training time
"""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))                 # experiments/
sys.path.insert(0, str(HERE.parent.parent))          # repo root

from _common import load_dataset, get_model, save_results, run_cv

OUT = HERE / "results"

DATASETS = {
    "ohsumed": {"min_df": 10, "max_samples": 20000},
    "pml":     {},  # 全部约 10K
    "pgb":     {"max_samples": 20000, "build_graph": False},
}
FEATURES = ["tfidf", "biobert", "lda"]
MODEL = "svm"  # 固定 SVM

if __name__ == "__main__":
    rows = []
    for ds_name, ds_kw in DATASETS.items():
        print(f"\n{'='*50}")
        print(f"Loading {ds_name}...")
        ds = load_dataset(ds_name, **ds_kw)
        print(f"  {len(ds)} docs, {ds.n_labels} labels")

        for feat in FEATURES:
            if feat == "lda" and ds_name == "pgb":
                continue  # LDA 不适合 PGB 的短文本 + 高标签空间
            print(f"  --- feat={feat} ---")
            try:
                r = run_cv(ds, feat, get_model(MODEL))
                rows.append(r)
                print(f"  macro_f1={r['f1_macro']:.4f}  time={r['train_time_s']}s")
            except Exception as e:
                print(f"  ERROR: {e}")

    save_results(rows, OUT / "feature_compare.csv")

    # Summary table
    print("\n" + "=" * 50)
    print("Summary: macro_f1")
    print(f"{'dataset':<12} {'feature':<10} {'f1_macro':<10} {'time_s':<8}")
    print("-" * 40)
    for r in rows:
        print(f"{r['dataset']:<12} {r['feature']:<10} {r['f1_macro']:<10.4f} {r['train_time_s']:<8.2f}")
