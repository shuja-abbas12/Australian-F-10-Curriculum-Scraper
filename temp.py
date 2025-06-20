"""
sum_total_pages.py
==================
Compute the overall total pages by summing the Pages column
from the "ByYear" sheet of your rounded workbook.

Usage
-----
$ python sum_total_pages.py
"""

import pandas as pd
from pathlib import Path

# ---------- Config ----------
INPUT_XLSX = Path("Final-Results.xlsx")  # the workbook with integer "Pages"
# --------------------------------

def main():
    if not INPUT_XLSX.exists():
        raise FileNotFoundError(f"{INPUT_XLSX} not found.")

    # Read the per‐year sheet
    by_year = pd.read_excel(INPUT_XLSX, sheet_name="ByYear")

    # Sum all Pages values
    total_pages = int(by_year["Pages"].sum())

    # Output the single total
    print(f"Total pages across all subjects: {total_pages}")

if __name__ == "__main__":
    main()
