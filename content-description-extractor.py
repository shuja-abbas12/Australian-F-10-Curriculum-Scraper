# content_description_extractor.py
"""
Iterate over FinalData.csv, visit every URL that has an empty
'Content Description' cell, count words in
  • list-page cards (base)
  • drawer body    (deep)
  • snapshots      (extra)
  • resources      (res)
and store the GRAND TOTAL.

CSV is saved after each processed row → progress is never lost.

Python ≥ 3.9 • Selenium ≥ 4.18 • Chrome ≥ 115
"""

from __future__ import annotations
import re, time, sys, contextlib, pandas as pd
from pathlib import Path
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException)

# ─── USER-TUNABLE SPEED / DEBUG ────────────────────────────────────────
HEADLESS   = True        # flip False to watch in real time
WAIT       = 12          # explicit waits (s)
SCROLL_PX  = 800         # window scroll → triggers lazy-load
SLOW       = 0.10        # delay after each navigation
# ───────────────────────────────────────────────────────────────────────

CSV_FILE   = Path("FinalData.csv")
NEW_COL    = "Content Description"

slug   = lambda s: re.sub(r"[^\w-]", "-", s.lower()).strip("-")
word_re = re.compile(r"\b[\w'-]+\b", re.UNICODE)
words  = lambda txt: len(word_re.findall(txt or ""))
READY  = lambda d: d.execute_script("return document.readyState") == "complete"


# ═════════════ generic helpers ═════════════
def safe_click(drv, el):
    drv.execute_script("arguments[0].scrollIntoView({block:'center'})", el)
    drv.execute_script("arguments[0].click()", el)

def win_scroll(drv) -> bool:
    last = drv.execute_script("return document.body.scrollHeight")
    drv.execute_script(f"window.scrollBy(0,{SCROLL_PX})")
    time.sleep(.08)
    return drv.execute_script("return document.body.scrollHeight") > last

def find_text(drv, css: str) -> str:
    with contextlib.suppress(NoSuchElementException):
        return drv.find_element(By.CSS_SELECTOR, css).text
    return ""


# ═════════════ drawer helpers ═════════════
def drawer_body(drv):
    return WebDriverWait(drv, WAIT).until(
        EC.presence_of_element_located((By.CSS_SELECTOR,
                                        "div.main-content.shifted")))

def drawer_words(drv) -> int:
    body = drawer_body(drv)
    for btn in body.find_elements(
            By.CSS_SELECTOR, "section.ContentToggle:not(.is-open) > header > button"):
        with contextlib.suppress(Exception):
            safe_click(drv, btn)
            time.sleep(.05)
    return words(body.text)

def snapshot_links(drv) -> dict[str, str]:
    body = drawer_body(drv)
    out = {}
    for a in body.find_elements(By.CSS_SELECTOR, "a[href*='-snapshot']"):
        href  = a.get_attribute("href")
        label = a.text.strip() or urlparse(href).path.split("/")[-1]
        out[href] = label
    return out

def resource_links(drv) -> dict[str, str]:
    body = drawer_body(drv)
    css = "div.SlideOutContentSection.Resources-title-slideOutContentSection"
    with contextlib.suppress(NoSuchElementException):
        sec = body.find_element(By.CSS_SELECTOR, css)
        links = sec.find_elements(By.CSS_SELECTOR, "a[href*='resources']")
        return {a.get_attribute("href"):
                (a.text.strip() or a.get_attribute("title")
                 or urlparse(a.get_attribute('href')).path.split('/')[-1])
                for a in links}
    return {}


# ═════════════ card processing ═════════════
def process_card(
        drv, code_link,
        seen_snaps: set[str], seen_res: set[str]
    ) -> tuple[int,int,int]:
    """return deep, extra, res counts for ONE card"""
    list_url = drv.current_url
    safe_click(drv, code_link)
    WebDriverWait(drv, WAIT).until(lambda d: d.current_url != list_url)

    deep  = drawer_words(drv)
    extra = res = 0

    # snapshots ----------
    for href, _ in snapshot_links(drv).items():
        if href in seen_snaps:
            continue
        seen_snaps.add(href)
        drv.get(href); WebDriverWait(drv, WAIT).until(READY)
        txt = find_text(drv, "div.main-content.shifted") or \
              drv.find_element(By.TAG_NAME, "body").text
        extra += words(txt)
        drv.back(); WebDriverWait(drv, WAIT).until(lambda d: d.current_url != href)
        time.sleep(SLOW)

    # resources ----------
    for href, _ in resource_links(drv).items():
        if href in seen_res:
            continue
        seen_res.add(href)
        drv.execute_script("window.open(arguments[0]);", href)
        drv.switch_to.window(drv.window_handles[-1])
        WebDriverWait(drv, WAIT).until(READY)
        txt = (find_text(drv, "#container-14d393ca7e")
               or find_text(drv, "main")
               or drv.find_element(By.TAG_NAME, "body").text)
        res += words(txt)
        drv.close()
        drv.switch_to.window(drv.window_handles[0])
        time.sleep(SLOW)

    drv.back(); WebDriverWait(drv, WAIT).until(lambda d: d.current_url == list_url)
    time.sleep(SLOW)
    return deep, extra, res


