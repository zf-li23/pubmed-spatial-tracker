import re

with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/web_app/app.py", "r") as f:
    text = f.read()

# fix upload_pdf_url to also save URL
if 'df.loc[idx, "pdf_path"] = filepath' in text and 'df.loc[idx, "url"] = url' not in text:
    text = text.replace('df.loc[idx, "pdf_path"] = filepath', 'df.loc[idx, "pdf_path"] = filepath\n    df.loc[idx, "url"] = url')

# fix save_pdf_link
if 'df.loc[idx, "pdf_path"] = url' in text:
    text = text.replace('df.loc[idx, "pdf_path"] = url', 'df.loc[idx, "url"] = url')

with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/web_app/app.py", "w") as f:
    f.write(text)
print("app.py URL saving parts updated")
