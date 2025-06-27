#!/usr/bin/env python3
"""
content_description_extractor.py
────────────────────────────────
Row-range runner (fast edition)

• keep all functional logic from the previous version
• one Chrome instance for the entire batch
• shorter fixed sleeps and bigger scroll steps
• CLI row range still honoured (python … 10 100)
"""

from __future__ import annotations
import re, time, sys, contextlib, textwrap, traceback, pandas as pd
from pathlib import Path
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup, Tag
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen.canvas import Canvas
from PyPDF2 import PdfReader

# ─── choose rows to run ──────────────────────────────────────────────
RUN_FROM = 0          # inclusive, 0-based
RUN_TO   = 393          # inclusive, 0-based
if len(sys.argv) == 3:
    try:
        RUN_FROM, RUN_TO = map(int, sys.argv[1:3])
    except ValueError:
        print("⇢  Row numbers must be integers – ignoring CLI args.\n")

# ─── basic tunables ─────────────────────────────────────────────────
HEADLESS   = True
WAIT       = 12
SCROLL_PX  = 1200      # was 800 → fewer scrolls
SLOW       = 0.03      # was 0.10
CSV_FILE   = Path("FinalData.csv")
NEW_COL    = "Content description"
DATA_DIR   = Path("data")
PDF_NAME   = "Content description-{s}-{y}.pdf"

FONTS   = {"h1":16, "h2":14, "h3":12, "h4":12, "h5":11, "h6":11}
WRAP    = 100
MARGIN  = 40
INDENT  = 15
LINE_SP = 1.35

word_re = re.compile(r"\b[\w'-]+\b", re.UNICODE)
words   = lambda t: len(word_re.findall(t or ""))
slug    = lambda s: re.sub(r"[\\/:'\"*?<>|]+", "_", s.strip())
say     = lambda m: print(m, flush=True)
READY   = lambda d: d.execute_script("return document.readyState") == "complete"

# ─── selenium helpers ───────────────────────────────────────────────
def start_driver() -> webdriver.Chrome:
    o = Options()
    if HEADLESS:
        o.add_argument("--headless=new")
    o.add_argument("--window-size=1400,950")
    return webdriver.Chrome(options=o)

def safe_click(drv, el):
    drv.execute_script("arguments[0].scrollIntoView({block:'center'})", el)
    drv.execute_script("arguments[0].click()", el)

def win_scroll(drv) -> bool:
    prev = drv.execute_script("return document.body.scrollHeight")
    drv.execute_script(f"window.scrollBy(0,{SCROLL_PX})"); time.sleep(.03)
    return drv.execute_script("return document.body.scrollHeight") > prev

def find_text(drv, css):
    with contextlib.suppress(NoSuchElementException):
        return drv.find_element(By.CSS_SELECTOR, css).text
    return ""

def open_all_accordions(drv):
    for b in drv.find_elements(
            By.CSS_SELECTOR,
            "section.ContentToggle:not(.is-open) > header > button,"
            "button[aria-expanded='false']"):
        with contextlib.suppress(Exception):
            safe_click(drv, b); time.sleep(.01)     # was 0.03

# ─── PDF helpers (unchanged logic) ──────────────────────────────────
PDFLine = tuple[str, str, int, int]

def wrap(txt:str, width:int):
    for seg in textwrap.wrap(txt, width) or [""]:
        yield seg

STRIP = {"script","style","noscript","svg","header","footer","nav","button"}

def clean(tag:Tag):
    for t in tag.find_all(lambda x:isinstance(x,Tag) and x.name in STRIP):
        t.decompose()

def walk(node:Tag, indent:int, out:list[PDFLine]):
    if isinstance(node, str): return
    for child in node.children:
        if isinstance(child, str): continue
        nm = child.name.lower()
        if nm in FONTS:
            for seg in wrap(child.get_text(" ", strip=True), WRAP):
                out.append((seg, "Helvetica-Bold", FONTS[nm], indent))
        elif nm == "p":
            for seg in wrap(child.get_text(" ", strip=True), WRAP):
                out.append((seg, "Helvetica", 10, indent))
        elif nm in {"ul","ol"}:
            for li in child.find_all("li", recursive=False):
                for seg in wrap("• "+li.get_text(" ", strip=True), WRAP):
                    out.append((seg, "Helvetica", 10, indent))
                for sub in li.find_all(["ul","ol"], recursive=False):
                    walk(sub, indent+INDENT, out)
        else:
            walk(child, indent, out)