# ═════════════ count ONE curriculum page ═════════════
def count_page(url: str) -> int:
    opts = Options()
    if HEADLESS:
        opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,900")
    drv = webdriver.Chrome(options=opts)

    total = 0
    try:
        drv.get(url); WebDriverWait(drv, 25).until(READY)

        # blue help banner
        with contextlib.suppress(TimeoutException):
            btn = WebDriverWait(drv, 4).until(EC.element_to_be_clickable((
                By.XPATH, "//section[contains(@class,'SlideOut')]/div/button")))
            safe_click(drv, btn)

        header = WebDriverWait(drv, WAIT).until(EC.presence_of_element_located((
            By.CSS_SELECTOR, "main div.CurriculumView-sectionHeader div")))

        # force Detailed view
        with contextlib.suppress(NoSuchElementException):
            det = header.find_element(By.XPATH,
                ".//label[.//span[normalize-space()='Detailed view']]")
            if "is-checked" not in det.get_attribute("class"):
                safe_click(drv, det); time.sleep(.2)

        chips = [c for c in header.find_elements(By.CSS_SELECTOR, "label[data-value]")
                 if c.text.strip() not in {"Simple view", "Detailed view"}]
        checked = lambda: header.find_elements(By.CSS_SELECTOR,
                                               "label.is-checked[data-value]")

        for chip in chips:
            if chip not in checked():
                while len(checked()) >= 3:
                    safe_click(drv, checked()[0]); time.sleep(.1)
                safe_click(drv, chip); time.sleep(.25)

            sid = slug(chip.text.strip())
            try:
                hdr = WebDriverWait(drv, WAIT).until(EC.presence_of_element_located((
                    By.CSS_SELECTOR, f"header#{sid}")))
            except TimeoutException:
                continue
            section = hdr.find_element(By.XPATH, "./ancestor::section[1]")

            seen_codes: set[str] = set()
            seen_snaps: set[str] = set()
            seen_res:   set[str] = set()

            def refresh_section():
                hdr2 = drv.find_element(By.CSS_SELECTOR, f"header#{sid}")
                return hdr2.find_element(By.XPATH, "./ancestor::section[1]")

            while True:
                cards = section.find_elements(By.CSS_SELECTOR, ".ContentDescription")
                for card in cards:
                    try:
                        code_link = card.find_element(By.CSS_SELECTOR,
                                                      "a.ContentDescription-code")
                        code = code_link.text or "(no-code)"
                    except NoSuchElementException:
                        continue
                    if code in seen_codes:
                        continue
                    seen_codes.add(code)

                    base = words(card.text)
                    deep, extra, res = process_card(drv, code_link,
                                                    seen_snaps, seen_res)
                    total += base + deep + extra + res

                    # DOM may rerender – refresh section object
                    section = refresh_section()

                if not win_scroll(drv):
                    break

    finally:
        drv.quit()
    return total


# ═════════════ batch over FinalData.csv ═════════════
def main():
    if not CSV_FILE.exists():
        print(f"CSV file '{CSV_FILE}' not found."); sys.exit(1)

    df = pd.read_csv(CSV_FILE, dtype=str)
    if NEW_COL not in df.columns:
        df[NEW_COL] = ""

    for idx, row in df.iterrows():
        cell = str(row.get(NEW_COL, "")).strip()
        if cell and cell.lower() != "nan":
            continue                      # already done

        url = row.get("URL") or row.get("Link")
        if not url or not url.startswith("http"):
            print(f"[skip] row {idx}: URL missing"); continue

        try:
            total = count_page(url)
            df.at[idx, NEW_COL] = total
            df.to_csv(CSV_FILE, index=False)
            print(f"[ok]   row {idx}: {row['Subject']} {row['Year']} → {total}")
        except Exception as e:
            print(f"[ERR]  row {idx}: {e.__class__.__name__} – left blank")
            df.to_csv(CSV_FILE, index=False)

    print("\n=== All rows processed ===")

if __name__ == "__main__":
    main()
