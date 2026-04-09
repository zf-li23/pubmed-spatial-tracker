import sys
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report
import os

db_path = "/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/spatial_literature.xlsx"
df = pd.read_excel(db_path)

confirmed_df = df[df["is_manually_confirmed"] == True]
unconfirmed_df = df[df["is_manually_confirmed"] == False]

if confirmed_df.empty:
    print("没有已确认的数据，无法训练。")
    sys.exit(1)

next_batch = int(unconfirmed_df["annotation_batch"].min())

# --- 1. Evaluate baseline/previous predictions ---
# 评估所有曾经被机器预测过，且现在已经被人工确认的数据
eval_df = confirmed_df[confirmed_df["auto_predicted_category"].notna()]
if not eval_df.empty:
    y_true_cat = eval_df["category"].astype(str)
    y_pred_cat = eval_df["auto_predicted_category"].astype(str)
    cat_acc = accuracy_score(y_true_cat, y_pred_cat)
    print(f"=== 表现评估 (基于 {len(eval_df)} 条已校验数据的历史预测) ===")
    print(f"大类(Category)预测准确率: {cat_acc:.2%}")
    print(classification_report(y_true_cat, y_pred_cat, zero_division=0))
    
    tags_acc = 0.0
    if "auto_predicted_tags" in eval_df.columns:
        y_true_tags = eval_df["tags"].fillna("").astype(str)
        y_pred_tags = eval_df["auto_predicted_tags"].fillna("").astype(str)
        tags_acc = accuracy_score(y_true_tags, y_pred_tags)
        print(f"Tag(完全一致)预测准确率: {tags_acc:.2%}")
        
    # 保存性能报告
    report_file = "/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/ML_Performance_Report.csv"
    report_data = pd.DataFrame([{
        "training_samples": len(confirmed_df),
        "target_batch": next_batch,
        "category_accuracy": cat_acc,
        "tags_exact_match_accuracy": tags_acc
    }])
    if os.path.exists(report_file):
        report_data.to_csv(report_file, mode='a', header=False, index=False)
    else:
        report_data.to_csv(report_file, index=False)

# --- 2. Train and Predict ---
print(f"\n=== 开始学习与预测 ===")
print(f"训练样本数: {len(confirmed_df)} (包含你在各个批次零星校验的数据)")
X_train = (confirmed_df["title"].fillna("") + " " + confirmed_df["abstract"].fillna("")).tolist()
Y_train_category = confirmed_df["category"].tolist()
Y_train_tags = confirmed_df["tags"].fillna("").tolist()

clf_cat = Pipeline([('tfidf', TfidfVectorizer(stop_words='english', max_features=3000)), ('clf', MultinomialNB())])
clf_tags = Pipeline([('tfidf', TfidfVectorizer(stop_words='english', max_features=3000)), ('clf', MultinomialNB())])

clf_cat.fit(X_train, Y_train_category)
clf_tags.fit(X_train, Y_train_tags)

target_idx = df[(df["annotation_batch"] == next_batch) & (df["is_manually_confirmed"] == False)].index
if not target_idx.empty:
    X_target = (df.loc[target_idx, "title"].fillna("") + " " + df.loc[target_idx, "abstract"].fillna("")).tolist()
    predicted_cats = clf_cat.predict(X_target)
    predicted_tags = clf_tags.predict(X_target)
    
    df.loc[target_idx, "category"] = predicted_cats
    df.loc[target_idx, "auto_predicted_category"] = predicted_cats
    df.loc[target_idx, "tags"] = predicted_tags
    df.loc[target_idx, "auto_predicted_tags"] = predicted_tags
    
    df.to_excel(db_path, index=False)
    print(f"成功对【第 {next_batch} 批次】的 {len(target_idx)} 条未校验数据进行了大类与 Tags 预测！")
else:
    print(f"第 {next_batch} 批次没有需要预测的未校验数据。")

