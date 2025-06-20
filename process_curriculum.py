"""
process_curriculum.py
---------------------
End‑to‑end script that:

1. Reads `FinalData.csv` (must be in the same directory).
2. Adds a **Total count** column that sums:
      • "Understanding of the subject"
      • "Level description"
      • "Achievement standard"
      • "Content Description"
3. Divides **Total count** by 250 to compute **Pages**.
4. Writes `SubjectPages.xlsx` with two tabs:
      • "ByYear"    – Subject | Year | Pages
      • "BySubject" – Subject | Total Pages (summed across years)

Usage
~~~~~
$ python process_curriculum.py
"""

from pathlib import Path
import sys

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    sys.exit("❌ pandas is required: pip install pandas openpyxl")

# ---------- Config ----------
INPUT_CSV   = Path("FinalData.csv")
OUTPUT_XLSX = Path("result.xlsx")

# Columns to sum for Total count
COUNT_COLS = [
    "Understanding of the subject",
    "Level description",
    "Achievement standard",
    "Content Description",
]
# ----------------------------


def main() -> None:
    if not INPUT_CSV.exists():
        sys.exit(f"❌ {INPUT_CSV} not found in {Path.cwd()}")

    # Load data
    df = pd.read_csv(INPUT_CSV)

    # Ensure required columns exist
    missing = [c for c in COUNT_COLS + ["Subject", "Year"] if c not in df.columns]
    if missing:
        sys.exit(f"❌ Missing columns in CSV: {', '.join(missing)}")

    # 1) Total count
    df["Total count"] = df[COUNT_COLS].sum(axis=1, skipna=True)

    # 2) Pages
    df["Pages"] = df["Total count"] / 250

    # 3) Sheet 1 – by year
    by_year = df[["Subject", "Year", "Pages"]].copy()

    # 4) Sheet 2 – grouped by subject
    by_subject = (
        by_year.groupby("Subject", as_index=False)["Pages"]
        .sum()
        .rename(columns={"Pages": "Total Pages"})
    )

    # 5) Write Excel file
    with pd.ExcelWriter(OUTPUT_XLSX, engine="openpyxl") as writer:
        by_year.to_excel(writer, sheet_name="ByYear", index=False)
        by_subject.to_excel(writer, sheet_name="BySubject", index=False)

    print(f"✅ Processed. Results written to {OUTPUT_XLSX.absolute()}")


if __name__ == "__main__":
    main()
