import pandas as pd
import re
df = pd.read_excel('/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/spatial_literature.xlsx')

cns_journals = ["cell", "nature", "science"]
def is_cns(journal_name):
    if pd.isna(journal_name): return False
    j = str(journal_name).lower()
    return any(re.search(rf"\b{c}\b", j) for c in cns_journals)

unconfirmed_mask = df["is_manually_confirmed"] == False

# Reset incorrectly confirmed "Research" papers since yesterday if the user missed any?
# User said: "我发现它也还挺有用的... 我已经把你自动修改的人工标注的非CNS正刊的...改回来了"
# We just want to make sure the latest active learning run from the user (which failed) didn't corrupt the file.
for idx in df[unconfirmed_mask].index:
    cat = df.loc[idx, "category"]
    journal = df.loc[idx, "journal"]
    if cat == "研究" and not is_cns(journal):
        df.loc[idx, "annotation_batch"] = 999

df.to_excel('/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/spatial_literature.xlsx', index=False)
print("Data checked and saved!")
