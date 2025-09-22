import pandas as pd
import time
import re
import json
import math
from tqdm import tqdm
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

x = "2023"
y = f"bersih_pihak_berelasi_{x}.json"
with open(y, "r", encoding="utf-8") as f:
    data_json = json.load(f)


def log(msg):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}")


# --- parameter slice ---
total_parts = 10   # mau bagi jadi 10
# <<< pilih di sini mau jalankan bagian ke berapa (1 s/d 10)
slice_index = 1

# hitung panjang tiap slice
n = len(data_json)
chunk_size = math.ceil(n / total_parts)

start_idx = (slice_index - 1) * chunk_size
end_idx = min(slice_index * chunk_size, n)

# slice data_json
data_slice = data_json[start_idx:end_idx]

log(f"Total data : {n}")
log(f"Running part {slice_index}/{total_parts} → data {start_idx} s/d {end_idx-1} ({len(data_slice)} rows)")


def clean_name(nama):
    nama = str(nama).strip()
    nama = re.sub(r'^\s*PT\s+', '', nama, flags=re.IGNORECASE)  # hapus PT
    nama = re.sub(r'(\s+Tbk\.?)+$', '', nama, flags=re.IGNORECASE)  # hapus Tbk
    suffixes = [
        "Co Ltd",
        "Pte Ltd",
        "Ltd",
        "Inc",
        "Corp",
        "LLC"
    ]
    for suf in suffixes:
        nama = re.sub(rf'\s+{suf}$', '', nama, flags=re.IGNORECASE)
    nama = re.sub(r'\s*\(.*?\)', '', nama)  # hapus (Persero) dsb
    return nama.strip()


def clean_name_and_type(nama):
    """
    Bersihkan nama dan tentukan jenis_korporasi sesuai prefix:
    - default : PT → value = "1"
    - yayasan : hapus "Yayasan" → value = "2"
    - koperasi: hapus "Koperasi" → value = "4"
    """
    jenis_korporasi = "1"  # default PT

    # cek awalan Yayasan
    if re.match(r"^\s*Yayasan\b", nama, flags=re.IGNORECASE):
        nama = re.sub(r"^\s*Yayasan\b", "", nama, flags=re.IGNORECASE).strip()
        jenis_korporasi = "2"

    # cek awalan Koperasi
    elif re.match(r"^\s*Koperasi\b", nama, flags=re.IGNORECASE):
        nama = re.sub(r"^\s*Koperasi\b", "", nama, flags=re.IGNORECASE).strip()
        jenis_korporasi = "4"

    # kalau bukan yayasan/koperasi, pakai clean_name biasa
    else:
        nama = clean_name(nama)

    return nama.strip(), jenis_korporasi


def is_valid_name(nama: str) -> bool:
    """
    Hanya izinkan:
    - Awalan PT (boleh pakai Tbk atau tidak)
    - Hanya akhiran Tbk
    - Awalan Yayasan
    - Awalan Koperasi
    """
    nama = nama.strip()
    lower = nama.lower()

    # Awalan PT
    if re.match(r"^\s*pt\b", nama, flags=re.IGNORECASE):
        return True

    # Akhiran Tbk
    if re.search(r"\btbk\.?\s*$", nama, flags=re.IGNORECASE):
        return True

    # Awalan Yayasan
    if re.match(r"^\s*yayasan\b", nama, flags=re.IGNORECASE):
        return True

    # Awalan Koperasi
    if re.match(r"^\s*koperasi\b", nama, flags=re.IGNORECASE):
        return True

    return False


def is_name(text):
    text = text.strip()
    if not text:
        return False
    if re.match(r"^[A-Z]\.", text):   # A. / B. / C. dst
        return False
    if len(text.split()) > 15:         # deskripsi panjang
        return False
    return True


driver = webdriver.Chrome()

full_success = 0
partial_success = 0
error_count = 0
error_list = []
owner_missing = []

pemilik_records = []   # untuk pemilik + alamat pemilik
alamat_records = []    # untuk alamat perusahaan


