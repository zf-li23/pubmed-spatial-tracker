"""E1.1 — Feature Comparison: TF-IDF / BioBERT / LDA（固定 LR，全部数据集）

设计思路：
  固定模型为 Logistic Regression，单独对比不同文本表示方法的效果。
  这是后续算法矩阵实验的前置分析——先确认哪种特征最好。

运行矩阵：
  OHSUMED (10K) × TF-IDF / BioBERT / LDA
  PML     (10K) × TF-IDF / BioBERT / LDA
  PGB     (5K)  × TF-IDF / BioBERT

预计耗时（本地，首次运行）：
  TF-IDF+LDA: < 2 分钟
  BioBERT:    ~15 分钟（首次提取嵌入，之后走缓存）
  有缓存后:   < 1 分钟
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
MODEL = "lr"
CV = 5


if __name__ == "__main__":
    rows = []
    total = len(DATASETS) * len(FEATURES) - 1  # LDA skipped on PGB
    pbar = tqdm(total=total, desc="E1.1", unit="run")

    for ds_name, ds_kw in DATASETS.items():
        ds = load_dataset(ds_name, **ds_kw)
        print(f"\n{'='*50}")
        print(f"  Dataset: {ds_name}  |  {len(ds)} docs  |  {ds.n_labels} labels")
        print(f"{'='*50}")

        for feat in FEATURES:
            if feat == "lda" and ds_name == "pgb":
                continue

            pbar.set_description(f"E1.1 {ds_name}/{feat}/{MODEL}")
            try:
                r = run_cv(ds, feat, get_model(MODEL), cv=CV, ds_kwargs=ds_kw)
                r["model"] = model_label(MODEL)
                rows.append(r)
                print(f"  {feat:8s}  f1_macro={r.get('f1_macro','?'):.4f}  "
                      f"time={r['train_time_s']:.1f}s")
            except Exception as e:
                print(f"  {feat:8s}  ERROR: {e}")
                import traceback; traceback.print_exc()
            pbar.update(1)

    pbar.close()
    save_results(rows, OUT / "feature_compare.csv")
    print(f"\n✅ E1.1 done — {len(rows)} results")
