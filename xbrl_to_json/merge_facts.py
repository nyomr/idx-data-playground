#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Merge semua *_facts.csv jadi ALL_facts.csv (tanpa makan RAM besar)

import pandas as pd
from pathlib import Path

# folder hasil sebelumnya
out_dir = Path(r"D:/Tugas_Akhir/xbrl_to_jason/xbrl_out")

# file output
all_path = out_dir / "ALL_facts.csv"

# cari semua *_facts.csv (kecuali ALL_facts.csv lama kalau ada)
files = sorted([p for p in out_dir.glob("*_facts.csv") if not p.name.startswith("ALL_")])

print(f"Ditemukan {len(files)} file facts, sedang digabung...")

header_written = False
with open(all_path, "w", encoding="utf-8", newline="") as fout:
    for i, f in enumerate(files, 1):
        try:
            df = pd.read_csv(f, dtype=str)  # baca sebagai string biar aman
            df.to_csv(fout, index=False, header=not header_written)
            header_written = True
            print(f"[{i}/{len(files)}] merged {f.name}")
        except Exception as e:
            print(f"[SKIP] {f.name} error: {e}")

print(f"[DONE] ALL_facts.csv berhasil dibuat di {all_path}")
