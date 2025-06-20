"""
collapse_understanding_to_wordcount.py
──────────────────────────────────────
• Loads FinalData.csv
• Counts the number of whitespace-separated words in column
  "Understanding of the subject" for each row
• Replaces that text with the integer count
• Overwrites FinalData.csv in place
"""
import pandas as pd
from datetime import datetime, UTC

CSV_PATH = "FinalData.csv"
COL_NAME = "Understanding of the subject"

df = pd.read_csv(CSV_PATH)

if COL_NAME not in df.columns:
    raise ValueError(f'"{COL_NAME}" column not found in {CSV_PATH}')

df[COL_NAME] = df[COL_NAME].fillna("").astype(str).apply(
    lambda txt: len(txt.split())
)

df.to_csv(CSV_PATH, index=False)
print(f"[{datetime.now(UTC).isoformat(timespec='seconds')}]  "
      f"Replaced text with word counts in '{COL_NAME}'.")
