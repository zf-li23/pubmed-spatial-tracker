import re

with open('/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/web_app/app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# remove what I appended
text = re.sub(r'class TagRenameData.*?\n(?=EOF|$)', '', text, flags=re.DOTALL)
text = text.replace('EOF', '').strip()

endpoints = """
class TagRenameData(BaseModel):
    old_tag: str
    new_tag: str
    
class TagDeleteData(BaseModel):
    tag: str

@app.put("/api/tags/rename")
def rename_tag(data: TagRenameData):
    df = get_df()
    if df.empty:
        return {"message": "Success"}
    
    def replace_tag(tags_str):
        if pd.isna(tags_str) or not str(tags_str).strip():
            return tags_str
        tags = [t.strip() for t in str(tags_str).split(";")]
        new_tags = [data.new_tag if t == data.old_tag else t for t in tags]
        new_tags = [t for t in new_tags if t]
        return "; ".join(new_tags)
        
    df["tags"] = df["tags"].apply(replace_tag)
    save_df(df)
    return {"message": "Success"}

@app.request("/api/tags/delete", methods=["DELETE"])
def delete_tag(data: TagDeleteData):
    df = get_df()
    if df.empty:
        return {"message": "Success"}
        
    def remove_tag(tags_str):
        if pd.isna(tags_str) or not str(tags_str).strip():
            return tags_str
        tags = [t.strip() for t in str(tags_str).split(";")]
        new_tags = [t for t in tags if t != data.tag]
        new_tags = [t for t in new_tags if t]
        return "; ".join(new_tags)
        
    df["tags"] = df["tags"].apply(remove_tag)
    save_df(df)
    return {"message": "Success"}

# Set up static directory for React
"""

text = text.replace("# Set up static directory for React", endpoints)

with open('/home/zf-li23/yangxueruilab/PubMed_Spatial_Tracker/web_app/app.py', 'w', encoding='utf-8') as f:
    f.write(text)

