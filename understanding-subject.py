"""
add_understanding_column.py
───────────────────────────
• Loads FinalData.csv (expects columns: Subject, Year, URL)
• Scans ./Understanding of learning area/*.docx
• For each row, finds the best-matching .docx by subject name:
      1. exact match (ignoring spaces / case)
      2. any two-word sequence match
      3. first word match
• Extracts ALL paragraph text from the .docx
• Writes it into a new column "Understanding of the subject"
• Overwrites FinalData.csv in-place
"""
import os, unicodedata, re
import pandas as pd
from docx import Document
from datetime import datetime, UTC

CSV_PATH   = "FinalData.csv"
DOCX_DIR   = "Understanding of learning area"
NEW_COL    = "Understanding of the subject"

# ── helper functions ───────────────────────────────────────────
def normalise(txt: str) -> str:
    return unicodedata.normalize("NFKD", txt).encode("ascii","ignore").decode()

def match_docx(subject: str, docx_list):
    """Return best matching .docx filename or None."""
    subj_norm = normalise(subject).lower()
    subj_key  = subj_norm.replace(" ", "")

    # 1) exact (no spaces)
    for fn in docx_list:
        name_key = normalise(os.path.splitext(fn)[0]).lower().replace(" ", "")
        if name_key == subj_key:
            return fn

    words = subj_norm.split()

    # 2) two-word sequence
    if len(words) >= 2:
        for fn in docx_list:
            fn_norm = normalise(fn).lower()
            for i in range(len(words)-1):
                if f"{words[i]} {words[i+1]}" in fn_norm:
                    return fn

    # 3) first-word fallback
    first = words[0]
    for fn in docx_list:
        if first in normalise(fn).lower():
            return fn
    return None

def extract_docx_text(path):
    doc = Document(path)
    return "\n".join(p.text for p in doc.paragraphs)

# ── load data ──────────────────────────────────────────────────
if not os.path.exists(CSV_PATH):
    raise FileNotFoundError("FinalData.csv not found.")

df = pd.read_csv(CSV_PATH)

docx_files = [f for f in os.listdir(DOCX_DIR) if f.lower().endswith(".docx")]
if not docx_files:
    raise FileNotFoundError("No .docx files found in 'Understanding of learning area/'")

# ── build new column ───────────────────────────────────────────
texts = []
for subj in df["Subject"]:
    fn = match_docx(subj, docx_files)
    if fn:
        full_path = os.path.join(DOCX_DIR, fn)
        texts.append(extract_docx_text(full_path))
    else:
        texts.append("")

df[NEW_COL] = texts

# ── save ───────────────────────────────────────────────────────
df.to_csv(CSV_PATH, index=False)
print(f"[{datetime.now(UTC).isoformat(timespec='seconds')}]  "
      f"FinalData.csv updated – {NEW_COL} column populated.")
