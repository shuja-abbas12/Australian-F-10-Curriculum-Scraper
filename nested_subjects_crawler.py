# nested_subjects_crawler.py  (2025-06-14)
# -------------------------------------------------------------
# Crawls the remaining F-10 learning-area groups that have
# nested check-boxes:
#   • Humanities & Social Sciences (HASS…)
#   • Languages (all inner sequences)
#   • Technologies (Design/ Digital)
#   • The Arts (Dance, Drama, …)
#
# One HTML per (Subject Variant , Year)  ➜  html/
# Appends to data.csv  (Subject label, Year, URL, Status, UTC)
# -------------------------------------------------------------
import csv, pathlib, re, time, unicodedata, contextlib, itertools
from datetime import datetime, UTC

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException

# ─── CONSTANTS ────────────────────────────────────────────────
HOME_URL  = "https://v9.australiancurriculum.edu.au/"
HTML_DIR  = pathlib.Path("html"); HTML_DIR.mkdir(exist_ok=True)
CSV_PATH  = pathlib.Path("FinalData.csv")

YEARS = {
    "foundationYear": "Foundation Year", "year1": "Year 1", "year2": "Year 2",
    "year3": "Year 3", "year4": "Year 4", "year5": "Year 5", "year6": "Year 6",
    "year7": "Year 7", "year8": "Year 8", "year9": "Year 9", "year10": "Year 10"
}

# --- group → {code: label} --------------------------------------------------
HASS = {
    "HASHAS": "HASS F-6",
    "HASCIV": "Civics and Citizenship 7-10",
    "HASECO": "Economics and Business 7-10",
    "HASGEO": "Geography 7-10",
    "HASHIS": "History 7-10",
}
TECH = {
    "TECTDE": "Design and Technologies",
    "TECTDI": "Digital Technologies",
}
ARTS = {
    "ARTDAN": "Dance", "ARTDRA": "Drama", "ARTMED": "Media Arts",
    "ARTMUS": "Music", "ARTVIS": "Visual Arts",
}
# --- Languages: parent → {code: label} --------------------------------------
LANG = {
    "Arabic": {
        "LANARAF-1": "Arabic → F-10 Sequence",
        "LANARA7-1": "Arabic → 7-10 Sequence",
    },
    "Auslan": {
        "LANAUSFLLF-1": "Auslan → First-LL Pathway F-10",
        "LANAUSFLL7-1": "Auslan → First-LL Pathway 7-10",
        "LANAUSSLLF-1": "Auslan → Second-LL Pathway F-10",
        "LANAUSSLL7-1": "Auslan → Second-LL Pathway 7-10",
    },
    "Chinese": {
        "LANCHIBLLF-1": "Chinese → Background LL F-10",
        "LANCHIBFL7-1": "Chinese → Background/First LL 7-10",
        "LANCHISECF-1": "Chinese → Second-LL F-10",
        "LANCHISEC7-1": "Chinese → Second-LL 7-10",
    },
    "Classical Greek": {
        "LANCLG": "Classical Greek 7-10",
    },
    "French": {
        "LANFREF-1": "French → F-10 Sequence",
        "LANFRE7-1": "French → 7-10 Sequence",
    },
    "German": {
        "LANGERF-1": "German → F-10 Sequence",
        "LANGER7-1": "German → 7-10 Sequence",
    },
    "Hindi": {
        "LANHINF-1": "Hindi → F-10 Sequence",
        "LANHIN7-1": "Hindi → 7-10 Sequence",
    },
    "Indonesian": {
        "LANINDF-1": "Indonesian → F-10 Sequence",
        "LANIND7-1": "Indonesian → 7-10 Sequence",
    },
    "Italian": {
        "LANITAF-1": "Italian → F-10 Sequence",
        "LANITA7-1": "Italian → 7-10 Sequence",
    },
    "Japanese": {
        "LANJAPF-1": "Japanese → F-10 Sequence",
        "LANJAP7-1": "Japanese → 7-10 Sequence",
    },
    "Korean": {
        "LANKORF-1": "Korean → F-10 Sequence",
        "LANKOR7-1": "Korean → 7-10 Sequence",
    },
    "Latin": {
        "LANLAT": "Latin 7-10",
    },
    "Modern Greek": {
        "LANMGRF-1": "Modern Greek → F-10 Sequence",
        "LANMGR7-1": "Modern Greek → 7-10 Sequence",
    },
    "Spanish": {
        "LANSPAF-1": "Spanish → F-10 Sequence",
        "LANSPA7-1": "Spanish → 7-10 Sequence",
    },
    "Turkish": {
        "LANTURF-1": "Turkish → F-10 Sequence",
        "LANTUR7-1": "Turkish → 7-10 Sequence",
    },
    "Vietnamese": {
        "LANVIEF-1": "Vietnamese → F-10 Sequence",
        "LANVIE7-1": "Vietnamese → 7-10 Sequence",
    },
}

# ─── selenium locators -------------------------------------------------------
COOKIE_X = "//button[contains(.,'Accept') or contains(.,'Consent')]"
NAV_F10_JS = "li.F10_CURRICULUM button"
POPUP_X   = "//div[contains(@class,'F10CurriculumWidget')]"
BTN_SUBJ  = "(//button[contains(@class,'InputSelector-button')])[1]"
BTN_YEAR  = "(//button[contains(@class,'InputSelector-button')])[2]"
SUBMIT_CS = "button.LearningAreaSelector-submitButton.LearningAreaSelector-button"
SLIDE_X   = ("//section[contains(@class,'SlideOut') and contains(@class,'is-open')]/div/button")
CHEVRON_JS = "arguments[0].click()"

