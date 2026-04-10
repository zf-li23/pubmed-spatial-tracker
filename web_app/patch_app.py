import re
with open("app.py", "r") as f:
    text = f.read()

pattern = r'@app\.get\("/api/tags"\)[\s\S]*?return \{"status": "success", "message": "Tags updated"\}'
match = re.search(pattern, text)
if match:
    endpoints_text = match.group(0)
    text = text.replace(endpoints_text, "")
    insertion_point = "# Set up static directory for React"
    text = text.replace(insertion_point, endpoints_text + "\n\n" + insertion_point)
    with open("app.py", "w") as f:
        f.write(text)
    print("Fixed!")
else:
    print("Not found.")
