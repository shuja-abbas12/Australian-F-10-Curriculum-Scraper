# rename_html_files.py

import os
import re

# Path to your HTML directory
HTML_DIR = "html"

for old_name in os.listdir(HTML_DIR):
    if not old_name.lower().endswith(".html"):
        continue

    old_path = os.path.join(HTML_DIR, old_name)
    base, ext = os.path.splitext(old_name)

    # 1) Replace all underscores with spaces
    new_base = base.replace("_", " ")
    # 2) Collapse any multiple spaces into one
    new_base = re.sub(r"\s+", " ", new_base).strip()

    new_name = new_base + ext
    new_path = os.path.join(HTML_DIR, new_name)

    if old_name != new_name:
        os.rename(old_path, new_path)
        print(f"Renamed: {old_name}  →  {new_name}")
