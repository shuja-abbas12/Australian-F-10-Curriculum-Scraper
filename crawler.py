# crawler.py

import time
import pathlib

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ─── CONFIG ────────────────────────────────────────────────────────────────
URL                   = "https://v9.australiancurriculum.edu.au/"
OUTFILE               = "english_foundation_results.html"

SEL_COOKIE            = "//button[contains(.,'Accept') or contains(.,'Consent')]"
SEL_F10_JS            = "li.F10_CURRICULUM button"
POPUP_ROOT_XPATH      = "//div[contains(@class,'F10CurriculumWidget')]"

SEL_SUBJECT_BTN_XPATH = "(//button[contains(@class,'InputSelector-button')])[1]"
SEL_ENGLISH_LBL_XPATH = "//label[@data-value='ENGENG']"

SEL_YEAR_BTN_XPATH    = "(//button[contains(@class,'InputSelector-button')])[2]"
SEL_FOUNDATION_LBL_XPATH = "//label[@data-value='foundationYear']"

# Matches the submit button once filters are selected
SEL_SUBMIT_BTN_CSS    = (
    "button.LearningAreaSelector-submitButton."
    "LearningAreaSelector-button"
)
# ─────────────────────────────────────────────────────────────────────────────

def wait_ready(driver, timeout=20):
    WebDriverWait(driver, timeout).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )

def main():
    opts = Options()
    # Comment out the next line if you want to run headless
    # opts.add_argument("--headless=new")
    opts.add_argument("--window-size=1400,900")

    driver = webdriver.Chrome(options=opts)  # Selenium Manager auto-handles the driver

    try:
        # 1) Load the home page
        driver.get(URL)
        wait_ready(driver)
        time.sleep(4)  # Allow navigation scripts to initialize

        # 2) Dismiss the cookie banner if present
        try:
            WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, SEL_COOKIE))
            ).click()
            wait_ready(driver)
        except Exception:
            pass

        # 3) Open the F-10 Curriculum popup via JS click
        driver.execute_script(
            "document.querySelector(arguments[0]).click()", SEL_F10_JS
        )

        # 4) Wait for the popup widget to become visible
        WebDriverWait(driver, 15).until(
            EC.visibility_of_element_located((By.XPATH, POPUP_ROOT_XPATH))
        )
        time.sleep(1)

        # 5) Select "English" subject
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, SEL_SUBJECT_BTN_XPATH))
        ).click()
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, SEL_ENGLISH_LBL_XPATH))
        ).click()

        # 6) Select "Foundation Year"
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, SEL_YEAR_BTN_XPATH))
        ).click()
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, SEL_FOUNDATION_LBL_XPATH))
        ).click()

        # 7) Scroll the submit button into view and click it via JS
        submit_btn = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, SEL_SUBMIT_BTN_CSS))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
        time.sleep(0.5)
        driver.execute_script("arguments[0].click();", submit_btn)

        # 8) Wait for the results page to load
        time.sleep(4)
        wait_ready(driver)

        # 9) Save the filtered results page HTML
        html = driver.page_source
        pathlib.Path(OUTFILE).write_text(html, encoding="utf-8")
        print(f"[saved] {OUTFILE} ({len(html):,} bytes)")

        # Keep the browser open briefly so you can inspect
        time.sleep(3)

    finally:
        driver.quit()


if __name__ == "__main__":
    main()
