#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Scan banyak JSON hasil konversi XBRL -> ambil Related Party facts

import json, re
from pathlib import Path
import pandas as pd

# Folder sumber JSON
json_dir = Path(r"D:\Tugas_Akhir\xbrl_to_jason\xbrl_out")
out_csv  = Path(r"D:\Tugas_Akhir\xbrl_to_jason\related_party_from_json.csv")
out_json = Path(r"D:\Tugas_Akhir\xbrl_to_jason\related_party_from_json.json")

# pola pencarian
PATTERNS = [
    r'related\s*party', r'related\s*parties',
    r'pihak\s*berelasi', r'pihak\s*terkait',
    r'related\s*party\s*transaction', r'related\s*party\s*transactions',
    r'name\s*of\s*related\s*party', r'relationship\s*with\s*related\s*party',
    r'nature\s*of\s*relationship', r'transaksi\s*pihak\s*berelasi',
    r'amounts?\s*owed\s*to\s*related', r'balances?\s*with\s*related',
    r'disclosure[s]?\s*of\s*related'
]
REGEXES = [re.compile(p, re.I) for p in PATTERNS]

rows = []

def search(obj, parent="", file=""):
    """recursive cari pola di key atau value JSON"""
    if isinstance(obj, dict):
        for k,v in obj.items():
            path = f"{parent}/{k}" if parent else k
            if any(rx.search(k) for rx in REGEXES):
                rows.append({"file": file, "path": path, "key": k, "value": v})
            search(v, path, file)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            search(item, f"{parent}[{i}]", file)
    else:
        if isinstance(obj, str) and any(rx.search(obj) for rx in REGEXES):
            rows.append({"file": file, "path": parent, "key": "", "value": obj})

def main():
    files = list(json_dir.glob("*.json"))
    print(f"Scanning {len(files)} JSON files...")
    for i, f in enumerate(files, 1):
        try:
            with open(f, encoding="utf-8") as fp:
                data = json.load(fp)
            before = len(rows)
            search(data, file=f.name)
            new = len(rows) - before
            if new:
                print(f"[{i}/{len(files)}] {f.name} -> {new} hits")
        except Exception as e:
            print(f"[ERROR] {f}: {e}")

    # simpan ke CSV dan JSON
    df = pd.DataFrame(rows)
    df.to_csv(out_csv, index=False, encoding="utf-8")
    df.to_json(out_json, orient="records", indent=2, force_ascii=False)

    print(f"\n[DONE] Found {len(rows)} related-party rows")
    print(f"- CSV : {out_csv}")
    print(f"- JSON: {out_json}")

if __name__ == "__main__":
    main()
