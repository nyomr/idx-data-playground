import os
import json
import math
import time
import zipfile
import pandas as pd
import undetected_chromedriver as uc
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://www.idx.co.id/primary/ListedCompany/GetFinancialReport"
BASE_DOWNLOAD = "https://www.idx.co.id"


def build_url(page, page_size=36, year=2021, report_type="rdf", emiten_type="s", periode="audit"):
    return (f"{BASE_URL}?indexFrom={page}"
            f"&pageSize={page_size}"
            f"&year={year}"
            f"&reportType={report_type}"
            f"&EmitenType={emiten_type}"
            f"&periode={periode}"
            f"&kodeEmiten="
            f"&SortColumn=KodeEmiten&SortOrder=asc")


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


# Setup driver
download_root = os.path.abspath("data")  # Download path
os.makedirs(download_root, exist_ok=True)

options = uc.ChromeOptions()
options.add_argument("--disable-blink-features=AutomationControlled")
prefs = {
    "download.default_directory": download_root,
    "download.prompt_for_download": False,
    "download.directory_upgrade": True,
    "safebrowsing.enabled": True,
    "plugins.always_open_pdf_externally": True
}
options.add_experimental_option("prefs", prefs)

driver = uc.Chrome(
    version_main=139,
    options=options
)

# Count data
page_size = 36
target_year = 2021
first_url = build_url(page=1, page_size=page_size, year=target_year)
driver.get(first_url)
driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
time.sleep(15)
raw = driver.find_element("tag name", "pre").text
data = json.loads(raw)

total_count = int(data.get("ResultCount", 0))
total_pages = max(1, math.ceil(total_count / page_size))
log(f"Total data: {total_count} | Page size: {page_size} | Total pages: {total_pages}")

# Loop page
rows = []
failed_files = []

for page in range(1, total_pages + 1):
    url = build_url(page=page, page_size=page_size, year=target_year)
    driver.get(url)
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(15)
    raw = driver.find_element("tag name", "pre").text
    data = json.loads(raw)

    for r in data.get("Results", []):
        code = r.get("KodeEmiten")
        name = r.get("NamaEmiten")
        year = r.get("Report_Year")

        for att in r.get("Attachments", []):
            fname = att.get("File_Name", "")
            fpath = att.get("File_Path", "")

            if (
                "instance.zip" in fname
                or ("FinancialStatement" in fname and fname.lower().endswith(".pdf"))
            ):
                url_download = BASE_DOWNLOAD + fpath

                # Retry loop
                max_retries = 3
                attempt = 0
                success = False
                while attempt < max_retries and not success:
                    attempt += 1
                    log(f"DOWNLOAD (attempt {attempt}): {fname} -> {url_download}")
                    driver.get(url_download)
                    time.sleep(3)

                    # Retry timeout
                    src_path = os.path.join(download_root, fname)
                    timeout = 300
                    interval = 2
                    waited = 0
                    while not os.path.exists(src_path) and waited < timeout:
                        time.sleep(interval)
                        waited += interval
                        if waited % 60 == 0:
                            log(f"Still waiting for {fname}... ({waited}s)")

                    if not os.path.exists(src_path):
                        log(f"FAIL: {fname} did not appear after {timeout}s (attempt {attempt})")
                        if attempt < max_retries:
                            log(f"Retrying download for {fname}...")
                            continue
                        else:
                            failed_files.append({
                                "File": fname,
                                "Company": code,
                                "Year": year,
                                "Reason": f"Not found after {timeout}s in {max_retries} attempts"
                            })
                            break

                    # Create folder {year}/{KodeEmiten}
                    save_dir = os.path.join(str(year), code)
                    os.makedirs(save_dir, exist_ok=True)

                    dst_path = os.path.join(save_dir, fname)

                    try:
                        os.replace(src_path, dst_path)
                        log(f"DONE: {fname} -> {dst_path}")
                        success = True
                        time.sleep(2)

                        if fname.lower().endswith(".zip"):
                            try:
                                extract_dir = os.path.join(
                                    save_dir, fname.replace(".zip", "")
                                )
                                os.makedirs(extract_dir, exist_ok=True)

                                with zipfile.ZipFile(dst_path, 'r') as zip_ref:
                                    zip_ref.extractall(extract_dir)

                                log(f"EXTRACT: {fname} -> {extract_dir}")
                                time.sleep(2)

                            except Exception as e:
                                log(f"ERR-UNZIP: {fname} | {e}")
                                failed_files.append({
                                    "File": fname,
                                    "Company": code,
                                    "Year": year,
                                    "Reason": f"Unzip error: {e}"
                                })

                    except Exception as e:
                        log(f"ERROR: {fname} | {e}")
                        failed_files.append({
                            "File": fname,
                            "Company": code,
                            "Year": year,
                            "Reason": str(e)
                        })
                        break

        rows.append({
            "KodeEmiten": code,
            "NamaEmiten": name,
            "Report_Year": year,
        })

# Save to CSV
df = pd.DataFrame(rows)
filename = f"data_perusahaan_{target_year}.csv"
df.to_csv(filename, index=False, encoding="utf-8-sig")
log(f"CSV saved → {filename}")

# Log error
if failed_files:
    log("FAILED DOWNLOADS")
    for f in failed_files:
        log(f"- {f['File']} - ({f['Company']} - {f['Year']}) | Reason: {f['Reason']}")
else:
    log("All files downloaded successfully")
