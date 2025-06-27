#!/usr/bin/env python3
"""
Batch scraper — identical per-row logic used for rows 0 & 1,
now applied to every row in FinalData.csv
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

# ── constants ──────────────────────────────────────────────
CSV_FILE      = Path("FinalData.csv")
DATA_DIR      = Path("data")
HEADLESS      = False          # show Chrome
PAGE_TIMEOUT  = 35
WAIT          = 15
BASE_PT       = 10
WRAP          = 90
MARGIN        = 40
LINE_SP       = 1.4
COL           = "Understanding of the learning area"
SEGMENT       = "/curriculum-information/understand-this-learning-area/"

FONT = {
    "h1": ("Helvetica-Bold",18), "h2": ("Helvetica-Bold",16),
    "h3": ("Helvetica-Bold",14), "h4": ("Helvetica-Bold",12),
    "h5": ("Helvetica-Bold",11), "h6": ("Helvetica-Bold",10),
}
DEF_FONT = ("Helvetica", BASE_PT); BULLET = ("Helvetica-Bold", BASE_PT)
WRE = re.compile(r"\b[\w'-]+\b", re.UNICODE)
slug = lambda s: re.sub(r"[\\/:'\"*?<>|]+", "_", str(s).strip())
say  = lambda m: print(m, flush=True)

# ── selenium helpers ──────────────────────────────────────
def start_drv():
    o = Options()
    if HEADLESS: o.add_argument("--headless=new")
    o.add_argument("--window-size=1400,1000")
    return webdriver.Chrome(options=o)

def ready(d): return d.execute_script("return document.readyState")=="complete"

def locate_cta(d):
    sel=("section.SlideOut.UnderstandArea-slideOut.is-open "
         "div>div>a.Button--external")
    return WebDriverWait(d,5).until(EC.element_to_be_clickable((By.CSS_SELECTOR,sel)))

def expand_all(d):
    for b in d.find_elements(
            By.CSS_SELECTOR,
            "section.ContentToggle:not(.is-open) > header > button, "
            "button[aria-expanded='false']"):
        with contextlib.suppress(Exception):
            d.execute_script("arguments[0].click()", b); time.sleep(.05)

# ── extract helpers ───────────────────────────────────────
def _clean(n):
    for t in n(["script","style","noscript","iframe","nav"]): t.decompose()
    for t in n.find_all(lambda x:isinstance(x,bs4.Tag) and (
            x.get("aria-hidden")=="true" or "display:none" in (x.get("style") or ""))):
        t.decompose()

def _yield(main):
    for t in main.descendants:
        if isinstance(t,bs4.Tag) and t.name in {"h1","h2","h3","h4","h5","h6","p","li","blockquote"}:
            txt=" ".join(t.get_text(" ",strip=True).split())
            if txt: yield t.name, txt

def extract_lines(html):
    soup=BeautifulSoup(html,"lxml")
    main=soup.select_one("#main-content"); _clean(main)
    lines=[]
    title=soup.select_one("header[id^='title-'] h1")
    if title: lines.append((title.text.strip(), *FONT["h1"]))
    for h in main.find_all(["h2","h3","h4","h5","h6"]):
        if h.text.strip().lower().startswith("resources"):
            for x in list(h.find_all_next()): x.decompose(); h.decompose(); break
    for tag,txt in _yield(main):
        lines.append(("• "+txt,*BULLET) if tag=="li" else (txt,*FONT.get(tag,DEF_FONT)))
    return lines

# ── PDF utils ─────────────────────────────────────────────
def write_pdf(lines, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    c=Canvas(str(path), pagesize=A4)
    w,h=A4; x,y=MARGIN,h-MARGIN
    for txt, font, sz in lines:
        c.setFont(font,sz)
        for seg in textwrap.wrap(txt, WRAP) or [""]:
            if y<MARGIN: c.showPage(); y=h-MARGIN; c.setFont(font,sz)
            c.drawString(x,y,seg); y-=sz*LINE_SP
    c.save()

def pdf_words(p):
    txt="\n".join(pg.extract_text() or "" for pg in PdfReader(str(p)).pages)
    return len(WRE.findall(txt))

# ── per-row process (unchanged) ──────────────────────────
def process(d, subj, yr, url):
    say(f"\n>>> {subj} / {yr}")
    d.get(url); WebDriverWait(d,PAGE_TIMEOUT).until(ready)

    before=d.window_handles.copy()
    locate_cta(d).click()
    WebDriverWait(d,WAIT).until(lambda drv: len(drv.window_handles)>len(before))
    d.switch_to.window(d.window_handles[-1])
    WebDriverWait(d,PAGE_TIMEOUT).until(lambda drv: SEGMENT in drv.current_url)
    WebDriverWait(d,PAGE_TIMEOUT).until(ready)

    expand_all(d); time.sleep(.3)
    lines=extract_lines(d.page_source)
    pdf=DATA_DIR/slug(subj)/slug(yr)/f"{subj} - Understanding of the learning area.pdf"
    write_pdf(lines, pdf); wc=pdf_words(pdf)
    say(f"   PDF → {pdf}  ({wc} words)")
    d.close(); d.switch_to.window(before[0])
    return wc

# ── main loop ────────────────────────────────────────────
def main():
    if not CSV_FILE.exists(): say("CSV missing"); return
    df=pd.read_csv(CSV_FILE,dtype=str)
    if COL not in df.columns: df[COL]=""

    drv=start_drv()
    try:
        for i,row in df.iterrows():
            try:
                wc=process(drv,row["Subject"],row["Year"],row["URL"])
                df.at[i,COL]=wc; df.to_csv(CSV_FILE,index=False)
            except Exception as e:
                say(f"!! row {i}: {e.__class__.__name__}")
                traceback.print_exc(limit=1)
                Path(f"fail_{slug(row['Subject'])}_{slug(row['Year'])}.html")\
                    .write_text(drv.page_source,"utf-8")
    finally:
        drv.quit(); say("\nDone.")

if __name__=="__main__":
    main()
