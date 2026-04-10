with open("web_app/app.py", "r") as f:
    content = f.read()

old_save = """def save_df(df):
    df.to_excel(DATA_FILE, index=False)"""

new_save = """from threading import Lock
import shutil
import os
df_lock = Lock()

def save_df(df):
    with df_lock:
        temp_file = DATA_FILE + ".writing"
        t_bak = DATA_FILE + ".backup"
        
        # 1. Write fully to a temp file
        df.to_excel(temp_file, index=False)
        
        # 2. Swap atomically (or near-atomically across platforms)
        if os.path.exists(DATA_FILE):
            shutil.copyfile(DATA_FILE, t_bak) # keep a quick backup
            
        os.replace(temp_file, DATA_FILE)"""

content = content.replace(old_save, new_save)

with open("web_app/app.py", "w") as f:
    f.write(content)
