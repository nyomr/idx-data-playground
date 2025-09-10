import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

URL = "https://www.idx.co.id/id/perusahaan-tercatat/profil-perusahaan-tercatat/"
OUTPUT = "clean_companies.csv"

def pick_all_rows(driver):
    """Pilih dropdown 'Baris' -> All atau -1"""
    try:
        # tunggu elemen dropdown dekat label 'Baris'
        dropdown = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, '//select[@name="DataTables_Table_0_length"]'))
        )
        driver.execute_script("arguments[0].scrollIntoView(true);", dropdown)
        time.sleep(1)

        select = Select(dropdown)
        try:
            select.select_by_visible_text("All")
        except:
            try:
                select.select_by_value("-1")
            except Exception as e:
                print("⚠️ Gagal pilih 'All', coba manual:", e)
        print("✅ Dropdown 'All' berhasil dipilih")
    except TimeoutException:
        print("⚠️ Tidak menemukan dropdown 'Baris'")

def wait_until_all_loaded(driver, min_rows=900):
    """Tunggu sampai tabel punya minimal jumlah baris"""
    for i in range(30):  # coba maksimal 30 detik
        rows = driver.find_elements(By.CSS_SELECTOR, "#DataTables_Table_0 tbody tr")
        if len(rows) >= min_rows:
            print(f"✅ Tabel sudah penuh: {len(rows)} baris")
            return
        time.sleep(1)
    print(f"⚠️ Timeout, hanya {len(rows)} baris yang terbaca")

def scrape_table(driver):
    """Ambil data tabel ke DataFrame pandas"""
    html = driver.page_source
    tables = pd.read_html(html)
    df = tables[0]
    # rapikan kolom
    df = df.rename(columns={
        "Kode/Nama Perusahaan": "Kode",
        "Nama": "Nama Perusahaan",
        "Tanggal Pencatatan": "Tanggal Pencatatan"
    })
    return df

def main():
    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # kalau mau headless uncomment ini
    # options.add_argument("--headless=new")

    driver = webdriver.Chrome(options=options)
    driver.get(URL)

    # pilih All
    pick_all_rows(driver)

    # tunggu sampai semua baris muncul
    wait_until_all_loaded(driver, min_rows=900)

    # scrape ke DataFrame
    df = scrape_table(driver)

    # bersihkan data
    df = df.dropna(how="all")
    df = df.drop_duplicates()

    # simpan ke CSV
    df.to_csv(OUTPUT, index=False, encoding="utf-8-sig")
    print(f"💾 Data perusahaan bersih disimpan ke {OUTPUT} ({len(df)} baris)")

    driver.quit()

if __name__ == "__main__":
    main()
