import pandas as pd
from pathlib import Path
import re
import os

# ==== KONFIGURASI PATH ====
SANCTION_FILE = r"D:\Tugas_Akhir\scrape_clean_companies\data_sanksi.xlsx"
WATCHLIST_FILE = r"D:\Tugas_Akhir\scrape_clean_companies\papan_pemantauan.xlsx"
CLEAN_FILE = r"D:\Tugas_Akhir\scrape_clean_companies\clean_companies_fix.csv"

# Rentang tahun
TAHUN_MIN, TAHUN_MAX = 2021, 2025

# path folder output
OUT_DIR = r"D:\Tugas_Akhir\scrape_clean_companies\hasil_filter"
os.makedirs(OUT_DIR, exist_ok=True)  # bikin folder kalau belum ada

# nama file output
OUT_SANCTION = os.path.join(OUT_DIR, "sanksi_filtered.csv")
OUT_WATCH    = os.path.join(OUT_DIR, "pemantauan_filtered.csv")
OUT_COMBINED = os.path.join(OUT_DIR, "gabungan_filtered.csv")
OUT_UNMATCH  = os.path.join(OUT_DIR, "perusahaan_tidak_terdeteksi.csv")

print("Output akan disimpan di:", OUT_DIR)

# ---------- util umum ----------
def normalize_code(s):
    if pd.isna(s): return ""
    return str(s).strip().upper()

def find_col(df: pd.DataFrame, aliases: list[str]) -> str | None:
    low2orig = {c.lower(): c for c in df.columns}
    # exact (case-insensitive)
    for a in aliases:
        if a.lower() in low2orig:
            return low2orig[a.lower()]
    # contains
    for a in aliases:
        for c in df.columns:
            if a.lower() in c.lower():
                return c
    return None

# ---------- loader CLEAN COMPANIES (semicolon) ----------
def load_clean_companies(path: str) -> pd.DataFrame:
    # coba pakai delimiter ';' dulu
    try:
        df = pd.read_csv(path, dtype=str, sep=';', encoding='utf-8-sig')
        cols = [c.strip().replace('\ufeff','') for c in df.columns]
        df.columns = cols
    except Exception:
        # fallback autodetect
        df = pd.read_csv(path, dtype=str, engine='python', sep=None, encoding='utf-8-sig')

    # normalisasi header ke standar
    rename_map = {
        "Kode Perusahaan": "Kode",
        "Kode/Nama Perusahaan": "Kode",
        "Nama": "Nama Perusahaan",
        "Nama Perusahaan": "Nama Perusahaan",
        "Tanggal Pencatatan": "Tanggal Pencatatan",
    }
    for k,v in list(rename_map.items()):
        if k in df.columns and v not in df.columns:
            df.rename(columns={k:v}, inplace=True)

    # jika masih satu kolom gabung karena delimiter salah, split manual
    if df.shape[1] == 1 and df.columns[0].count(";") == 2:
        # header gabungan → split
        df = df[df.columns[0]].str.split(";", n=2, expand=True)
        df.columns = ["Kode","Nama Perusahaan","Tanggal Pencatatan"]

    # pastikan kolom Kode ada
    if "Kode" not in df.columns:
        # mungkin masih ada kolom gabungan
        col = find_col(df, ["Kode/Nama Perusahaan","Kode Perusahaan","Kode"])
        if col:
            df["Kode"] = df[col].astype(str).str.strip().str.upper().str.replace(r"\s+.*$", "", regex=True)
        else:
            raise ValueError("Clean companies: tidak menemukan kolom Kode.")

    df["Kode"] = df["Kode"].map(normalize_code)
    df = df.dropna(subset=["Kode"]).drop_duplicates(subset=["Kode"])
    return df[["Kode"] + [c for c in df.columns if c != "Kode"]]

# ---------- loader WATCHLIST (papan_pemantauan.xlsx) ----------
def load_watchlist(path: str) -> pd.DataFrame:
    df = pd.read_excel(path, dtype=str)
    # normalisasi nama kolom yang umum dari filemu:
    # ['Kode Saham','Nama Perusahaan','Tanggal Masuk','Tanggal Keluar','Kriteria']
    # pastikan kolom Kode & Tahun ada
    if "Kode" not in df.columns:
        col_kode = find_col(df, ["Kode Saham","Kode","Stock Code","Ticker","Symbol"])
        if not col_kode:
            raise ValueError("Watchlist: kolom Kode tidak ditemukan.")
        df["Kode"] = df[col_kode].map(normalize_code)

    # derive Tahun dari Tanggal Masuk (kalau ada)
    col_tgl = find_col(df, ["Tanggal Masuk","Tanggal","Date","Effective Date"])
    if col_tgl:
        dt = pd.to_datetime(df[col_tgl], errors="coerce", dayfirst=True, infer_datetime_format=True)
        df["Tahun"] = dt.dt.year.astype("Int64")
    else:
        # kalau ada kolom Tahun eksplisit
        col_year = find_col(df, ["Tahun","Year"])
        df["Tahun"] = pd.to_numeric(df[col_year], errors="coerce").astype("Int64") if col_year else pd.NA

    # filter tahun bila ada
    mask = df["Tahun"].notna()
    if mask.any():
        df = df.loc[mask]
        df = df[(df["Tahun"] >= TAHUN_MIN) & (df["Tahun"] <= TAHUN_MAX)]

    df["Sumber"] = "Pemantauan"
    return df

