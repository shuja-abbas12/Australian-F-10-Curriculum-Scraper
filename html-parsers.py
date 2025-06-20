# update_ld_as_counts.py

import os, re, pandas as pd
from bs4 import BeautifulSoup
from datetime import datetime, UTC

CSV_PATH = "FinalData.csv"
HTML_DIR = "html"
LD_COL   = "Level description"
AS_COL   = "Achievement standard"

def load_html(subject, year):
    # 1) replace slashes with space, collapse multiple spaces
    subj = subject.replace("/", " ")
    subj = re.sub(r"\s+", " ", subj).strip()
    # 2) build filename
    filename = f"{subj} {year}.html"
    path     = os.path.join(HTML_DIR, filename)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8", errors="ignore") as fh:
        return BeautifulSoup(fh.read(), "html.parser")

def year_tokens(year_label: str):
    """Generate tokens like 'year-7', 'years-6-and-7', 'years-7-and-8'…"""
    y = year_label.lower()
    if y.startswith("foundation"):
        return ["foundation-year", "years-foundation-and-year-1"]
    m = re.match(r"year\s*(\d+)", y)
    if not m:
        return [y.replace(" ", "-")]
    n = int(m.group(1))
    toks = [f"year-{n}"]
    if n > 0:
        toks.append(f"years-{n-1}-and-{n}")
    if n < 10:
        toks.append(f"years-{n}-and-{n+1}")
    return toks

def count_words(soup, prefix, year_label):
    """Find <section id^=prefix> containing any year_token, count its words."""
    for tok in year_tokens(year_label):
        sec = soup.find(lambda t: (
            t.name == "section" and t.has_attr("id")
            and t["id"].startswith(prefix) and tok in t["id"]
        ))
        if sec:
            text = " ".join(sec.stripped_strings)
            return len(text.split())
    return pd.NA

# ── main ─────────────────────────────────────────────────────────────
df = pd.read_csv(CSV_PATH)

# ensure new columns exist
for col in (LD_COL, AS_COL):
    if col not in df.columns:
        df[col] = pd.NA

missing = []  # track rows still unresolved

for idx, row in df.iterrows():
    subj = str(row["Subject"]).strip()
    yr   = str(row["Year"]).strip()

    soup = load_html(subj, yr)
    if soup is None:
        missing.append((subj, yr, "file"))
        continue

    ld_cnt = count_words(soup, "level-description", yr)
    as_cnt = count_words(soup, "achievement-standard", yr)

    if pd.isna(ld_cnt): missing.append((subj, yr, "LD"))
    if pd.isna(as_cnt): missing.append((subj, yr, "AS"))

    df.at[idx, LD_COL] = ld_cnt
    df.at[idx, AS_COL] = as_cnt

# cast to nullable integer so no more .0
df[LD_COL] = df[LD_COL].astype("Int64")
df[AS_COL] = df[AS_COL].astype("Int64")

df.to_csv(CSV_PATH, index=False)

print(f"[{datetime.now(UTC).isoformat(timespec='seconds')}] counts updated\n")
if missing:
    print("Rows still missing data:")
    for s,y,what in missing:
        print(f"  – {s} | {y}  (missing {what})")
else:
    print("✓ All rows populated.")
