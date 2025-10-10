import pandas as pd
import os

year = 2023          
start_part = 1       # part awal
end_part = 20         # part akhir
group_size = 20       # jumlah part per file gabungan

folder = f"datafix/{year}"
base_name = f"perusahaan_owner_missing_{year}_part"
prefix_output = "merge_"

os.makedirs(folder, exist_ok=True)

for start in range(start_part, end_part + 1, group_size):
    end = min(start + group_size - 1, end_part)
    group_files = [os.path.join(folder, f"{base_name}{i}.csv") for i in range(start, end + 1)]

    # cek file yang benar-benar ada (menghindari error kalau ada yang hilang)
    existing_files = [f for f in group_files if os.path.exists(f)]
    if not existing_files:
        print(f"Tidak ada file untuk range {start}–{end}, dilewati.")
        continue

    dfs = [pd.read_csv(f) for f in existing_files]
    combined = pd.concat(dfs, ignore_index=True)

    output_index = (start - start_part) // group_size + 1
    output_name = os.path.join(folder, f"{prefix_output}{base_name}{output_index}.csv")
    combined.to_csv(output_name, index=False)

    print(f"File {output_name} berisi part {start}–{end}")