def cari_data(nama, kode, nama_emiten, jenis_korporasi="1"):
    max_retries = 2
    attempt = 0
    hasil = None

    alamat_perusahaan = ""

    while attempt < max_retries and hasil is None:
        attempt += 1
        try:
            # log(f"Searching '{nama}' (attempt {attempt})")
            driver.get("https://ahu.go.id/pencarian/profil-pemilik-manfaat")
            time.sleep(0.3)

            select = Select(driver.find_element(By.ID, "jenis_korporasi"))
            time.sleep(0.3)
            select.select_by_value(jenis_korporasi)

            input_box = driver.find_element(By.ID, "nama")
            input_box.clear()
            time.sleep(0.3)
            input_box.send_keys(nama)

            time.sleep(0.3)
            tombol_cari = driver.find_element(By.ID, "search")
            tombol_cari.click()

            # --- ambil alamat perusahaan ---
            try:
                alamat_div = WebDriverWait(driver, 4).until(
                    EC.presence_of_element_located((By.CLASS_NAME, "alamat"))
                )
                alamat_perusahaan = alamat_div.text.strip()
            except:
                alamat_perusahaan = ""

            # --- klik tombol detail ---
            tombol_detail = WebDriverWait(driver, 6).until(
                EC.element_to_be_clickable(
                    (By.CLASS_NAME, "detail_pemilik_manfaat"))
            )
            tombol_detail.click()

            # ambil semua nama (li)
            pemilik_list = WebDriverWait(driver, 6).until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "div.data-pemilik-manfaat ol li"))
            )

            results = []
            for li in pemilik_list:
                name_text = li.text.strip()
                if not is_name(name_text):
                    continue

                # cari div berikutnya (alamat + kriteria)
                try:
                    alamat_div = li.find_element(
                        By.XPATH, "following-sibling::div[1]"
                    )
                    alamat_text = alamat_div.text.strip()
                    alamat_only = alamat_text.split("Kriteria:")[0].strip()
                    alamat_only = re.sub(
                        r"^Alamat Korespondensi:\s*", "", alamat_only, flags=re.IGNORECASE
                    )
                except:
                    alamat_only = ""

                results.append((name_text, alamat_only))

            if results:
                hasil = results
            else:
                hasil = None

        except Exception as e:
            # log(f"Attempt {attempt} failed for '{nama}' ({e.__class__.__name__})")
            tqdm.write(
                f"[{datetime.now().strftime('%H:%M:%S')}] Attempt {attempt} failed for '{nama}' ({e.__class__.__name__})")
            time.sleep(0.3)  # jeda sebelum retry

    return hasil, alamat_perusahaan


for row in tqdm(data_slice, desc=f"Processing companies part {slice_index}", unit="company"):
    kode = row["kodeEmiten"]
    nama_emiten = row["name"]

    if not is_valid_name(nama_emiten):
        continue

    nama_clean, jenis_korporasi = clean_name_and_type(nama_emiten)

    hasil, alamat_perusahaan = cari_data(
        nama_clean, kode, nama_emiten, jenis_korporasi)

    # --- fallback khusus "Ind." ---
    if not hasil and re.search(r"Ind\.\s*$", nama_clean, flags=re.IGNORECASE):
        nama_alt1 = re.sub(r"Ind\.\s*$", "Industry",
                           nama_clean, flags=re.IGNORECASE)
        hasil, alamat_perusahaan = cari_data(nama_alt1, kode, nama_emiten)
        if not hasil:
            nama_alt2 = re.sub(r"Ind\.\s*$", "Industries",
                               nama_clean, flags=re.IGNORECASE)
            hasil, alamat_perusahaan = cari_data(nama_alt2, kode, nama_emiten)

    # --- fallback strip "-" jadi spasi ---
    if not hasil and "-" in nama_clean:
        nama_alt = nama_clean.replace("-", " ")
        hasil, alamat_perusahaan = cari_data(nama_alt, kode, nama_emiten)

    # --- simpan hasil + update counter ---
    if hasil:
        tqdm.write(f"{kode} - {nama_emiten} (with owner data)")
        if alamat_perusahaan:
            alamat_records.append(
                {**row, "AlamatPerusahaan": alamat_perusahaan})
        for h, alamat in hasil:
            pemilik_records.append(
                {**row, "NamaPemilik": h, "AlamatPemilik": alamat})
        full_success += 1

    elif alamat_perusahaan:
        tqdm.write(f"{kode} - {nama_emiten} (only company address)")
        alamat_records.append({**row, "AlamatPerusahaan": alamat_perusahaan})
        partial_success += 1
        owner_missing.append({**row})

    else:
        tqdm.write(f"{kode} - {nama_emiten} : Not found")
        error_count += 1
        error_list.append({**row})
        owner_missing.append({**row})

# simpan ke CSV
pd.DataFrame(pemilik_records).to_csv(
    f"data_pemilik_pihak_berelasi_{x}_part{slice_index}.csv", index=False, encoding="utf-8-sig")
pd.DataFrame(alamat_records).to_csv(
    f"data_administrasi_pihak_berelasi_{x}_part{slice_index}.csv", index=False, encoding="utf-8-sig")

# --- summary ---
df_len = len(data_json)
log("Final Processing Summary")
log(f"Total data        : {df_len}")
log(f"Full Success      : {full_success}")
log(f"Partial (address) : {partial_success}")
log(f"Error             : {error_count}")

# --- simpan error list ke CSV ---
if error_list:
    pd.DataFrame(error_list).to_csv(
        f"error_list_{x}_part{slice_index}.csv", index=False, encoding="utf-8-sig")

if owner_missing:
    pd.DataFrame(owner_missing).to_csv(
        f"owner_missing_{x}_part{slice_index}.csv", index=False, encoding="utf-8-sig")

log("Done scraping JSON names!")
