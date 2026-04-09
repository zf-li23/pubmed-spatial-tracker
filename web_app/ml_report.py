import pandas as pd
import os
from sklearn.metrics import classification_report, accuracy_score

db_path = "/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/spatial_literature.xlsx"
df = pd.read_excel(db_path)

confirmed_df = df[df["is_manually_confirmed"] == True]
# Let's say we analyze Batch 1
b1 = confirmed_df[confirmed_df["annotation_batch"] == 1]
b1_cat_acc = accuracy_score(b1['category'].astype(str), b1['auto_predicted_category'].astype(str)) if not b1.empty else 0

report_data = {
    "batch": [1],
    "sample_count": [len(b1)],
    "category_accuracy": [b1_cat_acc],
    "tags_exact_match_accuracy": [0.0]
}
report_df = pd.DataFrame(report_data)
report_file = "/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/ML_Performance_Report.csv"
report_df.to_csv(report_file, index=False)