def html_to_lines(html:str, indent:int=0):
    soup = BeautifulSoup(html, "lxml"); clean(soup)
    out:list[PDFLine]=[]; walk(soup.body or soup, indent, out); return out

def save_pdf(lines:list[PDFLine], path:Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    c = Canvas(str(path), pagesize=A4); _,h=A4; x0,y=MARGIN,h-MARGIN
    for txt,fnt,sz,ind in lines:
        c.setFont(fnt,sz)
        if y<MARGIN: c.showPage(); y=h-MARGIN; c.setFont(fnt,sz)
        c.drawString(x0+ind,y,txt); y-=sz*LINE_SP
    c.save()
    txt="\n".join(p.extract_text() or "" for p in PdfReader(str(path)).pages)
    return words(txt)

# ─── helpers for drawer / links (logic unchanged) ────────────────────
def drawer_body(d):
    return WebDriverWait(d, WAIT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR,"div.main-content.shifted")))

def drawer_html(d) -> str:
    return drawer_body(d).get_attribute("outerHTML")

def snapshot_links(d):
    body = drawer_body(d)
    return {a.get_attribute("href"):
            (a.text.strip() or urlparse(a.get_attribute("href")).path.split("/")[-1])
            for a in body.find_elements(By.CSS_SELECTOR,"a[href*='-snapshot']")}

def resource_links(d):
    body = drawer_body(d)
    css = "div.SlideOutContentSection.Resources-title-slideOutContentSection"
    with contextlib.suppress(NoSuchElementException):
        sec = body.find_element(By.CSS_SELECTOR, css)
        return {a.get_attribute("href"):
                (a.text.strip() or a.get_attribute("title")
                 or urlparse(a.get_attribute('href')).path.split('/')[-1])
                for a in sec.find_elements(By.CSS_SELECTOR,"a[href*='resources']")}
    return {}

# ─── card handler (unchanged) ────────────────────────────────────────
def handle_card(d, card, code_a,
                seen_snaps:set, seen_res:set) -> tuple[int,list[PDFLine]]:
    out:list[PDFLine] = []
    code = code_a.text or "(no-code)"
    out.append((code, "Helvetica-Bold", 14, 0))

    out.extend(html_to_lines(card.get_attribute("innerHTML")))
    inc = words(card.text)

    list_url = d.current_url
    safe_click(d, code_a)
    WebDriverWait(d, WAIT).until(lambda drv: drv.current_url != list_url)

    open_all_accordions(d)
    out.extend(html_to_lines(drawer_html(d)))
    inc += words(drawer_body(d).text)

    # snapshots ───────────────────────────
    for href, lbl in snapshot_links(d).items():
        if href in seen_snaps: continue
        seen_snaps.add(href)

        d.get(href); WebDriverWait(d, WAIT).until(READY)
        open_all_accordions(d)

        root_html = drawer_html(d)
        out.append((f"Snapshot – {lbl}", "Helvetica-Bold", 12, 0))
        out.extend(html_to_lines(root_html, indent=INDENT))
        inc += words(BeautifulSoup(root_html, "lxml").get_text(" ", strip=True))

        d.back(); WebDriverWait(d, WAIT).until(lambda drv: drv.current_url != href); time.sleep(SLOW)

    # resources ───────────────────────────
    for href, lbl in resource_links(d).items():
        if href in seen_res: continue
        seen_res.add(href)

        d.execute_script("window.open(arguments[0])", href)
        d.switch_to.window(d.window_handles[-1])
        WebDriverWait(d, WAIT).until(READY)

        res_html = ""
        with contextlib.suppress(NoSuchElementException):
            res_html = d.find_element(
                By.CSS_SELECTOR,
                "div[id^='container-'] div.container.responsivegrid.cmp-container--spacing-small"
            ).get_attribute("outerHTML")

        if not res_html:
            res_html = d.find_element(By.TAG_NAME,"body").get_attribute("outerHTML")

        out.append((f"Resource – {lbl}", "Helvetica-Bold", 12, 0))
        out.extend(html_to_lines(res_html, indent=INDENT))
        inc += words(BeautifulSoup(res_html,"lxml").get_text(" ", strip=True))

        d.close(); d.switch_to.window(d.window_handles[0]); time.sleep(SLOW)

    d.back(); WebDriverWait(d, WAIT).until(lambda drv: drv.current_url == list_url); time.sleep(SLOW)
    return inc, out

