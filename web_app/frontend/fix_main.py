import re

with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/main.py", "r") as f:
    text = f.read()

# fix columns
old_cols = """    columns = [
        "pmid", "doi", "title", "abstract", "pub_year", "journal",
        "category", "tags", "mesh_terms", "keywords", "is_preprint",
        "is_method_note", "citation_count", "is_manually_confirmed", "pdf_path", "notes"
    ]"""
new_cols = """    columns = [
        "pmid", "doi", "url", "title", "abstract", "pub_year", "journal",
        "category", "tags", "mesh_terms", "keywords", "is_preprint",
        "is_method_note", "citation_count", "is_manually_confirmed", "pdf_path", "notes",
        "annotation_batch", "auto_predicted_category", "auto_predicted_tags"
    ]"""
text = text.replace(old_cols, new_cols)

with open("/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/main.py", "w") as f:
    f.write(text)
print("Done")
