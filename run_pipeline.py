import pandas as pd
from web_app.ml_pipeline import AutomatedActiveLearner
from migrate_naive import get_naive
import sys

FILE_PATH = "spatial_literature.db"
import sqlite3
from sqlalchemy import create_engine
engine = create_engine(f"sqlite:///{FILE_PATH}")
try:
    df = pd.read_sql("SELECT * FROM literature", engine)
except Exception as e:
    print(f"Error loading {FILE_PATH}: {e}")
    sys.exit(1)

# Backup data just in case
backup_path = "spatial_literature_backup.xlsx"
df.to_excel(backup_path, index=False)
print(f"Backup saved to {backup_path}")

print("---------- Step 1: Naive Rule-based Classification ----------")
if "naive_category" not in df.columns:
    df["naive_category"] = ""
if "naive_tags" not in df.columns:
    df["naive_tags"] = ""

for idx, row in df.iterrows():
    cat, tags = get_naive(row["title"], row["abstract"], row["journal"])
    df.at[idx, "naive_category"] = cat
    df.at[idx, "naive_tags"] = tags
    
print("---------- Step 2: Machine Learning Active Prediction ----------")
train_df = df[df["is_manually_confirmed"] == True].copy()
unlabeled_df = df[df["is_manually_confirmed"] != True].copy()

if "uncertainty_score" not in df.columns:
    df["uncertainty_score"] = 0.0

if len(train_df) > 0:
    learner = AutomatedActiveLearner()
    learner.fit(train_df)
    
    if len(unlabeled_df) > 0:
        pred_cats, pred_tags, uncertainties = learner.predict(unlabeled_df)
        df.loc[df["is_manually_confirmed"] != True, "auto_predicted_category"] = pred_cats
        df.loc[df["is_manually_confirmed"] != True, "auto_predicted_tags"] = pred_tags
        df.loc[df["is_manually_confirmed"] != True, "uncertainty_score"] = uncertainties

try:
    df.to_sql("literature", engine, index=False, if_exists="replace")
    print("Pipeline run successfully! Data safely updated.")
    import os
    os.remove(backup_path) # cleanup backup after success
except Exception as e:
    print(f"Failed to save data. Backup preserved at {backup_path}. Error: {e}")