# ─── crawl whole page (driver passed-in) ────────────────────────────
def crawl(d, url:str, subj:str, yr:str) -> int:
    lines:list[PDFLine]=[]; grand=0
    d.get("about:blank")                # cheap reset
    d.get(url); WebDriverWait(d,25).until(READY)

    with contextlib.suppress(TimeoutException):
        safe_click(d, WebDriverWait(d,4).until(EC.element_to_be_clickable((
            By.XPATH,"//section[contains(@class,'SlideOut')]/div/button"))))

    header = WebDriverWait(d,WAIT).until(EC.presence_of_element_located((
        By.CSS_SELECTOR,"main div.CurriculumView-sectionHeader div")))

    # detailed view
    with contextlib.suppress(NoSuchElementException):
        det = header.find_element(By.XPATH,
            ".//label[.//span[normalize-space()='Detailed view']]")
        if "is-checked" not in det.get_attribute("class"):
            safe_click(d, det); time.sleep(.15)

    chips=[c for c in header.find_elements(By.CSS_SELECTOR,"label[data-value]")
           if c.text.strip() not in {"Simple view","Detailed view"}]
    checked=lambda: header.find_elements(By.CSS_SELECTOR,"label.is-checked[data-value]")

    for chip in chips:
        if chip not in checked():
            while len(checked())>=3:
                safe_click(d, checked()[0]); time.sleep(.05)
            safe_click(d, chip); time.sleep(.15)

        sid = re.sub(r"[^\w-]","-",chip.text.lower()).strip("-")
        try:
            hdr = WebDriverWait(d,WAIT).until(EC.presence_of_element_located((
                By.CSS_SELECTOR,f"header#{sid}")))
        except TimeoutException: continue
        section = hdr.find_element(By.XPATH,"./ancestor::section[1]")
        seen_codes=set(); seen_snaps=set(); seen_res=set()

        def refresh():
            h2=d.find_element(By.CSS_SELECTOR,f"header#{sid}")
            return h2.find_element(By.XPATH,"./ancestor::section[1]")

        while True:
            for card in section.find_elements(By.CSS_SELECTOR,".ContentDescription"):
                try:
                    code_a = card.find_element(By.CSS_SELECTOR,"a.ContentDescription-code")
                    code   = code_a.text or "(no-code)"
                except NoSuchElementException: continue
                if code in seen_codes: continue
                seen_codes.add(code)

                inc, blk = handle_card(d, card, code_a, seen_snaps, seen_res)
                grand += inc; lines.extend(blk)
                section = refresh()

            if not win_scroll(d): break

    pdf = DATA_DIR/slug(subj)/slug(yr)/PDF_NAME.format(s=subj, y=yr)
    wc = save_pdf(lines, pdf)
    say(f"   PDF → {pdf}  ({wc} words)")
    return wc

# ─── run batch ───────────────────────────────────────────────────────
def main():
    if not CSV_FILE.exists():
        say("CSV missing"); sys.exit(1)
    df = pd.read_csv(CSV_FILE, dtype=str)
    if NEW_COL not in df.columns:
        df[NEW_COL] = ""

    start = max(0, RUN_FROM)
    end   = min(len(df)-1, RUN_TO)
    if start > end:
        say(f"Nothing to do: RUN_FROM({RUN_FROM}) > RUN_TO({RUN_TO})"); return

    driver = start_driver()
    try:
        for idx in range(start, end+1):
            row = df.loc[idx]
            url = row.get("URL") or row.get("Link")
            if not url or not url.startswith("http"):
                say(f"[skip] row {idx}: bad URL"); continue
            try:
                wc = crawl(driver, url, row["Subject"], row["Year"])
                df.at[idx, NEW_COL] = wc
                df.to_csv(CSV_FILE, index=False)
                say(f"[ok] row {idx}: {row['Subject']} {row['Year']} → {wc}")
            except Exception as e:
                say(f"[ERR] row {idx}: {e.__class__.__name__}")
                traceback.print_exc(limit=1)
    finally:
        driver.quit()

    say("\nFinished requested rows.")

if __name__ == "__main__":
    main()
