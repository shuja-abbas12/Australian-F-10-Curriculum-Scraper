import time
import pathlib
import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─── CONFIG ────────────────────────────────────────────────────────────────
URL_TO_LOAD = "https://v9.australiancurriculum.edu.au/f-10-curriculum/learning-areas/mathematics/foundation-year/content-description?subject-identifier=MATMATFY&content-description-code=AC9MFN01&detailed-content-descriptions=0&hide-ccp=0&hide-gc=0&side-by-side=1&strands-start-index=0&view=quick"
OUTPUT_FILE = "Explore the content.html"

# Add any optional buttons to click for full content to load
OPTIONAL_SELECTORS = [
    "#curriculum-header-navigation-30b8f38125 > ul > li.cmp-navigation__item.cmp-navigation__item--level-0.F10_CURRICULUM.has-dropdown > button",
]
# ────────────────────────────────────────────────────────────────────────────

def wait_for_js(driver, timeout=20):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    time.sleep(1.5)  # small delay for dynamic content

def click_if_exists(driver, selector, timeout=10):
    try:
        el = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
        )
        el.click()
        wait_for_js(driver)
        print(f"[ok] clicked {selector}")
    except Exception as e:
        print(f"[info] skip or failed click for {selector}: {e}")

def main():
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=opts)

    try:
        driver.get(URL_TO_LOAD)
        wait_for_js(driver)
        print(f"[info] Loaded {URL_TO_LOAD}")

        for sel in OPTIONAL_SELECTORS:
            click_if_exists(driver, sel)

        html = driver.page_source
        pathlib.Path(OUTPUT_FILE).write_text(html, encoding="utf-8")
        print(f"[save] {OUTPUT_FILE} ({len(html):,} bytes)")

    finally:
        driver.quit()

if __name__ == "__main__":
    main()
