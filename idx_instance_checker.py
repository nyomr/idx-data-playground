import os
import pandas as pd

json_folder = "data_perusahaan_json/json"
csv_file = "data_perusahaan_bersih.csv"

# Load data
df = pd.read_csv(csv_file)
emiten_codes = df["KodeEmiten"].unique()
years = [2021, 2022, 2023, 2024]

# Expected total files
expected_total = len(emiten_codes) * len(years)

# Get all JSON files
json_files = [f for f in os.listdir(
    json_folder) if f.endswith("_instance.json")]
actual_total = len(json_files)

print("Number of unique emitens:", len(emiten_codes))
print("Number of years:", len(years))
print("Expected total JSON files:", expected_total)
print("Actual total JSON files:", actual_total)

existing = set()
for f in json_files:
    try:
        code, year, _ = f.split("_")
        existing.add((code, int(year)))
    except:
        print("File with unexpected format:", f)

# Find missing files
missing = []
for code in emiten_codes:
    for year in years:
        if (code, year) not in existing:
            missing.append((code, year))

print("Number of missing files:", len(missing))
if missing:
    for m in missing:
        print(m)

missing_df = pd.DataFrame(missing, columns=["KodeEmiten", "Year"])
missing_df.to_csv("missing_files.csv", index=False)

print("Missing files have been saved to missing_files.csv")
