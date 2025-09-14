import os
import time
import zipfile
import pandas as pd
import undetected_chromedriver as uc
from datetime import datetime

BASE_URL = "https://www.idx.co.id"


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


# Setup driver
download_root = os.path.abspath("data")  # download path
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

driver = uc.Chrome(version_main=139, options=options)


# Load data
missing_df = pd.read_csv("missing_files.csv")
missing = list(zip(missing_df["KodeEmiten"], missing_df["Year"]))

failed_files = []

# Loop task
for kode, year in missing:
    save_dir = os.path.join("missing_data", str(year), kode)
    os.makedirs(save_dir, exist_ok=True)

    # Set targets
    targets = [
        (f"{BASE_URL}/Portals/0/StaticData/ListedCompanies/Corporate_Actions/New_Info_JSX/"
         f"Jenis_Informasi/01_Laporan_Keuangan/02_Soft_Copy_Laporan_Keuangan/"
         f"Laporan Keuangan Tahun {year}/Audit/{kode}/instance.zip",
         "instance.zip"),
        (f"{BASE_URL}/Portals/0/StaticData/ListedCompanies/Corporate_Actions/New_Info_JSX/"
         f"Jenis_Informasi/01_Laporan_Keuangan/02_Soft_Copy_Laporan_Keuangan/"
         f"Laporan Keuangan Tahun {year}/Audit/{kode}/FinancialStatement-{year}-Tahunan-{kode}.pdf",
         f"FinancialStatement-{year}-Tahunan-{kode}.pdf"),
    ]

    for url_download, fname in targets:
        dst_path = os.path.join(save_dir, fname)
        if os.path.exists(dst_path):
            log(f"SKIP (already exists): {dst_path}")
            continue

        max_retries = 3
        attempt = 0
        success = False

        while attempt < max_retries and not success:
            attempt += 1
            log(f"DOWNLOAD (attempt {attempt}): {fname} -> {url_download}")
            driver.get(url_download)
            time.sleep(3)

            src_path = os.path.join(download_root, fname)
            timeout = 120
            interval = 2
            waited = 0
            while not os.path.exists(src_path) and waited < timeout:
                time.sleep(interval)
                waited += interval
                if waited % 30 == 0:
                    log(f"Still waiting for {fname}... ({waited}s)")

            if not os.path.exists(src_path):
                log(f"FAIL: {fname} did not appear after {timeout}s (attempt {attempt})")
                if attempt < max_retries:
                    continue
                else:
                    failed_files.append({
                        "File": fname,
                        "Company": kode,
                        "Year": year,
                        "Reason": "Not found after retries"
                    })
                    break

            try:
                os.replace(src_path, dst_path)
                log(f"DONE: {fname} -> {dst_path}")
                success = True
                time.sleep(2)

                # Unzip
                if fname.lower().endswith(".zip"):
                    try:
                        extract_dir = os.path.join(
                            save_dir, fname.replace(".zip", ""))
                        os.makedirs(extract_dir, exist_ok=True)
                        with zipfile.ZipFile(dst_path, 'r') as zip_ref:
                            zip_ref.extractall(extract_dir)
                        log(f"EXTRACT: {fname} -> {extract_dir}")
                    except Exception as e:
                        log(f"ERR-UNZIP: {fname} | {e}")
                        failed_files.append({
                            "File": fname,
                            "Company": kode,
                            "Year": year,
                            "Reason": f"Unzip error: {e}"
                        })

            except Exception as e:
                log(f"ERROR: {fname} | {e}")
                failed_files.append({
                    "File": fname,
                    "Company": kode,
                    "Year": year,
                    "Reason": str(e)
                })
                break

# Summary
if failed_files:
    log("FAILED DOWNLOADS")
    for f in failed_files:
        log(f"- {f['File']} ({f['Company']} {f['Year']}) | Reason: {f['Reason']}")
else:
    log("All missing files downloaded successfully")
