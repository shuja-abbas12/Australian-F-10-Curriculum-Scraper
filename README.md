# Australian F-10 Curriculum Scraper

This project automates the extraction and counting of content descriptions and related data from the official [Australian F-10 Curriculum website](https://v9.australiancurriculum.edu.au/).  
It provides accurate, reproducible, and large-scale word counts for every subject, year, and curriculum area—enabling deep insights into curriculum size and complexity.

---

## Overview

Teachers and stakeholders have expressed concern that the Australian F-10 Curriculum is overwhelming, containing far more material than is practical to use or manage.  
This project set out to **objectively measure** the volume of curriculum content by **automatically counting all visible words** in the main descriptions, deep content sections, general capability snapshots, and resource work samples for every curriculum subject and year.

---

## What the Scraper Does

For each curriculum page (e.g., Mathematics Year 1):

- **Collects all content descriptions** (the main “cards”).
- **Opens each card’s drawer** (detailed view) and counts every word (including headings, points, and notes).
- **Follows all "General Capabilities" and "Cross-curriculum Priorities"** snapshot links and counts the words on every snapshot page, ensuring only visible text is counted.
- **Checks for attached Work Samples/Resources**, opens them in new tabs, and counts the words in the main content area of each resource.
- **Totals** all these counts to provide an accurate measure of content volume for each subject and year.
- **Processes all subjects and years in bulk**, updating a CSV/Excel file in real time so that work is never lost if interrupted.

---

## How We Ensured Accuracy and Reliability

The project was designed to maximize correctness and reproducibility:

- **Human-reproducible navigation:**  
  The script mimics how a human would click through the curriculum site—opening every section, expanding toggles, visiting every deep link, and only counting what is visible on the page.
- **Comprehensive extraction:**  
  All relevant text is captured, including dynamically loaded sections that only appear after user interaction (scroll, click, or toggle).
- **Snapshots and Resources:**  
  Special care was taken to count the words in every "General Capability" and "Cross-curriculum Priority" page linked from each card. Work Samples/Resources are opened in new tabs and closed after counting, ensuring the process does not miss any content.
- **Robust against crashes:**  
  The CSV/Excel data file is updated after processing each page. If the script crashes or is stopped, all prior work is preserved.
- **Handles errors gracefully:**  
  If a page fails to load or an element is not found (for example, due to a website change or a temporary connection issue), the script skips the page and moves on, leaving an empty cell for later review.
- **Optimized speed without sacrificing accuracy:**  
  The script waits just long enough for content to load, but is optimized to minimize unnecessary delay. Timing values were tuned after multiple test runs.
- **Repeatability:**  
  The process can be rerun as often as needed, and can be split across devices for parallel processing. Only rows with missing or empty content counts are re-processed.

---

## Output and Results

- The script outputs a CSV/Excel file (`Final-Results.xlsx`) with the total content word count for every subject and year.
- Each row includes:
  - Subject and year
  - The curriculum URL
  - The grand total word count (base, deep, snapshot, and resource words)
- The results can be used to demonstrate, with concrete evidence, the sheer scale and complexity of the curriculum.

---

## How to Run the Scraper

### 1. **Setup**

- Python 3.9 or newer (recommended: latest stable Python 3)
- [Google Chrome](https://www.google.com/chrome/) (v115+)
- `pip install -r requirements.txt`  
  (installs `selenium`, `pandas`, and any other dependencies)

### 2. **Configure**

- Place your CSV file (e.g., `FinalData.csv`) with columns such as `Subject`, `Year`, and `URL` in the project folder.
- The script will update/add a column called `Content Description` with the results.

### 3. **Run the script**

```bash
python content_description_extractor.py
