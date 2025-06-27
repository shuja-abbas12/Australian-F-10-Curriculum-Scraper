#!/usr/bin/env python3
"""
Crawler – Level description + Achievement standard
(single-year + combined-year ids, now with list capture + faster suffix checks)
"""

from __future__ import annotations
import re, textwrap, traceback, contextlib, sys, time
from pathlib import Path
import pandas as pd
from bs4 import BeautifulSoup, element as bs4
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from PyPDF2 import PdfReader
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─── configuration ───────────────────────────────────────────────────
HEADLESS      = False
PAGE_TIMEOUT  = 35
WAIT          = 15
BASE_PT       = 10
WRAP          = 90
MARGIN        = 40
LINE_SP       = 1.4
CSV_FILE      = Path("FinalData.csv")
DATA_DIR      = Path("data")
NEW_COL       = "Description/Achievement"

HEADING_FONT  = ("Helvetica-Bold", 16)
BODY_FONT     = ("Helvetica", BASE_PT)
BULLET_FONT   = ("Helvetica-Bold", BASE_PT)

TRAIL_RE = re.compile(r",\s*(?:collapse|expand)\s+this\s+section\b.*", re.I)
WORD_RE  = re.compile(r"\b[\w'-]+\b", re.UNICODE)
slug     = lambda s: re.sub(r"[\\/:'\"*?<>|]+", "_", str(s).strip())
say      = lambda m: print(m, flush=True)

# ─── selenium helpers ────────────────────────────────────────────────
def start_driver():
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,1000")
    return webdriver.Chrome(options=opts)

def ready(d): return d.execute_script("return document.readyState") == "complete"

def close_slideout(d):
    css = ("section.SlideOut.UnderstandArea-slideOut.is-open > div > button")
    with contextlib.suppress(Exception):
        WebDriverWait(d, 6).until(EC.element_to_be_clickable((By.CSS_SELECTOR, css))).click()

def expand_if_present(d, css_sel):
    """Click header button only if it exists; skip otherwise (no long wait)."""
    btns = d.find_elements(By.CSS_SELECTOR, css_sel)
    if btns:
        with contextlib.suppress(Exception):
            WebDriverWait(d, 5).until(EC.element_to_be_clickable((By.CSS_SELECTOR, css_sel))).click()

# ─── year-suffix variants ────────────────────────────────────────────
def year_variants(label: str) -> list[str]:
    lbl = label.lower().strip()
    if lbl.startswith("foundation"):
        return ["foundation-year", "years-foundation-and-year-1"]

    m = re.match(r"year\s*(\d+)", lbl)
    if not m:
        return [lbl.replace(" ", "-")]

    n = int(m.group(1))
    out = [f"year-{n}"]
    if n > 0:  out.append(f"years-{n-1}-and-{n}")
    if n < 10: out.append(f"years-{n}-and-{n+1}")
    return out

# ─── HTML → lines (now includes <li>) ────────────────────────────────
def _clean(tag):
    for t in tag(["script","style","noscript","iframe"]): t.decompose()
    for t in tag.find_all(lambda x:isinstance(x,bs4.Tag) and (
            x.get("aria-hidden")=="true" or "display:none" in (x.get("style") or ""))):
        t.decompose()

def extract_desc_ach(html: str, level_sel: str, ach_sel: str):
    soup = BeautifulSoup(html, "lxml")
    blocks = []
    for sel in (level_sel, ach_sel):
        hdr  = soup.select_one(f"{sel} > header > button")
        body = soup.select_one(f"{sel} > div")
        if not (hdr and body): continue
        heading = TRAIL_RE.sub("", hdr.get_text(" ", strip=True))
        _clean(body)
        paras_and_lis = body.select("p, li")  # ← lists captured
        blocks.append((heading, paras_and_lis))

    lines = []
    for heading, nodes in blocks:
        lines.append((heading, *HEADING_FONT))
        for node in nodes:
            txt = " ".join(node.get_text(" ", strip=True).split())
            if not txt: continue
            if node.name == "li":
                txt = "• " + txt
                font = BULLET_FONT
            else:
                font = BODY_FONT
            for ln in textwrap.wrap(txt, WRAP) or [""]:
                lines.append((ln, *font))
    return lines

# ─── PDF helpers ─────────────────────────────────────────────────────
def write_pdf(lines, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    can = Canvas(str(path), pagesize=A4)
    _, h = A4
    x, y = MARGIN, h - MARGIN
    for txt, font, sz in lines:
        can.setFont(font, sz)
        if y < MARGIN:
            can.showPage(); y = h - MARGIN; can.setFont(font, sz)
        can.drawString(x, y, txt)
        y -= sz * LINE_SP
    can.save()

def pdf_words(p: Path) -> int:
    txt = "\n".join(pg.extract_text() or "" for pg in PdfReader(str(p)).pages)
    return len(WORD_RE.findall(txt))

# ─── per-row workflow ────────────────────────────────────────────────
def process_row(drv, subj, yr, url):
    say(f"\n>>> {subj} / {yr}")
    drv.get(url); WebDriverWait(drv, PAGE_TIMEOUT).until(ready)
    close_slideout(drv)

    lines = []
    for suffix in year_variants(yr):
        level_sel = f"#level-description\\:--{suffix}"
        ach_sel   = f"#achievement-standard\\:--{suffix}"

        expand_if_present(drv, f"{level_sel} > header > button")
        expand_if_present(drv, f"{ach_sel}  > header > button")
        time.sleep(.2)

        lines = extract_desc_ach(drv.page_source, level_sel, ach_sel)
        if lines: break  # found the correct suffix

    if not lines:
        raise ValueError("description / achievement not found")

    pdf = DATA_DIR/slug(subj)/slug(yr)/ \
          f"Level Description-Achievement standard-{subj}-{yr}.pdf"
    write_pdf(lines, pdf)
    wc = pdf_words(pdf)
    say(f"   PDF → {pdf}  ({wc} words)")
    return wc

# ─── main loop ────────────────────────────────────────────────────────
def main():
    if not CSV_FILE.exists():
        say("CSV missing"); sys.exit()
    df = pd.read_csv(CSV_FILE, dtype=str)
    if NEW_COL not in df.columns:
        df[NEW_COL] = ""

    drv = start_driver()
    try:
        for i, row in df.iterrows():
            url = row.get("URL") or row.get("Link")
            if not url or not url.startswith("http"):
                say(f"[skip] row {i}: URL missing"); continue
            try:
                wc = process_row(drv, row["Subject"], row["Year"], url)
                df.at[i, NEW_COL] = wc
                df.to_csv(CSV_FILE, index=False)
            except Exception as e:
                say(f"!! row {i}: {e.__class__.__name__}")
                traceback.print_exc(limit=1)
    finally:
        drv.quit(); say("\n✅ Description/Achievement PDF + counts complete.")

if __name__ == "__main__":
    main()
