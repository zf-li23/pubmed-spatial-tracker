import sys
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
import os

db_path = "/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/spatial_literature.xlsx"
df = pd.read_excel(db_path)

# Only strictly Batch 1
b1_df = df[(df["is_manually_confirmed"] == True) & (df["annotation_batch"] == 1)]

if b1_df.empty:
    print("No Batch 1 data found.")
    sys.exit(1)

print(f"=== 表现评估 (严格限定你完整校验过的 BATCH 1) ===")
cat_acc = 0.0
if "auto_predicted_category" in b1_df.columns and not b1_df["auto_predicted_category"].isna().all():
    y_true_cat = b1_df["category"].astype(str)
    # the predictions for batch 1 prior to you labeling it 
    y_pred_cat = b1_df["auto_predicted_category"].astype(str)
    
    # We filter out cases where auto_predicted is NaN. For Batch 1, they probably didn't have predictions (or maybe they did). If there's no auto_predicted_category, we can't eval.
    valid_eval = y_true_cat[y_pred_cat != "nan"]
    valid_pred = y_pred_cat[y_pred_cat != "nan"]
    if len(valid_eval) > 0:
        cat_acc = accuracy_score(valid_eval, valid_pred)
        print(f"大类(Category)预测准确率: {cat_acc:.2%}")
        print(classification_report(valid_eval, valid_pred, zero_division=0))

tags_acc = 0.0
if "auto_predicted_tags" in b1_df.columns and not b1_df["auto_predicted_tags"].isna().all():
    y_true_tags = b1_df["tags"].fillna("").astype(str)
    y_pred_tags = b1_df["auto_predicted_tags"].fillna("").astype(str)
    
    valid_t_eval = y_true_tags[y_pred_tags != "nan"]
    valid_t_pred = y_pred_tags[y_pred_tags != "nan"]
    if len(valid_t_eval) > 0:
        tags_acc = accuracy_score(valid_t_eval, valid_t_pred)
        print(f"Tag(完全一致)预测准确率: {tags_acc:.2%}")

# Rewrite ML_Performance_Report.csv cleanly
report_file = "/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/ML_Performance_Report.csv"
report_data = pd.DataFrame([{
    "batch": 1,
    "sample_count": len(b1_df),
    "category_accuracy": cat_acc,
    "tags_exact_match_accuracy": tags_acc
}])
report_data.to_csv(report_file, index=False)
print("\n[+] ML_Performance_Report.csv 已被覆写为干净、规范的初板 (只含 Batch 1)！")

print(f"\n=== 重置并应用分类机器学习 (只基于 Batch 1) ===")
X_train = (b1_df["title"].fillna("") + " " + b1_df["abstract"].fillna("")).tolist()
Y_train_category = b1_df["category"].tolist()
Y_train_tags = b1_df["tags"].fillna("").tolist()

clf_cat = Pipeline([('tfidf', TfidfVectorizer(stop_words='english', max_features=3000)), ('clf', MultinomialNB())])
clf_tags = Pipeline([('tfidf', TfidfVectorizer(stop_words='english', max_features=3000)), ('clf', MultinomialNB())])

clf_cat.fit(X_train, Y_train_category)
clf_tags.fit(X_train, Y_train_tags)

target_idx = df[(df["annotation_batch"] == 2) & (df["is_manually_confirmed"] == False)].index
if not target_idx.empty:
    X_target = (df.loc[target_idx, "title"].fillna("") + " " + df.loc[target_idx, "abstract"].fillna("")).tolist()
    df.loc[target_idx, "category"] = clf_cat.predict(X_target)
    df.loc[target_idx, "auto_predicted_category"] = clf_cat.predict(X_target)
    
    df.loc[target_idx, "tags"] = clf_tags.predict(X_target)
    df.loc[target_idx, "auto_predicted_tags"] = clf_tags.predict(X_target)
    
    df.to_excel(db_path, index=False)
    print(f"[+] 仅用 Batch 1 训练完毕。已规范地覆盖更新了 Batch 2 ({len(target_idx)} 条) 的预测数据。")
else:
    print(f"没有找需要预测的 Batch 2 数据。")