# ---------- loader SANKSI (Excel multi-sheet / header berantakan) ----------
def load_sanctions(path: str) -> pd.DataFrame:
    x = pd.ExcelFile(path)
    tables = []
    for sh in x.sheet_names:
        try:
            tmp = x.parse(sh, dtype=str, header=None)
        except Exception:
            continue
        # buang baris yang semuanya NaN
        tmp = tmp.dropna(how="all")
        if tmp.empty: 
            continue

        # deteksi baris header: cari baris yang memuat kata kunci
        header_row_idx = None
        for i in range(min(15, len(tmp))):  # scan 15 baris pertama
            row_vals = " ".join([str(v) for v in tmp.iloc[i].tolist() if pd.notna(v)]).lower()
            if any(k in row_vals for k in ["kode","saham","emiten"]) and any(k in row_vals for k in ["tahun","tanggal","tgl"]):
                header_row_idx = i
                break
        if header_row_idx is None:
            # tidak ada sinyal header yang bagus → skip sheet ini
            continue

        # set header
        tmp2 = x.parse(sh, dtype=str, header=header_row_idx)
        tmp2.columns = [str(c).strip() for c in tmp2.columns]
        # buang kolom Unnamed
        tmp2 = tmp2.loc[:, [c for c in tmp2.columns if not str(c).lower().startswith("unnamed")]]
        # buang baris kosong
        tmp2 = tmp2.dropna(how="all")
        if not tmp2.empty:
            tables.append(tmp2)

    if not tables:
        # fallback: coba read_excel biasa dan berharap ada kolom
        df = pd.read_excel(path, dtype=str)
    else:
        df = pd.concat(tables, ignore_index=True)

    # standar kolom Kode
    if "Kode" not in df.columns:
        col_kode = find_col(df, ["Kode Saham","Kode Emiten","Kode","Stock Code","Ticker","Symbol","Emiten"])
        if not col_kode:
            raise ValueError("Sanksi: kolom Kode tidak ditemukan.")
        if re.search(r"kode/?nama", col_kode, flags=re.I):
            df["Kode"] = df[col_kode].astype(str).str.strip().str.upper().str.replace(r"\s+.*$", "", regex=True)
        else:
            df["Kode"] = df[col_kode].astype(str).str.strip().str.upper()

    # derive Tahun
    col_year = find_col(df, ["Tahun","Year"])
    if col_year:
        df["Tahun"] = pd.to_numeric(df[col_year], errors="coerce").astype("Int64")
    else:
        col_tgl = find_col(df, ["Tanggal","Tgl","Tanggal Keputusan","Date","Effective Date"])
        if col_tgl:
            dt = pd.to_datetime(df[col_tgl], errors="coerce", dayfirst=True, infer_datetime_format=True)
            df["Tahun"] = dt.dt.year.astype("Int64")
        else:
            df["Tahun"] = pd.NA

    # filter tahun bila tersedia
    mask = df["Tahun"].notna()
    if mask.any():
        df = df.loc[mask]
        df = df[(df["Tahun"] >= TAHUN_MIN) & (df["Tahun"] <= TAHUN_MAX)]

    df["Sumber"] = "Sanksi"
    return df

# ---------- main ----------
def main():
    # load tiga sumber
    clean_df = load_clean_companies(CLEAN_FILE)
    sanctions_df = load_sanctions(SANCTION_FILE)
    watch_df = load_watchlist(WATCHLIST_FILE)

    # keep only kode bersih
    kode_bersih = set(clean_df["Kode"])
    sanctions_df = sanctions_df[sanctions_df["Kode"].isin(kode_bersih)]
    watch_df = watch_df[watch_df["Kode"].isin(kode_bersih)]

    # gabung & unmatched
    combined_df = pd.concat([sanctions_df, watch_df], ignore_index=True)
    matched_codes = set(combined_df["Kode"])
    unmatched = clean_df[~clean_df["Kode"].isin(matched_codes)].copy()

    # simpan
    sanctions_df.to_csv(OUT_SANCTION, index=False, encoding="utf-8-sig")
    watch_df.to_csv(OUT_WATCH, index=False, encoding="utf-8-sig")
    combined_df.to_csv(OUT_COMBINED, index=False, encoding="utf-8-sig")
    unmatched.to_csv(OUT_UNMATCH, index=False, encoding="utf-8-sig")

    print("✅ selesai. file hasil:")
    print("-", OUT_SANCTION, f"({len(sanctions_df)} baris)")
    print("-", OUT_WATCH,    f"({len(watch_df)} baris)")
    print("-", OUT_COMBINED, f"({len(combined_df)} baris)")
    print("-", OUT_UNMATCH,  f"({len(unmatched)} emiten tidak muncul di sanksi/pemantauan)")

if __name__ == "__main__":
    main()
