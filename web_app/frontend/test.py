import pandas as pd
from sklearn.metrics import accuracy_score
db_path = '/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/spatial_literature.xlsx'
df = pd.read_excel(db_path)
b1 = df[(df['is_manually_confirmed'] == True) & (df['annotation_batch'] == 1)]
print(f"Batch 1 Categorical Accuracy: {accuracy_score(b1['category'].astype(str), b1['auto_predicted_category'].astype(str)):.2%}")
if "auto_predicted_tags" in b1:
    print(f"Batch 1 Tag Accuracy: {accuracy_score(b1['tags'].fillna('').astype(str), b1['auto_predicted_tags'].fillna('').astype(str)):.2%}")
