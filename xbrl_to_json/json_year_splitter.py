import os
import shutil

# Base directory
base_dir = "data_perusahaan_json/json"

years = ["2021", "2022", "2023", "2024"]
for year in years:
    os.makedirs(os.path.join(base_dir, year), exist_ok=True)

# Loop each file
for filename in os.listdir(base_dir):
    filepath = os.path.join(base_dir, filename)

    if not os.path.isfile(filepath):
        continue

    # Check file name: {KodeEmiten}_{Year}_instance.json
    parts = filename.split("_")
    if len(parts) >= 3 and parts[1].isdigit():
        year = parts[1]
        if year in years:
            target_dir = os.path.join(base_dir, year)
            shutil.move(filepath, os.path.join(target_dir, filename))
            print(f"Moved {filename} -> {target_dir}")
