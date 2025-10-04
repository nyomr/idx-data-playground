import pandas as pd

# --- 1. Baca file ---
year = 2023
part = 20
filename = f"data/owner_missing_{year}_part{part}.csv"
df = pd.read_csv(filename)

# --- 2. Tambahkan kolom 'type' kosong jika belum ada ---
if "type" not in df.columns:
    df["type"] = ""

print(f"\nFile '{filename}' berhasil dimuat dengan {len(df)} baris dan {len(df.columns)} kolom.")
print("Kolom tersedia:", ", ".join(df.columns))
print("\nPetunjuk Label (kolom: type):")
print("1 = perusahaan")
print("2 = individu")
print("3 = anomali")
print("Ketik 'selesai' jika sudah selesai memberi label.\n")

# --- 3. Mapping angka ke string ---
type_map = {
    "1": "perusahaan",
    "2": "individu",
    "3": "anomali"
}

# --- 4. Fungsi bantu untuk parsing input range/index ---
def parse_indices(input_str):
    indices = []
    parts = input_str.split(",")
    for part in parts:
        part = part.strip()
        if "-" in part:
            start, end = part.split("-")
            indices.extend(range(int(start), int(end) + 1))
        else:
            indices.append(int(part))
    return indices

# --- 5. Proses input labeling ---
while True:
    index_input = input("Masukkan index (contoh: 0-10, 15, 20) atau 'selesai': ").strip().lower()
    if index_input == "selesai":
        break

    type_input = input("Masukkan type (1/2/3): ").strip()
    if type_input not in type_map:
        print("Input tidak valid, gunakan hanya 1, 2, atau 3.")
        continue

    try:
        label_str = type_map[type_input]
        idx_list = parse_indices(index_input)
        for i in idx_list:
            df.loc[i, "type"] = label_str
        print(f"Type '{label_str}' diterapkan ke index {index_input}.")
    except Exception as e:
        print("Terjadi kesalahan:", e)

# --- 6. Simpan hasil per type ---
for key, name in type_map.items():
    subset = df[df["type"] == name]
    if not subset.empty:
        output_name = f"{name}_owner_missing_{year}_part{part}.csv"
        subset.to_csv(output_name, index=False)
        print(f"💾 File '{output_name}' disimpan dengan {len(subset)} baris.")

print("\nProses selesai! Semua file telah dibuat.")
