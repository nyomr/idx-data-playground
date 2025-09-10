import pandas as pd
import time
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

df = pd.read_csv("data_perusahaan_bersih.csv")


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


def clean_name(name):
    name = str(name).strip()
    name = re.sub(r'^\s*PT\s+', '', name, flags=re.IGNORECASE)  # delete PT
    name = re.sub(r'(\s+Tbk\.?)+$', '', name,
                  flags=re.IGNORECASE)  # delete Tbk
    name = re.sub(r'\s*\(.*?\)', '', name)  # delete ()
    return name.strip()


def is_name(text):
    text = text.strip()
    if not text:
        return False
    if re.match(r"^[A-Z]\.", text):   # no bullet
        return False
    if len(text.split()) > 5:         # no description
        return False
    return True


df["NamaBersih"] = df["NamaEmiten"].apply(clean_name)

driver = webdriver.Chrome()

success_count = 0
error_count = 0
error_list = []

all_results = []


def search_data(name):
    driver.get("https://ahu.go.id/pencarian/profil-pemilik-manfaat")
    time.sleep(0.5)

    try:
        select = Select(driver.find_element(By.ID, "jenis_korporasi"))
        time.sleep(0.3)
        select.select_by_value("1")

        input_box = driver.find_element(By.ID, "nama")
        input_box.clear()
        time.sleep(0.3)
        input_box.send_keys(name)

        time.sleep(0.3)
        search_button = driver.find_element(By.ID, "search")
        search_button.click()

        detail_button = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable(
                (By.CLASS_NAME, "detail_pemilik_manfaat"))
        )
        time.sleep(2)
        detail_button.click()

        owner_list = WebDriverWait(driver, 6).until(
            EC.presence_of_all_elements_located(
                (By.CSS_SELECTOR, "div.data-pemilik-manfaat ol li")
            )
        )

        time.sleep(1)
        result = [li.text for li in owner_list if is_name(li.text)]
        return result if result else None

    except Exception:
        return None


for idx, row in df.iterrows():
    code = row["KodeEmiten"]
    name_emiten = row["NamaEmiten"]
    name_clean = row["NamaBersih"]

    result = search_data(name_clean)

    # Fallback
    if not result and re.search(r"Ind\.\s*$", name_clean, flags=re.IGNORECASE):
        name_alt1 = re.sub(r"Ind\.\s*$", "Industry",
                           name_clean, flags=re.IGNORECASE)
        result = search_data(name_alt1)
        if result:
            print(f"{code} used fallback: {name_alt1}")
        else:
            name_alt2 = re.sub(r"Ind\.\s*$", "Industries",
                               name_clean, flags=re.IGNORECASE)
            result = search_data(name_alt2)
            if result:
                print(f"{code} used fallback: {name_alt2}")

    # Fallback
    if not result and "-" in name_clean:
        name_alt = name_clean.replace("-", " ")
        result = search_data(name_alt)
        if result:
            print(f"{code} used fallback: {name_alt}")

    if result:
        log(f"{code} - {name_emiten}")
        for r in result:
            print("  -", r)
            all_results.append({
                "KodeEmiten": code,
                "NamaEmiten": name_emiten,
                "NamaPemilik": r
            })
        success_count += 1
    else:
        log(f"{code} - {name_emiten} : Not found")
        error_count += 1
        error_list.append(code)

driver.quit()

# Save to CSV
df_out = pd.DataFrame(all_results)
df_out.to_csv("data_pemilik_perusahaan.csv", index=False, encoding="utf-8-sig")

print("\nFinal Processing Summary")
log(f"Total data : {len(df)}")
log(f"Success    : {success_count}")
log(f"Error      : {error_count}")

if error_list:
    print("\nNo owner retrieved:")
    print(", ".join(error_list))
