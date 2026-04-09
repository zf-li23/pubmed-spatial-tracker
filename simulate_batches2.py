import pandas as pd
import numpy as np
import os
import sys

# Add web_app to path for ml_pipeline
sys.path.append(os.path.join(os.path.dirname(__file__), 'web_app'))
from ml_pipeline import AutomatedActiveLearner

print("Loading data...")
file_path = "spatial_literature.xlsx"
df = pd.read_excel(file_path)

cns_exact = ["Cell", "Nature", "Science (New York, N.Y.)"]
def is_cns(journal_name):
    if pd.isna(journal_name):
        return False
    return str(journal_name).strip() in cns_exact

confirmed_idx = df[df["is_manually_confirmed"] == True].index.tolist()
unconfirmed_idx = df[df["is_manually_confirmed"] == False].index.tolist()

df["annotation_batch"] = np.nan

b1_idx = confirmed_idx[:50]
b2_idx = confirmed_idx[50:150]
b3_idx = confirmed_idx[150:350]
b4_confirmed_idx = confirmed_idx[350:]

df.loc[b1_idx, "annotation_batch"] = 1
df.loc[b2_idx, "annotation_batch"] = 2
df.loc[b3_idx, "annotation_batch"] = 3
df.loc[b4_confirmed_idx, "annotation_batch"] = 4

print(f"Batch 1: {len(b1_idx)}, Batch 2: {len(b2_idx)}, Batch 3: {len(b3_idx)}, Batch 4 confirmed: {len(b4_confirmed_idx)}")

from sklearn.metrics import f1_score
from sklearn.preprocessing import MultiLabelBinarizer
import warnings

report_rows = []

def eval_and_report(learner, train_batches_str, test_idx, test_batch_name):
    test_df = df.loc[test_idx]
    y_true_cat = test_df["category"].tolist()
    y_pred_cat, y_pred_tags = learner.predict(test_df)
    
    correct = sum(1 for yt, yp in zip(y_true_cat, y_pred_cat) if yt == yp)
    acc = correct / len(y_true_cat) if len(y_true_cat) > 0 else 0
    
    y_true_tags_raw = [str(t).split(';') for t in test_df["tags"].tolist()]
    y_true_tags_clean = [[t.strip() for t in ts if t.strip()] for ts in y_true_tags_raw]
    y_pred_tags_raw = [str(t).split(';') for t in y_pred_tags]
    y_pred_tags_clean = [[t.strip() for t in ts if t.strip()] for ts in y_pred_tags_raw]
    
    if learner.mlb is not None:
        tmp_mlb = MultiLabelBinarizer(classes=learner.mlb.classes_)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            y_true_bin = tmp_mlb.fit_transform(y_true_tags_clean)
            y_pred_bin = tmp_mlb.transform(y_pred_tags_clean)
            micro_f1 = f1_score(y_true_bin, y_pred_bin, average="micro", zero_division=0)
            macro_f1 = f1_score(y_true_bin, y_pred_bin, average="macro", zero_division=0)
    else:
        micro_f1, macro_f1 = 0, 0
        
    report_rows.append({
        "Trained_On_Batches": train_batches_str,
        "Tested_On_Batch": test_batch_name,
        "Test_Samples": len(y_true_cat),
        "Category_Accuracy": round(acc, 3),
        "Tag_Micro_F1": round(micro_f1, 3),
        "Tag_Macro_F1": round(macro_f1, 3)
    })
    
    df.loc[test_idx, "auto_predicted_category"] = y_pred_cat
    df.loc[test_idx, "auto_predicted_tags"] = y_pred_tags


learner = AutomatedActiveLearner()

# Row 1: Baseline (0) on Batch 1
b1_df = df.loc[b1_idx]
y_true_cat_b1 = b1_df["category"].tolist()
y_pred_cat_b1 = b1_df["auto_predicted_category"].fillna("Research").tolist()
correct_b1 = sum(1 for yt, yp in zip(y_true_cat_b1, y_pred_cat_b1) if yt == yp)
acc_b1 = correct_b1 / len(y_true_cat_b1) if len(y_true_cat_b1) > 0 else 0
report_rows.append({
    "Trained_On_Batches": "Baseline(0)",
    "Tested_On_Batch": 1,
    "Test_Samples": len(y_true_cat_b1),
    "Category_Accuracy": round(acc_b1, 3),
    "Tag_Micro_F1": 0,
    "Tag_Macro_F1": 0
})

# Row 2: Train on [1], Eval on Batch 2
learner.fit(df.loc[b1_idx])
eval_and_report(learner, "[1]", b2_idx, 2)

# Row 3: Train on [1, 2], Eval on Batch 3
learner.fit(df.loc[b1_idx + b2_idx])
eval_and_report(learner, "[1, 2]", b3_idx, 3)

# Do NOT eval on Batch 4, because Batch 4 is incomplete (next_batch)

# Final Training on ALL confirmed data before Batch 4
print("Training final model on [1, 2, 3] for predictions...")
learner.fit(df.loc[b1_idx + b2_idx + b3_idx])

# Predict on Unconfirmed
unconfirmed_df = df.loc[unconfirmed_idx]
pred_cats, pred_tags = learner.predict(unconfirmed_df)

df.loc[unconfirmed_idx, "auto_predicted_category"] = pred_cats
df.loc[unconfirmed_idx, "auto_predicted_tags"] = pred_tags

batch_999_idx = []
remaining_unconfirmed_idx = []

for i, idx in enumerate(unconfirmed_idx):
    cat = pred_cats[i]
    journal = df.loc[idx, "journal"]
    if cat == "Research" and not is_cns(journal):
        batch_999_idx.append(idx)
    else:
        remaining_unconfirmed_idx.append(idx)

df.loc[batch_999_idx, "annotation_batch"] = 999
print(f"Assigned {len(batch_999_idx)} non-CNS Research articles to Batch 999.")

# Batch 4 needs 400 total.
b4_needed = 400 - len(b4_confirmed_idx)
b4_unconf = remaining_unconfirmed_idx[:b4_needed]
df.loc[b4_unconf, "annotation_batch"] = 4
remaining_unconfirmed_idx = remaining_unconfirmed_idx[b4_needed:]

print(f"Batch 4 filled with {len(b4_unconf)} unconfirmed. Total in B4: {len(b4_confirmed_idx) + len(b4_unconf)}")

curr_batch = 5
curr_size = 800

while remaining_unconfirmed_idx:
    batch_idx = remaining_unconfirmed_idx[:curr_size]
    df.loc[batch_idx, "annotation_batch"] = curr_batch
    remaining_unconfirmed_idx = remaining_unconfirmed_idx[curr_size:]
    print(f"Batch {curr_batch} filled with {len(batch_idx)} items.")
    curr_batch += 1
    curr_size *= 2

df.to_excel(file_path, index=False)
pd.DataFrame(report_rows).to_csv("ML_Performance_Report.csv", index=False)
print("Done. Saved to excel and ML_Performance_Report.csv.")
