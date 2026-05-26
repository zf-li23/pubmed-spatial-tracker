"""E1.2 — Algorithm Matrix: 7 models × TF-IDF/BioBERT/LDA × 3 datasets

设计思路：
  系统比较 7 种经典/集成算法在所有数据集和特征表示上的分类性能。

运行矩阵：
  OHSUMED (10K) × [NB, kNN, SVM, LR, RF, Ada, XGB] × TF-IDF / BioBERT / LDA
  PML     (10K) × [NB, kNN, SVM, LR, RF, Ada, XGB] × TF-IDF / BioBERT / LDA
  PGB     (5K)  × [NB, kNN, SVM, LR, RF, Ada, XGB] × TF-IDF / BioBERT / LDA

总计: 3 × 7 × 3 = 63 组

预计耗时（首次运行）：
  TF-IDF 提取: < 1 分钟
  LDA 提取:    < 1 分钟
  BioBERT 提取: ~15 分钟
  CV 拟合:      ~10 分钟（63 组 × 5 折，特征已缓存）
  有缓存后:     < 5 分钟
"""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parent.parent))

from tqdm import tqdm
from _common import load_dataset, get_model, save_results, run_cv, model_label

OUT = HERE / "results"

DATASETS = {
    "ohsumed": {"min_df": 10, "max_samples": 10000},
    "pml":     {},
    "pgb":     {"build_graph": False, "max_samples": 5000},
}

FEATURES = ["tfidf", "biobert", "lda"]
MODELS = ["nb", "knn", "svm", "lr", "rf", "ada", "xgb"]
CV = 5


if __name__ == "__main__":
    rows = []
    total = len(DATASETS) * len(FEATURES) * len(MODELS)
    pbar = tqdm(total=total, desc="E1.2", unit="run")

    for ds_name, ds_kw in DATASETS.items():
        ds = load_dataset(ds_name, **ds_kw)
        print(f"\n{'='*50}")
        print(f"  Dataset: {ds_name}  |  {len(ds)} docs  |  {ds.n_labels} labels")
        print(f"{'='*50}")

        for feat in FEATURES:
            print(f"\n  --- {feat} ---")
            for m in MODELS:
                pbar.set_description(f"E1.2 {ds_name}/{feat}/{m}")
                try:
                    r = run_cv(ds, feat, get_model(m), cv=CV, ds_kwargs=ds_kw)
                    r["model"] = model_label(m)
                    rows.append(r)
                    print(f"  {m:5s}  f1_macro={r.get('f1_macro','?'):.4f}  "
                          f"time={r['train_time_s']:.1f}s")
                except Exception as e:
                    print(f"  {m:5s}  ERROR: {e}")
                pbar.update(1)

    pbar.close()
    save_results(rows, OUT / "algorithm_matrix.csv")
    print(f"\n✅ E1.2 done — {len(rows)} results")