# ─── helper functions --------------------------------------------------------
def wait_dom(d,t=20):
    WebDriverWait(d,t).until(lambda drv: drv.execute_script(
        "return document.readyState")=="complete")

def js_click(d, el):
    d.execute_script("arguments[0].scrollIntoView({block:'center'});", el)
    d.execute_script("arguments[0].click()", el)

def open_widget(drv):
    drv.execute_script("document.querySelector(arguments[0]).click()", NAV_F10_JS)
    WebDriverWait(drv,10).until(EC.visibility_of_element_located((By.XPATH,POPUP_X)))
    time.sleep(0.4)

def close_slideout(drv):
    with contextlib.suppress(TimeoutException):
        btn=WebDriverWait(drv,4).until(EC.element_to_be_clickable((By.XPATH,SLIDE_X)))
        js_click(drv,btn)
        WebDriverWait(drv,4).until(EC.invisibility_of_element_located((By.XPATH,SLIDE_X)))

def safe(name:str)->str:
    txt=unicodedata.normalize("NFKD",name).encode("ascii","ignore").decode()
    return re.sub(r"[^\w\-]+","_",txt).strip("_")[:120]

def expand_to_label(drv, label_el):
    """Ensure all parent chevrons are open so the checkbox is clickable."""
    while True:
        try:
            js_click(drv, label_el)
            return
        except ElementClickInterceptedException:
            # find nearest sibling chevron button and click
            chevron = label_el.find_element(
                By.XPATH,
                "./ancestor::div[contains(@class,'InputSelector-checkboxListItem')][1]"
                "/div/button[contains(@class,'icon-prefix-button')]")
            drv.execute_script(CHEVRON_JS, chevron)
            time.sleep(0.3)

def iterate_years(code):
    """Return iterable of year codes allowed by sequence suffix."""
    if code.endswith("7-1") or code.endswith("7-1"):
        return [k for k in YEARS if k in
                ("year7","year8","year9","year10")]
    elif code.endswith("F-1") or code.endswith("F-1"):
        return YEARS.keys()
    elif code.endswith("7-10") or code.endswith("7-10"):  # fixed labels only
        return [k for k in YEARS if k in ("year7","year8","year9","year10")]
    else:
        return YEARS.keys()

def crawl_pair(drv, subj_code, subj_label, year_code, year_label):
    open_widget(drv)

    # open Subject drop-down
    js_click(drv, drv.find_element(By.XPATH, BTN_SUBJ))
    # locate target label element
    label = drv.find_element(By.CSS_SELECTOR, f"label[data-value='{subj_code}']")
    expand_to_label(drv, label)   # recursively open chevrons & click
    js_click(drv, drv.find_element(By.XPATH, BTN_SUBJ))   # close list

    # Year
    js_click(drv, drv.find_element(By.XPATH, BTN_YEAR))
    year_label_el = drv.find_element(By.CSS_SELECTOR, f"label[data-value='{year_code}']")
    js_click(drv, year_label_el)
    js_click(drv, drv.find_element(By.XPATH, BTN_YEAR))

    # Submit (may stay disabled if combo invalid)
    submit = drv.find_element(By.CSS_SELECTOR, SUBMIT_CS)
    if submit.get_property("disabled"):
        return "no_data", None, None
    js_click(drv, submit)

    WebDriverWait(drv,12).until(EC.invisibility_of_element_located((By.XPATH,POPUP_X)))
    wait_dom(drv); close_slideout(drv); time.sleep(0.6)
    return "saved", drv.page_source, drv.current_url

# ─── main loop ---------------------------------------------------------------
def main():
    opts=Options(); opts.add_argument("--window-size=1400,900")
    # opts.add_argument("--headless=new")
    drv=webdriver.Chrome(options=opts)

    try:
        with CSV_PATH.open("a", newline="", encoding="utf-8") as fcsv:
            wr=csv.writer(fcsv)
            if fcsv.tell()==0:
                wr.writerow(["Subject","Year","URL","Status","UTC"])

            subject_iter = (
                list(HASS.items()) +
                list(TECH.items()) +
                list(ARTS.items()) +
                list(itertools.chain.from_iterable(d.items() for d in LANG.values()))
            )

            for code,label in subject_iter:
                for y_code in iterate_years(code):
                    y_label = YEARS[y_code]
                    out_html = HTML_DIR/f"{safe(label)}__{safe(y_label)}.html"
                    if out_html.exists():               # skip done
                        continue

                    # load fresh home page each loop
                    drv.get(HOME_URL); wait_dom(drv); time.sleep(1.5)
                    with contextlib.suppress(TimeoutException):
                        WebDriverWait(drv,4).until(
                            EC.element_to_be_clickable((By.XPATH,COOKIE_X))).click()

                    stat,html,link = crawl_pair(drv,code,label,y_code,y_label)
                    utc=datetime.now(UTC).isoformat(timespec="seconds")
                    wr.writerow([label,y_label,link or "",stat,utc])

                    if stat=="saved":
                        out_html.write_text(html,encoding="utf-8")
                        print(f"✔ {out_html.name}")
                    else:
                        print(f"– {label} | {y_label} ({stat})")

    finally:
        drv.quit()

if __name__=="__main__":
    main()
