import pandas as pd
import json
import time
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def extract_role(data, role, kode_emiten):
    if role in data and isinstance(data[role], list):
        df = pd.DataFrame(data[role])
        df["KodeEmiten"] = kode_emiten
        return df
    return pd.DataFrame()


# Setup driver
options = webdriver.ChromeOptions()
driver = webdriver.Chrome(service=Service(
    ChromeDriverManager().install()), options=options)

# Load and count data
df_emiten = pd.read_csv("data_perusahaan_bersih.csv")
kode_emitens = df_emiten["KodeEmiten"].tolist()
total = len(kode_emitens)

# Dictionary to store data
all_data = {}

# Loop each company
for idx, kode in enumerate(kode_emitens, start=1):
    log(f"Processing ({idx}/{total}) {kode} ...")

    url = f"https://www.idx.co.id/primary/ListedCompany/GetCompanyProfilesDetail?KodeEmiten={kode}&language=id"
    driver.get(url)
    time.sleep(2)

    raw = driver.find_element("tag name", "pre").text
    data = json.loads(raw)

    list_keys = [key for key, value in data.items() if isinstance(value, list)]

    # Store data
    for key in list_keys:
        df = extract_role(data, key, kode)
        if not df.empty:
            if key not in all_data:
                all_data[key] = []
            all_data[key].append(df)

driver.quit()

# Save to CSV
for key, df_list in all_data.items():
    final_df = pd.concat(df_list, ignore_index=True)
    filename = f"{key.lower()}.csv"
    final_df.to_csv(filename, index=False, encoding="utf-8-sig")
    log(f"Saved {filename} ({len(final_df)} rows)")

log("Done")
