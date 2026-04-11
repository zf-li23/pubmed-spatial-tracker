import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC
from sqlalchemy import create_engine

from ml_pipeline import augment_text, get_embedding_model


def _to_set(tag_str):
    if pd.isna(tag_str) or not str(tag_str).strip():
        return set()
    return {t.strip() for t in str(tag_str).split(";") if t.strip()}


def _mean_jaccard(true_sets, pred_sets):
    scores = []
    for t_set, p_set in zip(true_sets, pred_sets):
        union = t_set | p_set
        if not union:
            scores.append(1.0)
        else:
            scores.append(len(t_set & p_set) / len(union))
    return float(np.mean(scores)) if scores else 0.0


def _metrics_row(y_true, y_pred, true_sets, pred_sets):
    exact_match = float(np.mean([t == p for t, p in zip(true_sets, pred_sets)])) if true_sets else 0.0
    return {
        "category_accuracy": float(accuracy_score(y_true, y_pred)) if len(y_true) else 0.0,
        "category_macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)) if len(y_true) else 0.0,
        "tags_exact_match_accuracy": exact_match,
        "tags_mean_jaccard": _mean_jaccard(true_sets, pred_sets),
    }


db_path = "/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/spatial_literature.db"
engine = create_engine(f"sqlite:///{db_path}")
df = pd.read_sql("SELECT * FROM literature", engine)

confirmed_df = df[pd.to_numeric(df["is_manually_confirmed"], errors="coerce").fillna(0).astype(int) == 1].copy()
report_rows = []

# 1) Current-global and per-category performance based on existing auto predictions.
eval_df = confirmed_df[
    confirmed_df["category"].astype(str).str.strip().ne("")
    & confirmed_df["auto_predicted_category"].astype(str).str.strip().ne("")
].copy()

if eval_df.empty:
    report_rows.append(
        {
            "report_type": "global_current_predictions",
            "scope": "all_confirmed",
            "category": "ALL",
            "sample_count": 0,
            "train_size": 0,
            "val_size": 0,
            "category_accuracy": 0.0,
            "category_macro_f1": 0.0,
            "tags_exact_match_accuracy": 0.0,
            "tags_mean_jaccard": 0.0,
            "delta_accuracy": "",
            "delta_macro_f1": "",
            "recommended_stop": "",
            "note": "No confirmed samples with non-empty auto predictions.",
        }
    )
else:
    y_true = eval_df["category"].astype(str)
    y_pred = eval_df["auto_predicted_category"].astype(str)
    true_sets = eval_df["tags"].apply(_to_set).tolist()
    pred_sets = eval_df["auto_predicted_tags"].apply(_to_set).tolist()
    m = _metrics_row(y_true, y_pred, true_sets, pred_sets)
    report_rows.append(
        {
            "report_type": "global_current_predictions",
            "scope": "all_confirmed",
            "category": "ALL",
            "sample_count": int(len(eval_df)),
            "train_size": 0,
            "val_size": int(len(eval_df)),
            "delta_accuracy": "",
            "delta_macro_f1": "",
            "recommended_stop": "",
            "note": "Current DB predictions on confirmed samples.",
            **m,
        }
    )

    for cat in sorted(eval_df["category"].dropna().astype(str).unique().tolist()):
        cat_df = eval_df[eval_df["category"].astype(str) == cat]
        cm = _metrics_row(
            cat_df["category"].astype(str),
            cat_df["auto_predicted_category"].astype(str),
            cat_df["tags"].apply(_to_set).tolist(),
            cat_df["auto_predicted_tags"].apply(_to_set).tolist(),
        )
        report_rows.append(
            {
                "report_type": "per_category_current_predictions",
                "scope": "all_confirmed",
                "category": cat,
                "sample_count": int(len(cat_df)),
                "train_size": 0,
                "val_size": int(len(cat_df)),
                "delta_accuracy": "",
                "delta_macro_f1": "",
                "recommended_stop": "",
                "note": "Current DB predictions split by true category.",
                **cm,
            }
        )

# 2) Learning curve simulation (increasing train size) for stop-training guidance.
sim_df = confirmed_df[confirmed_df["category"].astype(str).str.strip().ne("")].copy()
class_counts = sim_df["category"].astype(str).value_counts()
eligible_classes = class_counts[class_counts >= 2].index.tolist()
sim_df = sim_df[sim_df["category"].astype(str).isin(eligible_classes)].copy()

