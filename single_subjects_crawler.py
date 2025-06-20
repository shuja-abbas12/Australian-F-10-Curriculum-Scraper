# single_subjects_crawler.py
# ---------------------------------------------------------------
# Crawls the four “single” subjects (no nested drop-downs) across
# Foundation + Year 1-10 and saves:
#   html/<Subject>__<Year>.html
#   single_subjects.csv   Subject,Year,URL,Status,UTC
# ---------------------------------------------------------------
import csv, pathlib, re, time, unicodedata, contextlib
from datetime import datetime, UTC

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# ─── static look-ups taken from home.html ───────────────────────
SUBJECTS = {          # data-value code : UI label
    "ENGENG": "English",
    "MATMAT": "Mathematics",
    "SCISCI": "Science",                        
    "HPEHPE": "Health and Physical Education",
}

YEARS = {             # data-value code : UI label
    "foundationYear": "Foundation Year",
    "year1": "Year 1",
    "year2": "Year 2",
    "year3": "Year 3",
    "year4": "Year 4",
    "year5": "Year 5",
    "year6": "Year 6",
    "year7": "Year 7",
    "year8": "Year 8",
    "year9": "Year 9",
    "year10": "Year 10",
}
# ────────────────────────────────────────────────────────────────

HOME_URL         = "https://v9.australiancurriculum.edu.au/"
HTML_DIR         = pathlib.Path("html"); HTML_DIR.mkdir(exist_ok=True)
CSV_PATH         = pathlib.Path("data.csv")

COOKIE_BTN       = "//button[contains(.,'Accept') or contains(.,'Consent')]"
NAV_F10_JS       = "li.F10_CURRICULUM button"
POPUP_XPATH      = "//div[contains(@class,'F10CurriculumWidget')]"

BTN_SUBJECT      = "(//button[contains(@class,'InputSelector-button')])[1]"
BTN_YEAR         = "(//button[contains(@class,'InputSelector-button')])[2]"
SUBMIT_CSS       = ("button.LearningAreaSelector-submitButton."
                    "LearningAreaSelector-button")

# slide-out close button (search result page)
SLIDE_XPATH      = ("//section[contains(@class,'SlideOut') and contains(@class,'is-open')]"
                    "/div/button")

def wait_dom(drv, t=20):
    WebDriverWait(drv, t).until(
        lambda d: d.execute_script("return document.readyState") == "complete")

def js_click(drv, element):
    drv.execute_script("arguments[0].scrollIntoView({block:'center'});", element)
    drv.execute_script("arguments[0].click()", element)

def open_widget(drv):
    drv.execute_script("document.querySelector(arguments[0]).click()", NAV_F10_JS)
    WebDriverWait(drv, 10).until(
        EC.visibility_of_element_located((By.XPATH, POPUP_XPATH)))
    time.sleep(0.5)

def close_slideout_if_open(drv, timeout=5):
    """Dismiss blue ‘Understand the learning area’ slide-out if present."""
    try:
        btn = WebDriverWait(drv, timeout).until(
            EC.element_to_be_clickable((By.XPATH, SLIDE_XPATH)))
        js_click(drv, btn)
        WebDriverWait(drv, 4).until(
            EC.invisibility_of_element_located((By.XPATH, SLIDE_XPATH)))
    except TimeoutException:
        pass

def safe(text: str) -> str:
    txt = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^\w\-]+", "_", txt).strip("_")[:120]

def crawl_pair(drv, subj_code, year_code):
    open_widget(drv)

    # choose subject
    js_click(drv, drv.find_element(By.XPATH, BTN_SUBJECT))
    js_click(drv, drv.find_element(By.CSS_SELECTOR, f"label[data-value='{subj_code}']"))
    js_click(drv, drv.find_element(By.XPATH, BTN_SUBJECT))

    # choose year
    js_click(drv, drv.find_element(By.XPATH, BTN_YEAR))
    js_click(drv, drv.find_element(By.CSS_SELECTOR, f"label[data-value='{year_code}']"))
    js_click(drv, drv.find_element(By.XPATH, BTN_YEAR))

    # submit
    submit = drv.find_element(By.CSS_SELECTOR, SUBMIT_CSS)
    if submit.get_property("disabled"):
        return "no_data", None, None
    js_click(drv, submit)

    # wait until popup disappears
    WebDriverWait(drv, 12).until(
        EC.invisibility_of_element_located((By.XPATH, POPUP_XPATH)))
    wait_dom(drv)
    close_slideout_if_open(drv)
    time.sleep(1)
    return "saved", drv.page_source, drv.current_url

def main():
    opts = Options()
    opts.add_argument("--window-size=1400,900")
    # opts.add_argument("--headless=new")   # uncomment for headless batch
    drv = webdriver.Chrome(options=opts)

    try:
        with CSV_PATH.open("w", newline="", encoding="utf-8") as fcsv:
            wr = csv.writer(fcsv)
            wr.writerow(["Subject","Year","URL","Status","UTC"])

            for s_code, s_lbl in SUBJECTS.items():
                for y_code, y_lbl in YEARS.items():
                    drv.get(HOME_URL)
                    wait_dom(drv); time.sleep(2)

                    # accept cookies if shown
                    with contextlib.suppress(TimeoutException):
                        WebDriverWait(drv,4).until(
                            EC.element_to_be_clickable((By.XPATH, COOKIE_BTN))
                        ).click()

                    status, html, link = crawl_pair(drv, s_code, y_code)
                    utc = datetime.now(UTC).isoformat(timespec="seconds")
                    wr.writerow([s_lbl, y_lbl, link or "", status, utc])

                    if status == "saved":
                        fname = HTML_DIR / f"{safe(s_lbl)}__{safe(y_lbl)}.html"
                        fname.write_text(html, encoding="utf-8")
                        print(f"✔ {fname.name}")
                    else:
                        print(f"– {s_lbl} | {y_lbl}  ({status})")

    finally:
        drv.quit()

if __name__ == "__main__":
    main()
