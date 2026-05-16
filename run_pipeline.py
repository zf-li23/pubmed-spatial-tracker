#!/usr/bin/env python3
"""离线重训管道：备份数据库 → naive 重计算 → ML 重训 → 更新预测。"""

import pandas as pd
import os, sys, shutil
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "web_app"))

from sqlalchemy import create_engine, text
from migrate_naive import get_naive
from web_app.ml_pipeline import SpatialLiteratureClassifier

DB_PATH = os.path.join(os.path.dirname(__file__), "spatial_literature.db")
ENGINE = create_engine(f"sqlite:///{DB_PATH}")

# ── 1. 备份 ──
ts = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_path = f"spatial_literature_backup_{ts}.db"
shutil.copy2(DB_PATH, backup_path)
print(f"Backup: {backup_path}")

# ── 2. 读取 ──
df = pd.read_sql("SELECT * FROM literature", ENGINE)
print(f"Loaded {len(df)} articles")

# ── 3. Naive 重分类 ──
if "naive_category" not in df.columns:
    df["naive_category"] = ""
if "naive_tags" not in df.columns:
    df["naive_tags"] = ""

for idx, row in df.iterrows():
    cat, tags = get_naive(row["title"], row["abstract"], row["journal"])
    df.at[idx, "naive_category"] = cat
    df.at[idx, "naive_tags"] = tags
print("Naive classification updated")

# ── 4. ML 重训 ──
train_df = df[df["is_manually_confirmed"] == 1].copy()
unlabeled_df = df[df["is_manually_confirmed"] != 1].copy()

if "uncertainty_score" not in df.columns:
    df["uncertainty_score"] = 0.0
if "is_discarded" not in df.columns:
    df["is_discarded"] = 0

if len(train_df) > 0:
    learner = SpatialLiteratureClassifier()
    learner.fit(train_df)

    if len(unlabeled_df) > 0:
        pred_cats, pred_tags, uncertainties, discard_flags = learner.predict(unlabeled_df)
        unlabeled_idx = df["is_manually_confirmed"] != 1
        df.loc[unlabeled_idx, "auto_predicted_category"] = pred_cats
        df.loc[unlabeled_idx, "auto_predicted_tags"] = pred_tags
        df.loc[unlabeled_idx, "uncertainty_score"] = uncertainties
        df.loc[unlabeled_idx, "is_discarded"] = discard_flags
        print(f"ML prediction updated for {len(unlabeled_df)} articles")

# ── 5. 保存（逐行 upsert） ──
with ENGINE.begin() as con:
    for _, row in df.iterrows():
        row_dict = row.to_dict()
        cols = list(row_dict.keys())
        placeholders = ", ".join([f":{c}" for c in cols])
        con.execute(
            text(f"INSERT OR REPLACE INTO literature ({', '.join(cols)}) VALUES ({placeholders})"),
            row_dict,
        )

# 清理备份（保存成功后）
os.remove(backup_path)
print("Pipeline completed successfully.")