if len(sim_df) >= 40 and len(eligible_classes) >= 2:
    # Build embeddings once to keep reporting fast and stable.
    texts = [
        augment_text(t, a, py, j, m, k, nc, nt)
        for t, a, py, j, m, k, nc, nt in zip(
            sim_df["title"],
            sim_df["abstract"],
            sim_df["pub_year"],
            sim_df["journal"],
            sim_df.get("mesh_terms", [""] * len(sim_df)),
            sim_df.get("keywords", [""] * len(sim_df)),
            sim_df.get("naive_category", [""] * len(sim_df)),
            sim_df.get("naive_tags", [""] * len(sim_df)),
        )
    ]
    emb = get_embedding_model().encode(texts, batch_size=64, show_progress_bar=False)

    x_all = np.array(emb)
    y_all = sim_df["category"].astype(str).values

    train_pool, val_df = train_test_split(
        sim_df,
        test_size=0.2,
        random_state=42,
        stratify=sim_df["category"].astype(str),
    )

    train_idx, val_idx = train_test_split(
        np.arange(len(sim_df)),
        test_size=0.2,
        random_state=42,
        stratify=sim_df["category"].astype(str),
    )

    x_train_pool = x_all[train_idx]
    y_train_pool = y_all[train_idx]
    x_val = x_all[val_idx]
    y_val = y_all[val_idx]

    min_train = max(20, len(eligible_classes) * 5)
    max_train = len(train_idx)
    step = max(20, max_train // 5)
    train_sizes = sorted(set([min_train] + list(range(min_train, max_train + 1, step)) + [max_train]))

    prev_acc = None
    prev_f1 = None
    small_gain_streak = 0

    for n in train_sizes:
        if n < len(eligible_classes):
            continue

        rng = np.random.default_rng(42)
        sub_sel = rng.choice(np.arange(len(train_idx)), size=n, replace=False)
        x_sub = x_train_pool[sub_sel]
        y_sub = y_train_pool[sub_sel]

        clf = SVC(probability=True, class_weight="balanced", kernel="rbf", C=1.0)
        clf.fit(x_sub, y_sub)
        y_pred = clf.predict(x_val).tolist()

        y_true = y_val.tolist()
        true_sets = [set()] * len(y_true)
        pred_sets = [set()] * len(y_true)
        lm = _metrics_row(y_true, y_pred, true_sets, pred_sets)

        delta_acc = "" if prev_acc is None else float(lm["category_accuracy"] - prev_acc)
        delta_f1 = "" if prev_f1 is None else float(lm["category_macro_f1"] - prev_f1)

        recommended_stop = ""
        if prev_acc is not None:
            # If improvement is very small for two consecutive growth steps, signal a practical stop point.
            if abs(delta_acc) < 0.005 and abs(delta_f1) < 0.005:
                small_gain_streak += 1
            else:
                small_gain_streak = 0
            if small_gain_streak >= 2:
                recommended_stop = "YES"

        report_rows.append(
            {
                "report_type": "learning_curve_simulation",
                "scope": "confirmed_split_80_20",
                "category": "ALL",
                "sample_count": int(len(train_pool) + len(val_df)),
                "train_size": int(n),
                "val_size": int(len(val_df)),
                "tags_exact_match_accuracy": "",
                "tags_mean_jaccard": "",
                "delta_accuracy": delta_acc,
                "delta_macro_f1": delta_f1,
                "recommended_stop": recommended_stop,
                "note": "Learning curve via fixed-embedding SVC proxy on confirmed split (category only).",
                "category_accuracy": lm["category_accuracy"],
                "category_macro_f1": lm["category_macro_f1"],
            }
        )

        prev_acc = lm["category_accuracy"]
        prev_f1 = lm["category_macro_f1"]
else:
    report_rows.append(
        {
            "report_type": "learning_curve_simulation",
            "scope": "confirmed_split_80_20",
            "category": "ALL",
            "sample_count": int(len(sim_df)),
            "train_size": 0,
            "val_size": 0,
            "category_accuracy": 0.0,
            "category_macro_f1": 0.0,
            "tags_exact_match_accuracy": 0.0,
            "tags_mean_jaccard": 0.0,
            "delta_accuracy": "",
            "delta_macro_f1": "",
            "recommended_stop": "",
            "note": "Not enough class-balanced confirmed samples for learning-curve simulation.",
        }
    )

report_df = pd.DataFrame(report_rows)
report_file = "/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/ML_Performance_Report.csv"
report_df.to_csv(report_file, index=False)
print(f"Saved report to {report_file} with {len(report_df)} row(s).")
